import os
import re
from flask import Blueprint, render_template, url_for, jsonify, request, abort, send_file, current_app
from flask_jwt_extended import jwt_required, current_user
from App.database import db
from App.controllers import get_score_document, get_all_score_documents, get_unconfirmed_documents, get_unconfirmed_documents_count
from App.models import ScoreDocument, PointsRules
import pandas as pd
import numpy as np

judge_views = Blueprint('judge_views', __name__, template_folder='../templates')

#Checks if cells under institutions are empty, used to identify Challenge and event header rows
def _all_inst_empty(row, inst_cols):
    for col in inst_cols:
        val = row[col]
        if pd.notna(val) and str(val).strip() != '':
            return False
    return True

#Ensures there is no unneccesary whitespace
def _normalise_label(label):
    return re.sub(r'\s+', ' ', label).strip().lower()

#Returns a dict from the PointsRulesTable for use in identify_cell_errors
def _get_points_rule_lookup():
    lookup = {}
    try:
        for pr in PointsRules.query.all():
            if pr.label:
                key = re.sub(r'\s+', ' ', pr.label).strip().lower()
                if key not in lookup or pr.points > lookup[key]:
                    lookup[key] = pr.points
    except Exception as e:
        print(f"Warning: could not load PointsRules from DB: {e}")
    return lookup

#helper function to get point rules range
def _get_max_points_for_label(spreadsheet_label, points_lookup):
    normalised = _normalise_label(spreadsheet_label)

    if normalised in points_lookup:
        return points_lookup[normalised]

    matches = [(k, v) for k, v in points_lookup.items() if k in normalised]
    if matches:
        best_key, best_pts = max(matches, key=lambda kv: len(kv[0]))
        return best_pts
    return None

#Used to parse the document, 
def parse_hierarchical_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    if df.empty or 'Rule' not in df.columns:
        return None

    institutions = [c for c in df.columns if c != 'Rule']

    challenges = []
    totals = {}
    rankings = {}
    current_challenge = None
    current_event = None

    for _, row in df.iterrows():
        rule_val = row['Rule']
        rule_str = str(rule_val).strip() if pd.notna(rule_val) else ''

        if rule_str == '':
            # blank / spacer row – skip
            continue

        rule_upper = rule_str.upper()

        if 'TOTAL POINTS' in rule_upper:
            for inst in institutions:
                v = row[inst]
                totals[inst] = float(v) if pd.notna(v) and str(v).strip() != '' else 0.0
            continue

        if rule_upper.startswith('RANKING'):
            for inst in institutions:
                v = row[inst]
                rankings[inst] = v if pd.notna(v) and str(v).strip() != '' else ''
            continue

        if _all_inst_empty(row, institutions):
            if current_challenge is None or rule_str == rule_str.upper():
                current_challenge = {'name': rule_str, 'events': []}
                challenges.append(current_challenge)
                current_event = None
            else:
                current_event = {'name': rule_str, 'rules': []}
                if current_challenge is not None:
                    current_challenge['events'].append(current_event)
        else:
            scores = {}
            for inst in institutions:
                v = row[inst]
                scores[inst] = float(v) if pd.notna(v) and str(v).strip() != '' else 0.0

            rule_entry = {'label': rule_str, 'scores': scores}

            if current_event is not None:
                current_event['rules'].append(rule_entry)
            elif current_challenge is not None:
                if not current_challenge['events'] or current_challenge['events'][-1].get('_direct'):
                    if not current_challenge['events'] or not current_challenge['events'][-1].get('_direct'):
                        direct_event = {'name': '', 'rules': [], '_direct': True}
                        current_challenge['events'].append(direct_event)
                        current_event = direct_event
                    current_event['rules'].append(rule_entry)
                else:
                    current_event['rules'].append(rule_entry)
            else:
                if not challenges:
                    challenges.append({'name': '', 'events': []})
                    current_challenge = challenges[-1]
                orphan_event = {'name': '', 'rules': [rule_entry], '_direct': True}
                current_challenge['events'].append(orphan_event)

    calculated_totals = {inst: 0.0 for inst in institutions}
    for challenge in challenges:
        for event in challenge['events']:
            for rule in event['rules']:
                for inst in institutions:
                    calculated_totals[inst] += rule['scores'].get(inst, 0.0)
    calculated_totals = {inst: round(v, 2) for inst, v in calculated_totals.items()}

    sorted_insts = sorted(institutions, key=lambda i: calculated_totals[i], reverse=True)
    calculated_rankings = {}
    rank = 1
    for i, inst in enumerate(sorted_insts):
        if i > 0 and calculated_totals[inst] == calculated_totals[sorted_insts[i - 1]]:
            calculated_rankings[inst] = calculated_rankings[sorted_insts[i - 1]]
        else:
            calculated_rankings[inst] = rank
        rank += 1

    return {
        'institutions': institutions,
        'challenges': challenges,
        'totals': totals,
        'rankings': rankings,
        'calculated_totals': calculated_totals,
        'calculated_rankings': calculated_rankings,
        'raw_df': df,
    }


#Given the fact that the original final results document has multiple totals row, these are needed to remove it
def find_total_rows(doc_df):
    total_mask = doc_df['Rule'].astype(str).str.upper().str.contains('TOTAL POINTS')
    total_indices = doc_df.index[total_mask].tolist()
    return total_indices

def clean_duplicate_total_rows(doc_df):
    total_indices = find_total_rows(doc_df)
    
    if len(total_indices) <= 1:
        # No duplicates or only one TOTAL row
        return doc_df, total_indices[-1] if total_indices else None
    
    # Keep only the last TOTAL row
    last_total_idx = total_indices[-1]
    
    # Create a list of indices to drop (all total rows except the last)
    indices_to_drop = [idx for idx in total_indices if idx != last_total_idx]
    
    # Drop the duplicate total rows
    cleaned_df = doc_df.drop(index=indices_to_drop).reset_index(drop=True)
    
    # Find the new index of the kept TOTAL row
    new_total_mask = cleaned_df['Rule'].astype(str).str.upper().str.contains('TOTAL POINTS')
    new_total_indices = cleaned_df.index[new_total_mask].tolist()
    new_last_total_idx = new_total_indices[-1] if new_total_indices else None
    
    print(f"Removed {len(indices_to_drop)} duplicate TOTAL row(s). Keeping row {last_total_idx + 1} as the final TOTAL.")
    
    return cleaned_df, new_last_total_idx


def identify_cell_errors(unconfirmed_doc):
    try:
        parsed = parse_hierarchical_document(unconfirmed_doc.storedPath)
        if parsed is None:
            return []

        error_cells = []
        
        #Check each institution's total
        for inst in parsed['institutions']:
            reported = parsed['totals'].get(inst, 0.0)
            calculated = parsed['calculated_totals'].get(inst, 0.0)
            if abs(calculated - reported) >= 0.01:
                error_cells.append({
                    'institution': inst,
                    'calculated_value': calculated,
                    'reported_value': reported,
                    'difference': round(calculated - reported, 2),
                    'error_type': 'Total Mismatch',
                    'message': f"Total mismatch: Calculated {calculated} vs Reported {reported}",
                })
                
        points_lookup = _get_points_rule_lookup()

        #Compare scores to point rules
        for challenge in parsed['challenges']:
            for event in challenge['events']:
                for rule in event['rules']:
                    max_pts = _get_max_points_for_label(rule['label'], points_lookup)

                    for inst in parsed['institutions']:
                        v = rule['scores'].get(inst)

                        if v is None or (isinstance(v, float) and np.isnan(v)):
                            continue 

                        if v < 0:
                            error_cells.append({
                                'institution': inst,
                                'challenge':   challenge['name'],
                                'event':       event['name'],
                                'rule':        rule['label'],
                                'value':       v,
                                'max_points':  max_pts,
                                'error_type':  'Out of Range',
                                'message':     (
                                    f"Score {v} for '{rule['label']}' is below the minimum of 0"
                                    + (f" under '{event['name']}'" if event['name'] else '')
                                ),
                            })

                        elif max_pts is not None and v > max_pts:
                            error_cells.append({
                                'institution': inst,
                                'challenge':   challenge['name'],
                                'event':       event['name'],
                                'rule':        rule['label'],
                                'value':       v,
                                'max_points':  max_pts,
                                'error_type':  'Out of Range',
                                'message':     (
                                    f"Score {v} exceeds the maximum of {max_pts} for '{rule['label']}'"
                                    + (f" under '{event['name']}'" if event['name'] else '')
                                ),
                            })
    
        return error_cells
    except Exception as e:
        print(f"Error in identify_cell_errors: {e}")
        return []


def identify_all_cell_errors(unconfirmed_doc):
    try:
        parsed = parse_hierarchical_document(unconfirmed_doc.storedPath)
        if parsed is None:
            return []

        all_errors = list(identify_cell_errors(unconfirmed_doc))

        for challenge in parsed['challenges']:
            for event in challenge['events']:
                for rule in event['rules']:
                    for inst in parsed['institutions']:
                        v = rule['scores'].get(inst)
                        if v is None or (isinstance(v, float) and np.isnan(v)):
                            all_errors.append({
                                'institution': inst,
                                'challenge':   challenge['name'],
                                'event':       event['name'],
                                'rule':        rule['label'],
                                'value':       v,
                                'error_type':  'Missing Value',
                                'message':     (
                                    f"Missing value for '{rule['label']}'"
                                    + (f" under '{event['name']}'" if event['name'] else '')
                                ),
                            })
        return all_errors
    except Exception as e:
        print(f"Error in identify_all_cell_errors: {e}")
        return []


def get_system_calculated_results(document):
    try:
        parsed = parse_hierarchical_document(document.storedPath)
        if parsed is None:
            return None, []

        points_lookup = _get_points_rule_lookup()
        institutions  = parsed['institutions']

        for challenge in parsed['challenges']:
            for event in challenge['events']:
                for rule in event['rules']:
                    max_pts = _get_max_points_for_label(rule['label'], points_lookup)
                    rule['original_scores'] = dict(rule['scores'])  # reported values before clamping
                    rule['max_points']       = max_pts
                    for inst in institutions:
                        v = rule['scores'].get(inst, 0.0)
                        if v < 0:
                            v = 0.0
                        if max_pts is not None and v > max_pts:
                            v = max_pts
                        rule['scores'][inst] = v

        corrected_totals = {inst: 0.0 for inst in institutions}
        for challenge in parsed['challenges']:
            for event in challenge['events']:
                for rule in event['rules']:
                    for inst in institutions:
                        corrected_totals[inst] += rule['scores'].get(inst, 0.0)
        corrected_totals = {inst: round(v, 2) for inst, v in corrected_totals.items()}

        sorted_insts = sorted(institutions, key=lambda i: corrected_totals[i], reverse=True)
        corrected_rankings = {}
        rank = 1
        for i, inst in enumerate(sorted_insts):
            if i > 0 and corrected_totals[inst] == corrected_totals[sorted_insts[i - 1]]:
                corrected_rankings[inst] = corrected_rankings[sorted_insts[i - 1]]
            else:
                corrected_rankings[inst] = rank
            rank += 1

        parsed['calculated_totals']   = corrected_totals
        parsed['calculated_rankings'] = corrected_rankings

        comparison_data = []
        for inst in institutions:
            original  = parsed['totals'].get(inst, 0.0)
            corrected = corrected_totals[inst]
            diff      = round(corrected - original, 2)
            comparison_data.append({
                'institution':     inst,
                'original_value':  original,
                'corrected_value': corrected,
                'difference':      diff,
                'matches':         abs(diff) < 0.01,
            })

        return parsed, comparison_data
    except Exception as e:
        print(f"Error calculating system results: {e}")
        import traceback; traceback.print_exc()
        return None, []

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
    doc_data = {
        "id":             document.documentID,
        "filename":       document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":     document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw":  document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":       ext or "FILE",
        "viewUrl":        url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":      url_for('scoretaker_views.delete_document', documentID=document.documentID),
    }

    try:
        if not os.path.exists(document.storedPath):
            raise Exception(f"File not found at path: {document.storedPath}")

        parsed = parse_hierarchical_document(document.storedPath)
        if parsed is None:
            raise Exception("Could not parse document")

        errors = identify_all_cell_errors(document)

        table_data = {
            'institutions':       parsed['institutions'],
            'challenges':         parsed['challenges'],
            'totals':             parsed['totals'],
            'rankings':           parsed['rankings'],
            'calculated_totals':  parsed['calculated_totals'],
            'calculated_rankings': parsed['calculated_rankings'],
            'errors':             errors,
            'total_errors':       len(errors),
        }

    except Exception as e:
        print(f"Error loading document: {e}")
        import traceback; traceback.print_exc()
        table_data = {
            'institutions': [],
            'challenges': [],
            'totals': {},
            'rankings': {},
            'calculated_totals': {},
            'calculated_rankings': {},
            'errors': [],
            'total_errors': 0,
            'load_error': str(e),
        }

    return render_template('judge/review_document.html', document=doc_data, table_data=table_data)

@judge_views.route('/judge/debug-points/<int:documentID>')
@jwt_required()
def debug_points(documentID):
    document = get_score_document(documentID)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    lookup = _get_points_rule_lookup()
    parsed = parse_hierarchical_document(document.storedPath)

    doc_labels = []
    if parsed:
        for challenge in parsed["challenges"]:
            for event in challenge["events"]:
                for rule in event["rules"]:
                    normalised = _normalise_label(rule["label"])
                    resolved = _get_max_points_for_label(rule["label"], lookup)
                    doc_labels.append({
                        "raw_label":   rule["label"],
                        "normalised":  normalised,
                        "max_pts":     resolved,
                        "lookup_hit":  resolved is not None,
                    })

    return jsonify({
        "points_rule_lookup": {k: v for k, v in lookup.items()},
        "document_labels":    doc_labels,
    })


#Modified from scoretaker
@judge_views.route('/judge/document/<int:documentID>', methods=['GET'])
@jwt_required()
def download_document(documentID):
    doc = ScoreDocument.query.filter_by(
        documentID=documentID
    ).first_or_404()
    
    filename = os.path.basename(doc.storedPath)
    root = os.path.dirname(current_app.root_path)
    file_path = os.path.join(root, 'uploads', filename)
    
    if not os.path.isfile(file_path):
        abort(404, description=f"Document file not found: {doc.originalFilename}")
    
    return send_file(
        file_path,
        as_attachment=False,
        download_name=doc.originalFilename
    )
    
    
@judge_views.route('/judge/review/<int:documentID>/edit', methods=['GET', 'POST'])
@jwt_required()
def edit_score_document(documentID):
    document = get_score_document(documentID)

    ext = os.path.splitext(document.originalFilename)[1].lstrip('.').upper() if document.originalFilename else ''
    doc_data = {
        "id":             document.documentID,
        "filename":       document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":     document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw":  document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":       ext or "FILE",
        "viewUrl":        url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":      url_for('scoretaker_views.delete_document', documentID=document.documentID),
    }

    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not data or 'rows' not in data:
            return jsonify({"error": "Invalid request body. Expected JSON with a 'rows' key."}), 400

        try:
            file_ext = os.path.splitext(document.storedPath)[1].lower()

            # Read with the correct engine based on actual file extension
            engine_map = {
                '.xlsx': 'openpyxl',
                '.xls':  'xlrd',
                '.xlsm': 'openpyxl',
                '.xlsb': 'pyxlsb',
            }
            if file_ext in engine_map:
                existing_df = pd.read_excel(document.storedPath, engine=engine_map[file_ext])
            elif file_ext == '.csv':
                existing_df = pd.read_csv(document.storedPath)
            else:
                # Last-resort: let pandas sniff the engine
                existing_df = pd.read_excel(document.storedPath)

            columns = existing_df.columns.tolist()
            
            submitted_rows = data['rows']

            if len(submitted_rows) != len(existing_df):
                return jsonify({
                    "error": f"Row count mismatch: expected {len(existing_df)}, received {len(submitted_rows)}."
                }), 400

            if any(len(row) != len(columns) for row in submitted_rows):
                return jsonify({"error": "Column count mismatch in one or more rows."}), 400

            def coerce(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return val if val not in ('', None) else np.nan

            coerced_rows = [[coerce(cell) for cell in row] for row in submitted_rows]
            updated_df = pd.DataFrame(coerced_rows, columns=columns)

            if file_ext == '.csv':
                updated_df.to_csv(document.storedPath, index=False)
            elif file_ext == '.xls':
                updated_df.to_excel(document.storedPath, index=False, engine='xlwt')
            elif file_ext in ('.xlsm', '.xlsb'):
                new_path = os.path.splitext(document.storedPath)[0] + '.xlsx'
                updated_df.to_excel(new_path, index=False, engine='openpyxl')
                document.storedPath = new_path
                db.session.commit()
            else:
                updated_df.to_excel(document.storedPath, index=False, engine='openpyxl')

            return jsonify({"message": "Document saved successfully."}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to save document: {str(e)}"}), 500

    try:
        parsed = parse_hierarchical_document(document.storedPath)
        if parsed is None:
            raise Exception("Could not parse document")

        table_data = {
            'institutions':      parsed['institutions'],
            'challenges':        parsed['challenges'],
            'totals':            parsed['totals'],
            'rankings':          parsed['rankings'],
            'calculated_totals': parsed['calculated_totals'],
        }
    except Exception as e:
        table_data = {
            'institutions': [],
            'challenges': [],
            'totals': {},
            'rankings': {},
            'calculated_totals': {},
            'load_error': str(e),
        }

    return render_template('judge/edit_document.html', document=doc_data, table_data=table_data)

@judge_views.route('/judge/review/<int:documentID>/system-results', methods=['GET'])
@jwt_required()
def view_system_results(documentID):
    document = get_score_document(documentID)

    ext = os.path.splitext(document.originalFilename)[1].lstrip('.').upper() if document.originalFilename else ''
    doc_data = {
        "id":             document.documentID,
        "filename":       document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":     document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw":  document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":       ext or "FILE",
        "viewUrl":        url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":      url_for('scoretaker_views.delete_document', documentID=document.documentID),
    }

    try:
        parsed, comparison_data = get_system_calculated_results(document)

        if parsed is None:
            raise Exception("Could not calculate system results")

        table_data = {
            'institutions':        parsed['institutions'],
            'challenges':          parsed['challenges'],
            'totals':              parsed['totals'],
            'rankings':            parsed['rankings'],
            'calculated_totals':   parsed['calculated_totals'],
            'calculated_rankings': parsed['calculated_rankings'],
            'is_system_results':   True,
            'comparison_data':     comparison_data,
            'original_filename':   document.originalFilename,
        }

    except Exception as e:
        print(f"Error loading system results: {e}")
        import traceback; traceback.print_exc()
        table_data = {
            'institutions': [],
            'challenges': [],
            'totals': {},
            'rankings': {},
            'calculated_totals': {},
            'calculated_rankings': {},
            'is_system_results': True,
            'comparison_data': [],
            'load_error': str(e),
        }

    return render_template('judge/system_results.html', document=doc_data, table_data=table_data)


@judge_views.route('/judge/finalize/<int:documentID>', methods=['POST'])
@jwt_required()
def finalize_document(documentID):
    document = get_score_document(documentID)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    try:
        data = request.get_json(silent=True) or {}
        use_system_results = data.get('use_system_results', False)

        parsed, _ = get_system_calculated_results(document)
        if parsed is None:
            return jsonify({"error": "Could not parse document"}), 500

        # Reconstruct a flat DataFrame in the original format for export
        institutions = parsed['institutions']
        rows = []

        for challenge in parsed['challenges']:
            # Challenge header row
            rows.append({'Rule': challenge['name'], **{inst: '' for inst in institutions}})

            for event in challenge['events']:
                if event['name']:
                    rows.append({'Rule': event['name'], **{inst: '' for inst in institutions}})

                for rule in event['rules']:
                    if use_system_results:
                        row = {'Rule': rule['label'], **rule['scores']}
                    else:
                        row = {'Rule': rule['label'], **rule['scores']}
                    rows.append(row)

                rows.append({'Rule': '', **{inst: '' for inst in institutions}})

        totals_row = {'Rule': 'TOTAL POINTS'}
        rankings_row = {'Rule': 'RANKING'}
        for inst in institutions:
            if use_system_results:
                totals_row[inst] = parsed['calculated_totals'].get(inst, 0.0)
                rankings_row[inst] = parsed['calculated_rankings'].get(inst, '')
            else:
                totals_row[inst] = parsed['totals'].get(inst, 0.0)
                rankings_row[inst] = parsed['rankings'].get(inst, '')

        rows.append(totals_row)
        rows.append(rankings_row)

        final_df = pd.DataFrame(rows, columns=['Rule'] + institutions)

        # Save the document as the final version
        base, ext = os.path.splitext(document.storedPath)
        final_path = f"{base}_final{ext}"
        if ext.lower() in ('.xlsx', '.xls'):
            final_df.to_excel(final_path, index=False)
        else:
            final_df.to_csv(final_path, index=False)

        document.confirmed = True
        db.session.commit()

        return jsonify({
            "message": "Document successfully finalized",
            "document_id": documentID,
            "used_system_results": use_system_results,
            "redirect_url": url_for('judge_views.review_scores'),
        }), 200

    except Exception as e:
        print(f"Error finalizing document: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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