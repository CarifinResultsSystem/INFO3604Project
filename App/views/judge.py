import os
from flask import Blueprint, render_template, url_for, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from App.controllers import get_score_document, get_all_score_documents, get_unconfirmed_documents, get_unconfirmed_documents_count
from App.models import ScoreDocument
import pandas as pd
import numpy as np

judge_views = Blueprint('judge_views', __name__, template_folder='../templates')

def identify_cell_errors(unconfirmed_doc):
    try:
        doc_df = pd.read_excel(unconfirmed_doc.storedPath)
        error_cells = []
        
        # Check if 'Event/Institution' column exists
        if 'Event/Institution' not in doc_df.columns:
            print("Warning: 'Event/Institution' column not found")
            return error_cells
        
        # Find the TOTAL row
        total_mask = doc_df['Event/Institution'].astype(str).str.title() == 'Total'
        total_row_indices = doc_df.index[total_mask].tolist()
        
        if len(total_row_indices) > 0:
            total_idx = total_row_indices[0]
            
            # Get all rows before the TOTAL row
            rows_before_total = doc_df.iloc[:total_idx]
            
            # Get institution columns (all except first column)
            institutions = doc_df.columns[1:]
            
            # Check each institution's total
            for inst_idx, inst in enumerate(institutions, start=1):
                try:
                    calculated_sum = rows_before_total[inst].sum()
                    actual_total = doc_df.loc[total_idx, inst]
                    
                    if abs(calculated_sum - actual_total) >= 0.01:
                        error_cells.append({
                            'institution': inst,
                            'column_index': inst_idx,
                            'row_index': total_idx,
                            'calculated_value': round(calculated_sum, 2),
                            'reported_value': actual_total,
                            'difference': round(calculated_sum - actual_total, 2),
                            'cell_location': f"Row {total_idx + 1}, Column {inst}",
                            'error_type': 'Total Mismatch'
                        })
                except Exception as e:
                    print(f"Error processing institution {inst}: {str(e)}")
                    continue
        
        return error_cells
    except Exception as e:
        print(f"Error in identify_cell_errors: {str(e)}")
        return []


def identify_all_cell_errors(unconfirmed_doc):
    doc_df = pd.read_excel(unconfirmed_doc.storedPath)
    all_errors = []
    
    # Get institution columns (all except first column)
    institutions = doc_df.columns[1:]
    
    # Check for TOTAL row errors first
    total_errors = identify_cell_errors(unconfirmed_doc)
    all_errors.extend(total_errors)
    
    # Check each cell in the dataframe for other issues
    for row_idx in range(len(doc_df)):
        event_name = doc_df.iloc[row_idx, 0]
        
        # Skip checking the TOTAL row for negative values (it should be a sum)
        if event_name and 'TOTAL' in str(event_name).upper():
            continue
            
        for col_idx, inst in enumerate(institutions, start=1):
            cell_value = doc_df.iloc[row_idx, col_idx]
            
            # Check if value is numeric
            if pd.isna(cell_value):
                all_errors.append({
                    'institution': inst,
                    'column_index': col_idx,
                    'row_index': row_idx,
                    'event': event_name,
                    'value': cell_value,
                    'cell_location': f"Row {row_idx + 1}, Column {inst}",
                    'error_type': 'Missing Value'
                })
            elif not isinstance(cell_value, (int, float)):
                try:
                    float(cell_value)
                except (ValueError, TypeError):
                    all_errors.append({
                        'institution': inst,
                        'column_index': col_idx,
                        'row_index': row_idx,
                        'event': event_name,
                        'value': cell_value,
                        'cell_location': f"Row {row_idx + 1}, Column {inst}",
                        'error_type': 'Non-numeric Value'
                    })
            elif cell_value < 0:
                all_errors.append({
                    'institution': inst,
                    'column_index': col_idx,
                    'row_index': row_idx,
                    'event': event_name,
                    'value': cell_value,
                    'cell_location': f"Row {row_idx + 1}, Column {inst}",
                    'error_type': 'Negative Value'
                })
    
    
    return all_errors


def count_errors(unconfirmed_doc):
    errors = identify_all_cell_errors(unconfirmed_doc)
    return len(errors)


@judge_views.route('/judge/')
@jwt_required()
def judge_dashboard():
    unconfirmed_docs_count = get_unconfirmed_documents_count()
    unconfirmed_docs = get_unconfirmed_documents()
    errors = 0
    
    for doc in unconfirmed_docs:
        errors += count_errors(doc)
        
    print(errors)
        
    return render_template('judge/judge.html', user=current_user, unconfirmed_docs_count=unconfirmed_docs_count, errors=errors)

@judge_views.route('/judge/review')
@jwt_required()
def review_scores():
    documents = get_unconfirmed_documents()
    
    docs_data = []
    for d in documents:
        ext = os.path.splitext(d.originalFilename)[1].lstrip('.').upper() if d.originalFilename else ''
        docs_data.append({
            "id":            d.documentID,
            "filename":      d.originalFilename or '—',
            "storedFilename": d.storedFilename,
            "uploadedAt":    d.uploadedOn.strftime("%b %d, %Y · %H:%M") if d.uploadedOn else "—",
            "uploadedAtRaw": d.uploadedOn.isoformat() if d.uploadedOn else "",
            "fileType":      ext or "FILE",
            "viewUrl":       url_for('scoretaker_views.view_document', documentID=d.documentID),
            "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=d.documentID),
            "errors":       count_errors(d),
        })

    # Sort newest first by default
    docs_data.sort(key=lambda x: x["uploadedAtRaw"], reverse=True)
    
    return render_template('judge/review.html', documents=docs_data)

@judge_views.route('/judge/review/<int:documentID>', methods=['GET'])
@jwt_required()
def review_score_document(documentID):
    document = get_score_document(documentID)
    
    ext = os.path.splitext(document.originalFilename)[1].lstrip('.').upper() if document.originalFilename else ''
    doc_data = ({
        "id":            document.documentID,
        "filename":      document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":    document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw": document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":      ext or "FILE",
        "viewUrl":       url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=document.documentID),
    })
    
    try:
        if not os.path.exists(document.storedPath):
            raise Exception(f"File not found at path: {document.storedPath}")
        
        df = pd.read_excel(document.storedPath)
        
        error_map = {}
        
        try:
            errors = identify_cell_errors(document)
            
            for error in errors:
                key = f"{error['row_index']},{error['column_index']}"
                error['message'] = f"Total mismatch: Calculated {error['calculated_value']} vs Reported {error['reported_value']}"
                error_map[key] = error
        except Exception as e:
            print(f"Error in identify_cell_errors: {str(e)}")
            import traceback
            traceback.print_exc()
        
        try:
            # Get all cell errors
            all_errors = identify_all_cell_errors(document)
            
            for error in all_errors:
                key = f"{error['row_index']},{error['column_index']}"
                if key not in error_map:
                    if error['error_type'] == 'Missing Value':
                        error['message'] = f"Missing value at {error['cell_location']}"
                    else:
                        error['message'] = error['error_type']
                    error_map[key] = error
        except Exception as e:
            print(f"Error in identify_all_cell_errors: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Convert rows to ensure all values are properly formatted
        rows = []
        for row_idx, row in enumerate(df.values.tolist()):
            new_row = []
            for col_idx, cell in enumerate(row):
                if pd.isna(cell):
                    new_row.append('')
                elif isinstance(cell, (int, float)):
                    new_row.append(cell)
                else:
                    new_row.append(str(cell))
            rows.append(new_row)
        
        table_data = {
            'columns': df.columns.tolist(),
            'rows': rows,
            'headers': df.columns.tolist(),
            'error_map': error_map,
            'total_errors': len(error_map)
        }
        
        
    except Exception as e:
        print(f"Error loading document: {str(e)}")
        import traceback
        traceback.print_exc()
        table_data = {
            'columns': ['Error'],
            'rows': [[f'Could not load file: {str(e)}']],
            'headers': ['Error'],
            'error_map': {},
            'total_errors': 0
        }
    
    return render_template('judge/review_document.html', document=doc_data, table_data=table_data)

@judge_views.route('/judge/review/<int:documentID>/edit', methods=['GET', 'POST'])
@jwt_required()
def edit_score_document(documentID):
    document = get_score_document(documentID)
    
    ext = os.path.splitext(document.originalFilename)[1].lstrip('.').upper() if document.originalFilename else ''
    doc_data = ({
        "id":            document.documentID,
        "filename":      document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":    document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw": document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":      ext or "FILE",
        "viewUrl":       url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=document.documentID),
    })
    
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not data or 'rows' not in data:
            return jsonify({"error": "Invalid request body. Expected JSON with a 'rows' key."}), 400

        try:
            existing_df = pd.read_excel(document.storedPath)
            columns = existing_df.columns.tolist()

            submitted_rows = data['rows']

            if len(submitted_rows) != len(existing_df):
                return jsonify({
                    "error": f"Row count mismatch: expected {len(existing_df)}, received {len(submitted_rows)}."
                }), 400

            if any(len(row) != len(columns) for row in submitted_rows):
                return jsonify({
                    "error": "Column count mismatch in one or more rows."
                }), 400

            def coerce(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return val if val not in ('', None) else np.nan

            coerced_rows = [[coerce(cell) for cell in row] for row in submitted_rows]
            updated_df = pd.DataFrame(coerced_rows, columns=columns)

            updated_df.to_excel(document.storedPath, index=False)

            return jsonify({"message": "Document saved successfully."}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to save document: {str(e)}"}), 500
    
    try:
        df = pd.read_excel(document.storedPath)
        table_data = {
            'columns': df.columns.tolist(),
            'rows': df.values.tolist(),
            'headers': df.columns.tolist()
        }
    except Exception as e:
        table_data = {
            'columns': ['Error'],
            'rows': [[f'Could not load file: {str(e)}']],
            'headers': ['Error']
        }
    
    return render_template('judge/edit_document.html', document=doc_data, table_data=table_data)

#modified from scoretaker archives
@judge_views.route('/judge/archives')
@jwt_required()
def archives():
    documents = get_all_score_documents()

    docs_data = []
    for d in documents:
        ext = os.path.splitext(d.originalFilename)[1].lstrip('.').upper() if d.originalFilename else ''
        docs_data.append({
            "id":            d.documentID,
            "filename":      d.originalFilename or '—',
            "storedFilename": d.storedFilename,
            "uploadedAt":    d.uploadedOn.strftime("%b %d, %Y · %H:%M") if d.uploadedOn else "—",
            "uploadedAtRaw": d.uploadedOn.isoformat() if d.uploadedOn else "",
            "fileType":      ext or "FILE",
            "viewUrl":       url_for('scoretaker_views.view_document', documentID=d.documentID),
            "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=d.documentID),
        })

    # Sort newest first by default
    docs_data.sort(key=lambda x: x["uploadedAtRaw"], reverse=True)

    return render_template(
        'judge/archives.html',
        documents=docs_data,
        total=len(docs_data),
        user=current_user
    )