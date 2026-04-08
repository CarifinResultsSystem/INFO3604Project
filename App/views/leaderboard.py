from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from App.controllers import get_all_users_json
from App.database import db
from App.models import ScoreDocument, Season

import io
import os
import re
import pandas as pd
import numpy as np

leaderboard_views = Blueprint('leaderboard_views', __name__, template_folder='../templates')


# ---------------------------------------------------------------------------
# Inline parse helper (mirrors judge_views so leaderboard has no circular dep)
# ---------------------------------------------------------------------------

def _all_inst_empty(row, inst_cols):
    for col in inst_cols:
        val = row[col]
        if pd.notna(val) and str(val).strip() != '':
            return False
    return True


def _parse_document(doc):
    """
    Parse a ScoreDocument in the same way judge views do,
    so leaderboard and judge agree on the spreadsheet structure.
    """
    if not doc.fileData:
        return None

    ext = os.path.splitext(doc.originalFilename)[1].lower()
    buf = io.BytesIO(doc.fileData)

    try:
        # Match judge behavior first
        if ext in ('.xlsx', '.xls'):
            df = pd.read_excel(buf, header=1)
        else:
            df = pd.read_csv(buf, header=1)
    except Exception as e:
        print(f"PARSE ERROR reading doc {doc.documentID}: {e}")
        return None

    if df is None or df.empty:
        print(f"PARSE ERROR: empty dataframe for doc {doc.documentID}")
        return None

    # Match judge parser: rename first column to Rule
    df = df.rename(columns={df.columns[0]: 'Rule'})

    # Remove repeated institution header row if present
    df = df[df['Rule'].astype(str).str.strip() != 'Event / Institution'].reset_index(drop=True)

    if 'Rule' not in df.columns:
        print(f"PARSE ERROR: no Rule column for doc {doc.documentID}")
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

            # If scores appear on an event row directly, preserve them
            if current_event is None and current_challenge is not None:
                current_event = {
                    'name': rule_str,
                    'rules': [],
                    'event_scores': scores,
                    '_direct': True
                }
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
            if event.get('rules'):
                for rule in event['rules']:
                    for inst in institutions:
                        v = rule['scores'].get(inst, 0.0)
                        if isinstance(v, float) and np.isnan(v):
                            v = 0.0
                        calculated_totals[inst] += v
            elif event.get('event_scores'):
                for inst in institutions:
                    v = event['event_scores'].get(inst, 0.0)
                    if isinstance(v, float) and np.isnan(v):
                        v = 0.0
                    calculated_totals[inst] += v

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

    print(
        f"PARSED OK doc {doc.documentID}: "
        f"{len(institutions)} institutions, {len(challenges)} challenges"
    )

    return {
        'institutions': institutions,
        'challenges': challenges,
        'totals': totals,
        'rankings': rankings,
        'calculated_totals': calculated_totals,
        'calculated_rankings': calculated_rankings,
    }
    
def _doc_season_year(doc):
    if not getattr(doc, 'seasonID', None):
        return None

    season = db.session.get(Season, doc.seasonID)
    return season.year if season else None


# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------

@leaderboard_views.route('/leaderboard', methods=['GET'])
def get_leaderboard_page():
    return render_template('user/leaderboard.html')


# ---------------------------------------------------------------------------
# API — leaderboard data from confirmed documents
# ---------------------------------------------------------------------------
@leaderboard_views.route('/api/leaderboard', methods=['GET'])
def get_leaderboard_api():
    """
    Returns aggregated leaderboard data from confirmed ScoreDocuments.
    """

    # Gather confirmed documents only
    confirmed_docs = db.session.scalars(
        db.select(ScoreDocument).filter_by(confirmed=True)
    ).all()

    if not confirmed_docs:
        return jsonify({
            "season_year": None,
            "available_years": [],
            "challenges": [],
            "leaderboard": [],
            "message": "No confirmed results yet."
        })

    # Group confirmed docs by season year
    docs_by_year = {}
    for doc in confirmed_docs:
        year = _doc_season_year(doc)
        if year is None:
            continue
        docs_by_year.setdefault(year, []).append(doc)

    if not docs_by_year:
        return jsonify({
            "season_year": None,
            "available_years": [],
            "challenges": [],
            "leaderboard": [],
            "message": "No confirmed results could be matched to a season."
        })

    available_years = sorted(docs_by_year.keys(), reverse=True)

    print("CONFIRMED DOCS:")
    for d in confirmed_docs:
        season = db.session.get(Season, d.seasonID) if getattr(d, "seasonID", None) else None
        print(
            "docID=", d.documentID,
            "filename=", d.originalFilename,
            "confirmed=", d.confirmed,
            "seasonID=", getattr(d, "seasonID", None),
            "season_year=", season.year if season else None,
        )

    # Pick requested year if valid
    requested_year = request.args.get("year", type=int)

    if requested_year is not None:
        if requested_year not in docs_by_year:
            return jsonify({
                "season_year": requested_year,
                "available_years": available_years,
                "challenges": [],
                "leaderboard": [],
                "message": f"No confirmed results found for season {requested_year}."
            })
        target_year = requested_year
    else:
        target_year = available_years[0]

    # FIX: define target_docs
    target_docs = docs_by_year[target_year]

    print("TARGET YEAR:", target_year)
    print("TARGET DOC COUNT:", len(target_docs))

    # Aggregate institution -> challenge -> points
    agg = {}
    challenge_names = []

    for doc in target_docs:
        parsed = _parse_document(doc)

        print(
            "PARSE CHECK:",
            "docID=", doc.documentID,
            "filename=", doc.originalFilename,
            "seasonID=", getattr(doc, "seasonID", None),
            "resolved_year=", _doc_season_year(doc),
            "parsed=", parsed is not None
        )

        if parsed is None:
            continue

        for challenge in parsed.get("challenges", []):
            c_name = (challenge.get("name") or "").strip()
            if not c_name:
                continue

            if c_name not in challenge_names:
                challenge_names.append(c_name)

            for inst in parsed.get("institutions", []):
                agg.setdefault(inst, {})
                challenge_pts = 0.0

                for event in challenge.get("events", []):
                    for rule in event.get("rules", []):
                        v = rule.get("scores", {}).get(inst, 0.0)
                        if isinstance(v, float) and np.isnan(v):
                            v = 0.0
                        challenge_pts += v

                agg[inst][c_name] = round(
                    agg[inst].get(c_name, 0.0) + challenge_pts, 2
                )

    if not agg:
        return jsonify({
            "season_year": target_year,
            "available_years": available_years,
            "challenges": [],
            "leaderboard": [],
            "message": "Documents found but could not be parsed."
        })

    # Build totals
    totals = {
        inst: round(sum(challenge_points.values()), 2)
        for inst, challenge_points in agg.items()
    }

    sorted_insts = sorted(totals.keys(), key=lambda inst: totals[inst], reverse=True)

    leaderboard = []
    next_rank = 1

    for i, inst in enumerate(sorted_insts):
        if i > 0 and totals[inst] == totals[sorted_insts[i - 1]]:
            assigned_rank = leaderboard[-1]["rank"]
        else:
            assigned_rank = next_rank

        leaderboard.append({
            "rank": assigned_rank,
            "institution": inst,
            "total_points": totals[inst],
            "challenge_points": agg[inst],
        })

        next_rank += 1

    # Optional event/challenge filter
    event_filter = (request.args.get("event") or "").strip().lower()
    if event_filter and event_filter != "overall":
        filtered = []

        for entry in leaderboard:
            matched_key = next(
                (
                    key for key in entry["challenge_points"].keys()
                    if key.lower() == event_filter or event_filter in key.lower()
                ),
                None
            )

            pts = entry["challenge_points"].get(matched_key, 0.0) if matched_key else 0.0

            filtered.append({
                **entry,
                "filtered_points": pts
            })

        filtered.sort(key=lambda x: x["filtered_points"], reverse=True)

        reranked = []
        next_rank = 1

        for i, entry in enumerate(filtered):
            if i > 0 and entry["filtered_points"] == filtered[i - 1]["filtered_points"]:
                assigned_rank = reranked[-1]["rank"]
            else:
                assigned_rank = next_rank

            reranked.append({
                "rank": assigned_rank,
                "institution": entry["institution"],
                "total_points": entry["total_points"],
                "challenge_points": entry["challenge_points"],
            })

            next_rank += 1

        leaderboard = reranked

    return jsonify({
        "season_year": target_year,
        "available_years": available_years,
        "challenges": challenge_names,
        "leaderboard": leaderboard,
    })