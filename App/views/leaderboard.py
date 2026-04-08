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
    """Return parsed dict with institutions, challenges, calculated_totals, calculated_rankings."""
    if not doc.fileData:
        return None

    ext = os.path.splitext(doc.originalFilename)[1].lower()
    buf = io.BytesIO(doc.fileData)

    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(buf, header=1)
    else:
        df = pd.read_csv(buf, header=1)

    if df.empty or 'Rule' not in df.columns:
        return None

    institutions = [c for c in df.columns if c != 'Rule']
    challenges = []
    totals = {}
    current_challenge = None
    current_event = None

    for _, row in df.iterrows():
        rule_val = row['Rule']
        rule_str = str(rule_val).strip() if pd.notna(rule_val) else ''
        if rule_str == '':
            continue

        rule_upper = rule_str.upper()

        if 'TOTAL POINTS' in rule_upper:
            for inst in institutions:
                v = row[inst]
                totals[inst] = float(v) if pd.notna(v) and str(v).strip() != '' else 0.0
            continue

        if rule_upper.startswith('RANKING'):
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
                if not current_challenge['events'] or not current_challenge['events'][-1].get('_direct'):
                    direct_event = {'name': '', 'rules': [], '_direct': True}
                    current_challenge['events'].append(direct_event)
                    current_event = direct_event
                current_event['rules'].append(rule_entry)

    # Calculate totals from scores
    calculated_totals = {inst: 0.0 for inst in institutions}
    for challenge in challenges:
        for event in challenge['events']:
            for rule in event['rules']:
                for inst in institutions:
                    v = rule['scores'].get(inst, 0.0)
                    if isinstance(v, float) and np.isnan(v):
                        v = 0.0
                    calculated_totals[inst] += v
    calculated_totals = {inst: round(v, 2) for inst, v in calculated_totals.items()}

    # Build rankings
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
        'calculated_totals': calculated_totals,
        'calculated_rankings': calculated_rankings,
    }


def _doc_season_year(doc):
    """
    Resolve which season year a confirmed ScoreDocument belongs to.
    Prefers a direct seasonID FK on the document (if it exists),
    falls back to the year of uploadedOn.
    """
    # If the model has a seasonID column, use it
    if hasattr(doc, 'seasonID') and doc.seasonID:
        season = db.session.get(Season, doc.seasonID)
        if season:
            return season.year

    # Fall back to upload year
    if doc.uploadedOn:
        upload_year = doc.uploadedOn.year
        season = Season.query.filter_by(year=upload_year).first()
        if season:
            return season.year
        return upload_year  # return bare year even without a Season row

    return None


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
    Returns aggregated leaderboard data from the most recent season
    that has at least one confirmed ScoreDocument.

    Query params:
        year (int, optional) – override to fetch a specific season year
        event (str, optional) – challenge name filter (case-insensitive)

    Response shape:
    {
        "season_year": 2025,
        "available_years": [2025, 2024],
        "challenges": ["Overall", "100m Sprint", ...],
        "leaderboard": [
            {
                "rank": 1,
                "institution": "UWI St. Augustine",
                "total_points": 1482.0,
                "challenge_points": {
                    "100m Sprint": 320.0,
                    ...
                }
            },
            ...
        ]
    }
    """
    # -- Gather all confirmed documents
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

    # -- Map each doc to its season year
    docs_by_year: dict[int, list] = {}
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

    # -- Determine target year
    try:
        requested_year = int(request.args.get('year', 0))
    except (ValueError, TypeError):
        requested_year = 0

    if requested_year and requested_year in docs_by_year:
        target_year = requested_year
    else:
        target_year = available_years[0]  # most recent season with confirmed docs

    target_docs = docs_by_year[target_year]

    # -- Aggregate scores across all confirmed docs for the target year
    # institution -> challenge -> points
    agg: dict[str, dict[str, float]] = {}

    challenge_names: list[str] = []  # ordered, de-duped

    for doc in target_docs:
        parsed = _parse_document(doc)
        if parsed is None:
            continue

        for challenge in parsed['challenges']:
            c_name = challenge['name'].strip()
            if c_name and c_name not in challenge_names:
                challenge_names.append(c_name)

            for inst in parsed['institutions']:
                if inst not in agg:
                    agg[inst] = {}

                challenge_pts = 0.0
                for event in challenge['events']:
                    for rule in event['rules']:
                        v = rule['scores'].get(inst, 0.0)
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

    # -- Build totals and rank
    totals = {inst: round(sum(pts.values()), 2) for inst, pts in agg.items()}
    sorted_insts = sorted(totals.keys(), key=lambda i: totals[i], reverse=True)

    leaderboard = []
    rank = 1
    for i, inst in enumerate(sorted_insts):
        if i > 0 and totals[inst] == totals[sorted_insts[i - 1]]:
            assigned_rank = leaderboard[-1]['rank']
        else:
            assigned_rank = rank
        rank += 1

        leaderboard.append({
            "rank": assigned_rank,
            "institution": inst,
            "total_points": totals[inst],
            "challenge_points": agg[inst],
        })

    # -- Optional challenge filter for the event tab
    event_filter = request.args.get('event', '').strip().lower()
    if event_filter and event_filter != 'overall':
        # Re-rank by challenge-specific points
        filtered = []
        for entry in leaderboard:
            matched_key = next(
                (k for k in entry['challenge_points']
                 if k.lower() == event_filter or event_filter in k.lower()),
                None
            )
            pts = entry['challenge_points'].get(matched_key, 0.0) if matched_key else 0.0
            filtered.append({**entry, "filtered_points": pts})

        filtered.sort(key=lambda x: x['filtered_points'], reverse=True)
        rank = 1
        for i, entry in enumerate(filtered):
            if i > 0 and entry['filtered_points'] == filtered[i - 1]['filtered_points']:
                entry['rank'] = filtered[i - 1]['rank']
            else:
                entry['rank'] = rank
            rank += 1

        leaderboard = filtered

    return jsonify({
        "season_year": target_year,
        "available_years": available_years,
        "challenges": challenge_names,
        "leaderboard": leaderboard,
    })