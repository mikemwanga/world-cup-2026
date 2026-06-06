from pathlib import Path
from datetime import datetime

import pandas as pd

from scoring_rules import (
    EXACT_SCORE_POINTS,
    CORRECT_OUTCOME_POINTS,
    WRONG_PREDICTION_POINTS,
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MATCHES_FILE = DATA_DIR / "matches.csv"
DATA_FIFA_FILE = DATA_DIR / "fifa-world-cup-2026.csv"
ORIGINAL_FIFA_FILE = ROOT / "fifa-world-cup-2026-original.csv"
USERS_FILE = DATA_DIR / "users.csv"
SCORES_FILE = DATA_DIR / "scores.csv"
PREDICTIONS_CSV = DATA_DIR / "predictions.csv"
PREDICTIONS_XLSX = DATA_DIR / "predictions.xlsx"
ADMIN_USER_ID = "ADMIN01"
ADMIN_USERNAME = "Admin"

DEFAULT_MATCHES = [
    {
        "team_a": "Brazil",
        "team_b": "Argentina",
        "match_date": "2026-06-10 20:00",
        "prediction_deadline": "2026-06-10 19:00",
        "actual_score_a": 3,
        "actual_score_b": 1,
    },
    {
        "team_a": "France",
        "team_b": "Germany",
        "match_date": "2026-06-11 18:00",
        "prediction_deadline": "2026-06-11 17:00",
        "actual_score_a": 2,
        "actual_score_b": 2,
    },
    {
        "team_a": "Spain",
        "team_b": "England",
        "match_date": "2026-06-12 20:00",
        "prediction_deadline": "2026-06-12 19:00",
        "actual_score_a": None,
        "actual_score_b": None,
    },
    {
        "team_a": "Portugal",
        "team_b": "Netherlands",
        "match_date": "2026-06-13 16:00",
        "prediction_deadline": "2026-06-13 15:00",
        "actual_score_a": None,
        "actual_score_b": None,
    },
    {
        "team_a": "Japan",
        "team_b": "Canada",
        "match_date": "2026-06-14 14:00",
        "prediction_deadline": "2026-06-14 13:00",
        "actual_score_a": None,
        "actual_score_b": None,
    },
]

DEFAULT_USER_IDS = [f"P{i:03d}" for i in range(1, 11)]


def ensure_data_files():
    DATA_DIR.mkdir(exist_ok=True)

    if not USERS_FILE.exists():
        users = pd.DataFrame(
            {
                "participant_id": DEFAULT_USER_IDS + [ADMIN_USER_ID],
                "username": ["" for _ in DEFAULT_USER_IDS] + [ADMIN_USERNAME],
            }
        )
        users.to_csv(USERS_FILE, index=False)
    else:
        users = pd.read_csv(USERS_FILE)
        if ADMIN_USER_ID not in users["participant_id"].astype(str).str.upper().values:
            users = pd.concat(
                [users,
                 pd.DataFrame({"participant_id": [ADMIN_USER_ID], "username": [ADMIN_USERNAME]})],
                ignore_index=True,
            )
            users.to_csv(USERS_FILE, index=False)

    if not MATCHES_FILE.exists():
        source_file = None
        if DATA_FIFA_FILE.exists():
            source_file = DATA_FIFA_FILE
        elif ORIGINAL_FIFA_FILE.exists():
            source_file = ORIGINAL_FIFA_FILE

        if source_file is not None:
            df = pd.read_csv(source_file)
            df = _normalize_matches_df(df)
            df.to_csv(MATCHES_FILE, index=False)
        else:
            matches = pd.DataFrame(DEFAULT_MATCHES)
            matches["match_id"] = range(1, len(matches) + 1)
            matches.to_csv(MATCHES_FILE, index=False)

    if not SCORES_FILE.exists():
        scores = pd.DataFrame(
            {
                "match_id": range(1, len(DEFAULT_MATCHES) + 1),
                "match_label": [f"{m['team_a']} vs {m['team_b']}" for m in DEFAULT_MATCHES],
                "actual_score_a": [m.get("actual_score_a", "") for m in DEFAULT_MATCHES],
                "actual_score_b": [m.get("actual_score_b", "") for m in DEFAULT_MATCHES],
            }
        )
        scores.to_csv(SCORES_FILE, index=False)

    if not PREDICTIONS_CSV.exists() or not PREDICTIONS_XLSX.exists():
        empty = pd.DataFrame(
            columns=[
                "participant_id",
                "username",
                "match_id",
                "match_label",
                "predicted_score_a",
                "predicted_score_b",
                "predicted_outcome",
                "saved_at",
            ]
        )
        empty.to_csv(PREDICTIONS_CSV, index=False)
        empty.to_excel(PREDICTIONS_XLSX, index=False)


def _normalize_matches_df(df):
    column_map = {}
    lower_map = {col.lower(): col for col in df.columns}

    if "match number" in lower_map:
        column_map[lower_map["match number"]] = "match_id"
    if "match_id" in lower_map:
        column_map[lower_map["match_id"]] = "match_id"
    if "round number" in lower_map:
        column_map[lower_map["round number"]] = "round_number"
    if "round_number" in lower_map:
        column_map[lower_map["round_number"]] = "round_number"
    if "date" in lower_map:
        column_map[lower_map["date"]] = "match_date"
    if "home team" in lower_map:
        column_map[lower_map["home team"]] = "team_a"
    if "away team" in lower_map:
        column_map[lower_map["away team"]] = "team_b"
    if "group" in lower_map:
        column_map[lower_map["group"]] = "group"
    if "location" in lower_map:
        column_map[lower_map["location"]] = "location"
    if "result" in lower_map:
        column_map[lower_map["result"]] = "result"
    if "prediction_deadline" in lower_map:
        column_map[lower_map["prediction_deadline"]] = "prediction_deadline"
    if "actual_score_a" in lower_map:
        column_map[lower_map["actual_score_a"]] = "actual_score_a"
    if "actual_score_b" in lower_map:
        column_map[lower_map["actual_score_b"]] = "actual_score_b"

    df = df.rename(columns=column_map)

    if "match_id" not in df.columns:
        df["match_id"] = pd.Series(range(1, len(df) + 1), index=df.index)
    df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce")
    # Fill missing match_id values with a per-row sequential index
    fallback_ids = pd.Series(range(1, len(df) + 1), index=df.index)
    df["match_id"] = df["match_id"].fillna(fallback_ids).astype(int)

    if "match_date" in df.columns:
        df["match_date"] = pd.to_datetime(df["match_date"], dayfirst=True, errors="coerce")
    else:
        raise ValueError("Match file must include a date column.")

    if "prediction_deadline" not in df.columns:
        df["prediction_deadline"] = df["match_date"] - pd.Timedelta(hours=1)
    else:
        df["prediction_deadline"] = pd.to_datetime(df["prediction_deadline"], dayfirst=True, errors="coerce")
        df["prediction_deadline"] = df["prediction_deadline"].fillna(df["match_date"] - pd.Timedelta(hours=1))

    # Preserve round labels (they may be numeric like 1,2,3 or text like 'Round of 32')
    if "round_number" not in df.columns:
        df["round_number"] = "1"
    # Normalize to string and strip whitespace
    df["round_number"] = df["round_number"].astype(str).str.strip().fillna("1")

    df["group"] = df.get("group", pd.Series("All", index=df.index)).astype(str).fillna("All").str.strip()
    df.loc[df["group"] == "", "group"] = "All"

    df["location"] = df.get("location", pd.Series("", index=df.index)).astype(str).fillna("").str.strip()

    df["team_a"] = df["team_a"].astype(str).str.strip()
    df["team_b"] = df["team_b"].astype(str).str.strip()

    if "actual_score_a" in df.columns and "actual_score_b" in df.columns:
        df["actual_score_a"] = pd.to_numeric(df["actual_score_a"], errors="coerce")
        df["actual_score_b"] = pd.to_numeric(df["actual_score_b"], errors="coerce")
    elif "result" in df.columns:
        result_scores = df["result"].astype(str).str.extract(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
        df["actual_score_a"] = pd.to_numeric(result_scores[0], errors="coerce")
        df["actual_score_b"] = pd.to_numeric(result_scores[1], errors="coerce")
    else:
        df["actual_score_a"] = pd.NA
        df["actual_score_b"] = pd.NA

    df["match_label"] = (df["team_a"] + " vs " + df["team_b"]).str.strip()
    return df


def load_matches():
    source_file = MATCHES_FILE
    if DATA_FIFA_FILE.exists():
        source_file = DATA_FIFA_FILE
    elif ORIGINAL_FIFA_FILE.exists():
        source_file = ORIGINAL_FIFA_FILE

    df = pd.read_csv(source_file)
    df = _normalize_matches_df(df)

    if SCORES_FILE.exists():
        scores = load_scores()
        if "match_id" in scores.columns:
            df = df.merge(scores[["match_id", "actual_score_a", "actual_score_b"]], on="match_id", how="left", suffixes=("", "_score"))
        else:
            scores["match_label"] = scores["match_label"].astype(str).str.strip()
            df = df.merge(scores[["match_label", "actual_score_a", "actual_score_b"]], on="match_label", how="left", suffixes=("", "_score"))
        df["actual_score_a"] = df["actual_score_a_score"].combine_first(df["actual_score_a"])
        df["actual_score_b"] = df["actual_score_b_score"].combine_first(df["actual_score_b"])
        df = df.drop(columns=["actual_score_a_score", "actual_score_b_score"])

    df["is_finished"] = df["actual_score_a"].notna() & df["actual_score_b"].notna()
    return df


def load_scores():
    df = pd.read_csv(SCORES_FILE)
    if "match_id" in df.columns:
        df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce").astype(int)
    df["match_label"] = df["match_label"].astype(str).str.strip()
    df["actual_score_a"] = pd.to_numeric(df["actual_score_a"], errors="coerce")
    df["actual_score_b"] = pd.to_numeric(df["actual_score_b"], errors="coerce")
    return df


def load_users():
    df = pd.read_csv(USERS_FILE)
    df["participant_id"] = df["participant_id"].astype(str).str.upper()
    df["username"] = df["username"].fillna("")
    return df


def load_predictions():
    try:
        return pd.read_excel(PREDICTIONS_XLSX)
    except FileNotFoundError:
        return pd.DataFrame(
            columns=[
                "participant_id",
                "username",
                "match_id",
                "match_label",
                "predicted_score_a",
                "predicted_score_b",
                "predicted_outcome",
                "saved_at",
            ]
        )


def save_predictions(df):
    df.to_csv(PREDICTIONS_CSV, index=False)
    df.to_excel(PREDICTIONS_XLSX, index=False)


def save_scores(df):
    df.to_csv(SCORES_FILE, index=False)


def save_user_name(participant_id, username):
    df = load_users()
    participant_id = participant_id.strip().upper()
    if participant_id in df["participant_id"].values:
        df.loc[df["participant_id"] == participant_id, "username"] = username.strip()
        df.to_csv(USERS_FILE, index=False)
        return True
    return False


def get_prediction_key(score_a, score_b):
    if int(score_a) > int(score_b):
        return "A"
    if int(score_a) < int(score_b):
        return "B"
    return "Draw"


def add_or_update_prediction(participant_id, username, match_id, score_a, score_b, match_label):
    df = load_predictions()
    participant_id = participant_id.strip().upper()
    predicted_outcome = get_prediction_key(score_a, score_b)
    saved_at = datetime.now().isoformat(sep=" ", timespec="seconds")

    existing = df[(df["participant_id"] == participant_id) & (df["match_id"] == match_id)]
    if not existing.empty:
        df.loc[existing.index, ["predicted_score_a", "predicted_score_b", "predicted_outcome", "saved_at"]] = [
            score_a,
            score_b,
            predicted_outcome,
            saved_at,
        ]
    else:
        new_row = {
            "participant_id": participant_id,
            "username": username,
            "match_id": match_id,
            "match_label": match_label,
            "predicted_score_a": score_a,
            "predicted_score_b": score_b,
            "predicted_outcome": predicted_outcome,
            "saved_at": saved_at,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    save_predictions(df)
    return df


def compute_score(row, match_row):
    if not match_row["is_finished"]:
        return None

    actual_a = int(match_row["actual_score_a"])
    actual_b = int(match_row["actual_score_b"])
    predicted_a = int(row["predicted_score_a"])
    predicted_b = int(row["predicted_score_b"])

    if predicted_a == actual_a and predicted_b == actual_b:
        return EXACT_SCORE_POINTS

    actual_outcome = get_prediction_key(actual_a, actual_b)
    predicted_outcome = get_prediction_key(predicted_a, predicted_b)
    if predicted_outcome == actual_outcome:
        return CORRECT_OUTCOME_POINTS

    return WRONG_PREDICTION_POINTS


def build_leaderboard(predictions, matches):
    if predictions.empty:
        return pd.DataFrame(
            columns=["Rank", "Participant ID", "Name", "Total Points"]
        )

    scores = []
    for pid, group in predictions.groupby("participant_id"):
        total = 0
        name = group["username"].iloc[0] if "username" in group.columns else ""
        for _, row in group.iterrows():
            match_row = matches[matches["match_id"] == int(row["match_id"])]
            if not match_row.empty:
                points = compute_score(row, match_row.iloc[0])
                if points is not None:
                    total += points
        scores.append({"Participant ID": pid, "Name": name, "Total Points": total})

    leaderboard = pd.DataFrame(scores).sort_values(by="Total Points", ascending=False)
    leaderboard.insert(0, "Rank", range(1, len(leaderboard) + 1))
    return leaderboard
