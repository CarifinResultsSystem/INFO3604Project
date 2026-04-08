from flask import Blueprint, render_template, jsonify, request
from App.database import db
from App.models import ScoreDocument, Season

import io
import os
import pandas as pd
import numpy as np

leaderboard_views = Blueprint('leaderboard_views', __name__, template_folder='../templates')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_inst_empty(row, inst_cols):
    for col in inst_cols:
        val = row[col]
        if pd.notna(val) and str(val).strip() != '':
            return False
    return True


def _parse_document(doc):
    if not doc.fileData:
        return None

    ext = os.path.splitext(doc.originalFilename)[1].lower()
    buf = io.BytesIO(doc.fileData)

    try:
        # Read raw sheet with no assumed header
        if ext in ('.xlsx', '.xls'):
            raw_df = pd.read_excel(buf, header=None)
        else:
            raw_df = pd.read_csv(buf, header=None)
    except Exception as e:
        print(f"PARSE ERROR reading doc {doc.documentID}: {e}")
        return None

    if raw_df is None or raw_df.empty:
        print(f"PARSE ERROR: empty raw dataframe for doc {doc.documentID}")
        return None

    # Find the actual header row
    # Accept either:
    # - Event / Institution   (template files)
    # - Rule                  (finalized files)
    header_row_idx = None
    for i in range(len(raw_df)):
        first_cell = raw_df.iat[i, 0]
        first_text = str(first_cell).strip() if pd.notna(first_cell) else ""
        if first_text in ("Event / Institution", "Rule"):
            header_row_idx = i
            break

    if header_row_idx is None:
        print(f"PARSE ERROR: could not find header row for doc {doc.documentID}")
        return None

    # Build dataframe using the detected header row
    header_values = raw_df.iloc[header_row_idx].tolist()
    df = raw_df.iloc[header_row_idx + 1:].copy()
    df.columns = header_values
    df = df.reset_index(drop=True)

    # Normalize first column name to Rule
    df = df.rename(columns={df.columns[0]: "Rule"})

    # Drop repeated header rows if they appear later in the file
    df = df[df["Rule"].astype(str).str.strip() != "Event / Institution"].reset_index(drop=True)

    # Remove completely empty columns
    df = df.dropna(axis=1, how="all")

    institutions = [
        c for c in df.columns
        if c != "Rule"
        and pd.notna(c)
        and str(c).strip() != ""
        and not str(c).startswith("Unnamed:")
    ]

    if not institutions:
        print(f"PARSE ERROR: no valid institution columns for doc {doc.documentID}")
        print("COLUMNS FOUND:", list(df.columns))
        return None

    challenges = []
    totals = {}
    rankings = {}
    current_challenge = None
    current_event = None

    for _, row in df.iterrows():
        rule_val = row["Rule"]
        rule_str = str(rule_val).strip() if pd.notna(rule_val) else ""

        if rule_str == "":
            current_event = None
            continue

        rule_upper = rule_str.upper()

        if "TOTAL POINTS" in rule_upper:
            for inst in institutions:
                v = row[inst]
                totals[inst] = float(v) if pd.notna(v) and str(v).strip() != "" else 0.0
            continue

        if rule_upper.startswith("RANKING"):
            for inst in institutions:
                v = row[inst]
                rankings[inst] = v if pd.notna(v) and str(v).strip() != "" else ""
            continue

        if _all_inst_empty(row, institutions):
            if current_challenge is None or rule_str == rule_str.upper():
                current_challenge = {"name": rule_str, "events": []}
                challenges.append(current_challenge)
                current_event = None
            else:
                current_event = {"name": rule_str, "rules": []}
                if current_challenge is not None:
                    current_challenge["events"].append(current_event)
        else:
            scores = {}
            for inst in institutions:
                v = row[inst]
                scores[inst] = float(v) if pd.notna(v) and str(v).strip() != "" else 0.0

            if current_event is None and current_challenge is not None:
                current_event = {
                    "name": rule_str,
                    "rules": [],
                    "event_scores": scores,
                    "_direct": True
                }
                current_challenge["events"].append(current_event)
            else:
                rule_entry = {"label": rule_str, "scores": scores}
                if current_event is not None:
                    current_event["rules"].append(rule_entry)
                elif current_challenge is not None:
                    if not current_challenge["events"] or current_challenge["events"][-1].get("_direct"):
                        direct_event = {"name": "", "rules": [], "_direct": True}
                        current_challenge["events"].append(direct_event)
                        current_event = direct_event
                    current_event["rules"].append(rule_entry)

    calculated_totals = {inst: 0.0 for inst in institutions}
    for challenge in challenges:
        for event in challenge["events"]:
            if event.get("rules"):
                for rule in event["rules"]:
                    for inst in institutions:
                        v = rule["scores"].get(inst, 0.0)
                        if isinstance(v, float) and np.isnan(v):
                            v = 0.0
                        calculated_totals[inst] += v
            elif event.get("event_scores"):
                for inst in institutions:
                    v = event["event_scores"].get(inst, 0.0)
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

    print(f"PARSED OK doc {doc.documentID}: {institutions}")

    return {
        "institutions": institutions,
        "challenges": challenges,
        "totals": totals,
        "rankings": rankings,
        "calculated_totals": calculated_totals,
        "calculated_rankings": calculated_rankings,
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
# API route
# ---------------------------------------------------------------------------

@leaderboard_views.route('/api/leaderboard', methods=['GET'])
def get_leaderboard_api():
    all_seasons = Season.query.order_by(Season.year.desc()).all()
    available_years = [s.year for s in all_seasons]

    if not available_years:
        return jsonify({
            "season_year": None,
            "available_years": [],
            "challenges": [],
            "leaderboard": [],
            "message": "No seasons have been created yet."
        })

    confirmed_docs = db.session.scalars(
        db.select(ScoreDocument).filter_by(confirmed=True)
    ).all()

    docs_by_year = {}
    for doc in confirmed_docs:
        year = _doc_season_year(doc)
        if year is None:
            continue
        docs_by_year.setdefault(year, []).append(doc)

    requested_year = request.args.get("year", type=int)

    if requested_year is not None:
        if requested_year not in available_years:
            return jsonify({
                "season_year": requested_year,
                "available_years": available_years,
                "challenges": [],
                "leaderboard": [],
                "message": f"Season {requested_year} does not exist."
            })
        target_year = requested_year
    else:
        target_year = available_years[0]

    if target_year not in docs_by_year:
        return jsonify({
            "season_year": target_year,
            "available_years": available_years,
            "challenges": [],
            "leaderboard": [],
            "message": f"No confirmed results found for season {target_year}."
        })

    # Use only the latest confirmed document for the selected season
    target_docs = docs_by_year[target_year]
    latest_doc = max(target_docs, key=lambda d: d.uploadedOn or 0)

    parsed = _parse_document(latest_doc)

    print(
        "USING LATEST DOC:",
        "docID=", latest_doc.documentID,
        "filename=", latest_doc.originalFilename,
        "seasonID=", getattr(latest_doc, "seasonID", None),
        "resolved_year=", _doc_season_year(latest_doc),
        "parsed=", parsed is not None
    )

    if parsed is None:
        return jsonify({
            "season_year": target_year,
            "available_years": available_years,
            "challenges": [],
            "leaderboard": [],
            "message": "Latest confirmed document could not be parsed."
        })

    agg = {}
    challenge_names = []

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
                if event.get("rules"):
                    for rule in event["rules"]:
                        v = rule.get("scores", {}).get(inst, 0.0)
                        if isinstance(v, float) and np.isnan(v):
                            v = 0.0
                        challenge_pts += v
                elif event.get("event_scores"):
                    v = event["event_scores"].get(inst, 0.0)
                    if isinstance(v, float) and np.isnan(v):
                        v = 0.0
                    challenge_pts += v

            agg[inst][c_name] = round(challenge_pts, 2)

    if not agg:
        return jsonify({
            "season_year": target_year,
            "available_years": available_years,
            "challenges": [],
            "leaderboard": [],
            "message": "Latest confirmed document parsed, but no leaderboard values were produced."
        })

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