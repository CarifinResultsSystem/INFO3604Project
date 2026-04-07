import io
import os
import re
from flask import Blueprint, render_template, url_for, jsonify, request, abort, send_file, current_app
from flask_jwt_extended import jwt_required, current_user
from App.database import db
from App.controllers import get_score_document, get_all_score_documents, get_unconfirmed_documents, get_unconfirmed_documents_count
from App.models import ScoreDocument, PointsRules, AutomatedResult, Event
import pandas as pd
import numpy as np

judge_views = Blueprint('judge_views', __name__, template_folder='../templates')

def _doc_to_dataframe(document, header=1):
    """Return a DataFrame from a ScoreDocument's in-DB binary content."""
    if not document.fileData:
        raise ValueError(f"Document {document.documentID} has no file data.")

    ext = os.path.splitext(document.originalFilename)[1].lower()
    buf = io.BytesIO(document.fileData)

    if ext in ('.xlsx', '.xls'):
        return pd.read_excel(buf, header=header)
    else:
        return pd.read_csv(buf, header=header)

def _dataframe_to_bytes(df, ext, index=False, header=False):
    """Serialise a DataFrame back to bytes matching the original file extension."""
    buf = io.BytesIO()
    ext = ext.lower()
    if ext in ('.xlsx', '.xlsm', '.xlsb', '.xls'):
        df.to_excel(buf, index=index, header=header, engine='openpyxl')
    else:
        df.to_csv(buf, index=index, header=header)
    buf.seek(0)
    return buf.read()

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


def _get_event_rules_lookup():
    event_lookup = {}   # event_key -> label_key -> entry
    global_lookup = {}  # label_key -> entry  (team/category rules shared across events)
    try:
        events = Event.query.all()
        for ev in events:
            ev_key = re.sub(r'\s+', ' ', ev.eventName).strip().lower()
            event_lookup[ev_key] = {}
            for pr in (ev.points_rules or []):
                if pr.ruleType == 'individual':
                    # "Event Win Points" — placement values specific to this event
                    label_key = 'event win points'
                elif pr.ruleType == 'team' and pr.category:
                    label_key = re.sub(r'\s+', ' ', pr.category).strip().lower()
                else:
                    label_key = re.sub(r'\s+', ' ', pr.label or '').strip().lower() if pr.label else None
                if not label_key:
                    continue

                # Update event-level entry
                ev_entry = event_lookup[ev_key].setdefault(label_key, {'values': set(), 'max': 0, 'is_exact': False})
                ev_entry['values'].add(pr.points)
                if pr.points > ev_entry['max']:
                    ev_entry['max'] = pr.points

                # Also update the global (cross-event) fallback for team/category rules
                if pr.ruleType != 'individual':
                    gl_entry = global_lookup.setdefault(label_key, {'values': set(), 'max': 0, 'is_exact': False})
                    gl_entry['values'].add(pr.points)
                    if pr.points > gl_entry['max']:
                        gl_entry['max'] = pr.points

        # Mark is_exact on all entries
        for ev_key, rules in event_lookup.items():
            for lk, entry in rules.items():
                entry['is_exact'] = len(entry['values']) > 1
        for lk, entry in global_lookup.items():
            entry['is_exact'] = len(entry['values']) > 1

    except Exception as e:
        print(f"Warning: could not build event rules lookup: {e}")

    return event_lookup, global_lookup


def _get_rule_entry(rule_label, event_name, event_lookup, global_lookup):
    """
    Return the validation entry for a rule, scoped to the specific event.
    Lookup order:
      1. event_lookup[event_key][label_key]   — exact event + label match
      2. global_lookup[label_key]              — cross-event team/category rule
      3. None
    """
    label_key = _normalise_label(rule_label)
    ev_key    = re.sub(r'\s+', ' ', event_name).strip().lower() if event_name else ''

    # 1. Per-event match
    ev_rules = event_lookup.get(ev_key, {})
    if label_key in ev_rules:
        return ev_rules[label_key]
    # Partial label match within this event
    partial = [(k, v) for k, v in ev_rules.items() if label_key in k or k in label_key]
    if partial:
        return max(partial, key=lambda kv: kv[1]['max'])[1]

    # 2. Global fallback (team/category rules)
    if label_key in global_lookup:
        return global_lookup[label_key]
    partial = [(k, v) for k, v in global_lookup.items() if label_key in k or k in label_key]
    if partial:
        return max(partial, key=lambda kv: kv[1]['max'])[1]

    return None


# Thin wrapper kept for any callers that only need the ceiling value
def _get_max_points_for_label(rule_label, event_name, event_lookup, global_lookup):
    entry = _get_rule_entry(rule_label, event_name, event_lookup, global_lookup)
    return entry['max'] if entry else None

def _parse_dataframe(df):
    """Parse a pre-loaded DataFrame and return the hierarchical structure."""
    df = df.rename(columns={df.columns[0]: 'Rule'})
    df = df[df['Rule'].astype(str).str.strip() != 'Event / Institution'].reset_index(drop=True)

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
            current_event = None
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

            # Event-level total row — open a new event but don't add to summation
            if current_event is None and current_challenge is not None:
                current_event = {'name': rule_str, 'rules': [], 'event_scores': scores, '_direct': True}
                current_challenge['events'].append(current_event)
            else:
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
            if event['rules']:
                # Sum from individual rules
                for rule in event['rules']:
                    for inst in institutions:
                        calculated_totals[inst] += rule['scores'].get(inst, 0.0)
            elif event.get('event_scores'):
                # No sub-rules — use the event-level total row directly
                for inst in institutions:
                    calculated_totals[inst] += event['event_scores'].get(inst, 0.0)
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


def parse_hierarchical_document(document):
    """Parse a ScoreDocument object. Reads from fileData (LargeBinary)."""
    df = _doc_to_dataframe(document, header=1)
    return _parse_dataframe(df)

def find_total_rows(doc_df):
    total_mask = doc_df['Rule'].astype(str).str.upper().str.contains('TOTAL POINTS')
    return doc_df.index[total_mask].tolist()


def clean_duplicate_total_rows(doc_df):
    total_indices = find_total_rows(doc_df)

    if len(total_indices) <= 1:
        # No duplicates or only one TOTAL row
        return doc_df, total_indices[-1] if total_indices else None

    last_total_idx = total_indices[-1]
    
    # Create a list of indices to drop (all total rows except the last)
    indices_to_drop = [idx for idx in total_indices if idx != last_total_idx]
    
    # Drop the duplicate total rows
    cleaned_df = doc_df.drop(index=indices_to_drop).reset_index(drop=True)

    new_total_mask = cleaned_df['Rule'].astype(str).str.upper().str.contains('TOTAL POINTS')
    new_total_indices = cleaned_df.index[new_total_mask].tolist()
    new_last_total_idx = new_total_indices[-1] if new_total_indices else None

    print(f"Removed {len(indices_to_drop)} duplicate TOTAL row(s). Keeping last as the final TOTAL.")
    return cleaned_df, new_last_total_idx


def identify_cell_errors(unconfirmed_doc):
    try:
        parsed = parse_hierarchical_document(unconfirmed_doc)
        if parsed is None:
            return []

        error_cells = []

        for inst in parsed['institutions']:
            reported   = parsed['totals'].get(inst, 0.0)
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

        event_lookup, global_lookup = _get_event_rules_lookup()
        all_maxes = [e['max'] for rules in event_lookup.values() for e in rules.values()]
        global_max = max(all_maxes) if all_maxes else None

        for challenge in parsed['challenges']:
            for event in challenge['events']:
                for rule in event['rules']:
                    entry = _get_rule_entry(rule['label'], event['name'], event_lookup, global_lookup)
                    if entry is not None:
                        max_pts  = entry['max']
                        is_exact = entry['is_exact']
                        valid_pts = entry['values']
                    else:
                        max_pts   = global_max
                        is_exact  = False
                        valid_pts = None

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
                                'message':     f"Score {v} for '{rule['label']}' is below the minimum of 0",
                            })
                        elif is_exact and valid_pts is not None and v not in valid_pts and v != 0:
                            # Placement-style rule: score must be one of the configured values.
                            valid_str = '/'.join(
                                str(int(p) if p == int(p) else p)
                                for p in sorted(valid_pts, reverse=True)
                            )
                            error_cells.append({
                                'institution': inst,
                                'challenge':   challenge['name'],
                                'event':       event['name'],
                                'rule':        rule['label'],
                                'value':       v,
                                'max_points':  max_pts,
                                'error_type':  'Invalid Score',
                                'message':     f"Score {v} for '{rule['label']}' under '{event['name']}' is not a valid placement value (expected one of {valid_str})",
                            })
                        elif not is_exact and max_pts is not None and v > max_pts:
                            error_cells.append({
                                'institution': inst,
                                'challenge':   challenge['name'],
                                'event':       event['name'],
                                'rule':        rule['label'],
                                'value':       v,
                                'max_points':  max_pts,
                                'error_type':  'Out of Range',
                                'message':     f"Score {v} exceeds the maximum of {max_pts} for '{rule['label']}' under '{event['name']}'",
                            })

        return error_cells
    except Exception as e:
        print(f"Error in identify_cell_errors: {e}")
        import traceback; traceback.print_exc()
        return []


def identify_all_cell_errors(unconfirmed_doc):
    try:
        parsed = parse_hierarchical_document(unconfirmed_doc)
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


def persist_errors_for_document(document):
    # Clear stale results for this document
    AutomatedResult.query.filter_by(
        participantID=str(document.documentID)
    ).delete(synchronize_session=False)

    errors = identify_all_cell_errors(document)

    for err in errors:
        record = AutomatedResult(
            score=float(err.get('value') or 0.0),
            participantID=str(document.documentID),
            eventID=1,
            pointsID=1,
        )
        record.numErrors        = 1
        record.errorType        = err.get('error_type', 'Unknown')
        record.errorDescription = err.get('message', '')
        record.errorCorrection  = (
            f"Clamped to max {err['max_points']}"
            if err.get('max_points') is not None
            and err.get('error_type') == 'Out of Range'
            else ''
        )
        db.session.add(record)

    db.session.commit()
    return errors

def get_system_calculated_results(document):
    try:
        parsed = parse_hierarchical_document(document)
        if parsed is None:
            return None, []

        event_lookup, global_lookup = _get_event_rules_lookup()
        all_maxes = [e['max'] for rules in event_lookup.values() for e in rules.values()]
        global_max = max(all_maxes) if all_maxes else None
        institutions = parsed['institutions']

        for challenge in parsed['challenges']:
            for event in challenge['events']:
                for rule in event['rules']:
                    entry = _get_rule_entry(rule['label'], event['name'], event_lookup, global_lookup)
                    if entry is not None:
                        max_pts   = entry['max']
                        is_exact  = entry['is_exact']
                        valid_pts = entry['values']
                    else:
                        max_pts   = global_max
                        is_exact  = False
                        valid_pts = None

                    rule['original_scores'] = dict(rule['scores'])
                    rule['max_points']       = max_pts
                    for inst in institutions:
                        v = rule['scores'].get(inst, 0.0)
                        if v < 0:
                            v = 0.0
                        if is_exact and valid_pts is not None and v not in valid_pts and v != 0:
                            # Clamp to the nearest valid placement value (round down)
                            lower = [p for p in valid_pts if p <= v]
                            v = max(lower) if lower else 0.0
                        elif not is_exact and max_pts is not None and v > max_pts:
                            v = max_pts
                        rule['scores'][inst] = v

        corrected_totals = {inst: 0.0 for inst in institutions}
        for challenge in parsed['challenges']:
            for event in challenge['events']:
                if event['rules']:
                    for rule in event['rules']:
                        for inst in institutions:
                            corrected_totals[inst] += rule['scores'].get(inst, 0.0)
                elif event.get('event_scores'):
                    for inst in institutions:
                        corrected_totals[inst] += event['event_scores'].get(inst, 0.0)
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
        if not document.fileData:
            raise Exception(f"Document {documentID} has no file data in the database.")

        parsed = parse_hierarchical_document(document)
        if parsed is None:
            raise Exception("Could not parse document")

        errors = persist_errors_for_document(document)

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
        errors = []
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

#Modified from scoretaker
@judge_views.route('/judge/document/<int:documentID>', methods=['GET'])
@jwt_required()
def download_document(documentID):
    #Serve the document directly from DB binary data
    doc = ScoreDocument.query.filter_by(documentID=documentID).first_or_404()

    if not doc.fileData:
        abort(404, description=f"No file data found for document: {doc.originalFilename}")

    ext = os.path.splitext(doc.originalFilename)[1].lower()
    mime_map = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls':  'application/vnd.ms-excel',
        '.csv':  'text/csv',
    }
    mimetype = mime_map.get(ext, 'application/octet-stream')

    return send_file(
        io.BytesIO(doc.fileData),
        mimetype=mimetype,
        as_attachment=False,
        download_name=doc.originalFilename,
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
            file_ext = os.path.splitext(document.originalFilename)[1].lower()
            submitted_rows = data['rows']

            # Read raw bytes from DB into a DataFrame (no header parsing)
            raw_buf = io.BytesIO(document.fileData)
            if file_ext in ('.xlsx', '.xls', '.xlsm', '.xlsb'):
                raw_df = pd.read_excel(raw_buf, header=None)
            else:
                raw_df = pd.read_csv(raw_buf, header=None)

            raw_rows = raw_df.values.tolist()

            header_label = str(raw_rows[1][0]).strip() if len(raw_rows) > 1 else 'Event / Institution'
            remaining_raw = raw_rows[1:]


            header_positions = [
                i for i, r in enumerate(remaining_raw)
                if str(r[0]).strip() == header_label
            ]

            final_rows = [raw_rows[0]]
            submitted_idx = 0
            for i, raw_row in enumerate(remaining_raw):
                if i in header_positions:
                    final_rows.append(raw_row)
                else:
                    if submitted_idx < len(submitted_rows):
                        final_rows.append(submitted_rows[submitted_idx])
                        submitted_idx += 1

            n_cols = len(raw_rows[1]) if len(raw_rows) > 1 else len(submitted_rows[0])
            final_rows = [(row + [''] * n_cols)[:n_cols] for row in final_rows]

            updated_df = pd.DataFrame(final_rows)

            # Serialise back to bytes and persist in DB
            out_ext = '.xlsx' if file_ext in ('.xlsm', '.xlsb', '.xls') else file_ext
            new_bytes = _dataframe_to_bytes(updated_df, out_ext, index=False, header=False)

            document.fileData = new_bytes
            # Update stored filename extension if format was normalised
            if out_ext != file_ext:
                base = os.path.splitext(document.storedFilename)[0]
                document.storedFilename = base + out_ext
                base_orig = os.path.splitext(document.originalFilename)[0]
                document.originalFilename = base_orig + out_ext

            db.session.commit()

            return jsonify({"message": "Document saved successfully."}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to save document: {str(e)}"}), 500

    try:
        parsed = parse_hierarchical_document(document)
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
                    row = {'Rule': rule['label'], **rule['scores']}
                    rows.append(row)

                rows.append({'Rule': '', **{inst: '' for inst in institutions}})

        totals_row   = {'Rule': 'TOTAL POINTS'}
        rankings_row = {'Rule': 'RANKING'}
        for inst in institutions:
            if use_system_results:
                totals_row[inst]   = parsed['calculated_totals'].get(inst, 0.0)
                rankings_row[inst] = parsed['calculated_rankings'].get(inst, '')
            else:
                totals_row[inst]   = parsed['totals'].get(inst, 0.0)
                rankings_row[inst] = parsed['rankings'].get(inst, '')

        rows.append(totals_row)
        rows.append(rankings_row)

        final_df = pd.DataFrame(rows, columns=['Rule'] + institutions)

        # Serialise final DataFrame back into the DB record
        file_ext = os.path.splitext(document.originalFilename)[1].lower()
        out_ext  = '.xlsx' if file_ext in ('.xls', '.xlsm', '.xlsb') else file_ext
        document.fileData = _dataframe_to_bytes(final_df, out_ext, index=False, header=True)

        document.confirmed = True
        # Mark corresponding AutomatedResult rows as confirmed too
        AutomatedResult.query.filter_by(
            participantID=str(documentID)
        ).update({'confirmed': True}, synchronize_session=False)
        db.session.commit()

        return jsonify({
            "message": "Document successfully finalized",
            "document_id": documentID,
            "used_system_results": use_system_results,
            "redirect_url":        url_for('judge_views.review_scores'),
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