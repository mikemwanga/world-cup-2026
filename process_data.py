import random
from pathlib import Path
from datetime import datetime

import pandas as pd

from scoring_rules import (
    EXACT_SCORE_POINTS,
    CORRECT_OUTCOME_AND_GD_POINTS,
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

USER_COLUMNS = ["participant_id", "username", "first_signed_in_at"]
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ID_LENGTH = 6

DISPLAY_TEAM_ALIASES = {
    "Bosnia and Herzegovina": "Bosnia-Hzgv",
    "Korea Republic": "Korea Re.",
}

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


def display_team_name(name):
    cleaned = str(name).strip()
    return DISPLAY_TEAM_ALIASES.get(cleaned, cleaned)


def display_match_label(label_or_team_a, team_b=None):
    if team_b is not None:
        return f"{display_team_name(label_or_team_a)} vs {display_team_name(team_b)}"
    parts = str(label_or_team_a).split(" vs ", 1)
    if len(parts) == 2:
        return f"{display_team_name(parts[0])} vs {display_team_name(parts[1])}"
    return display_team_name(label_or_team_a)


def ensure_data_files():
    DATA_DIR.mkdir(exist_ok=True)

    if not USERS_FILE.exists():
        pd.DataFrame(
            [
                {
                    "participant_id": ADMIN_USER_ID,
                    "username": ADMIN_USERNAME,
                    "first_signed_in_at": "",
                }
            ]
        ).to_csv(USERS_FILE, index=False)

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


def _merge_scores_into_matches(df, scores):
    if scores.empty:
        return df
    if "match_id" in scores.columns:
        return df.merge(
            scores[["match_id", "actual_score_a", "actual_score_b"]],
            on="match_id",
            how="left",
            suffixes=("", "_score"),
        ).assign(
            actual_score_a=lambda d: d["actual_score_a_score"].combine_first(d["actual_score_a"]),
            actual_score_b=lambda d: d["actual_score_b_score"].combine_first(d["actual_score_b"]),
        ).drop(columns=["actual_score_a_score", "actual_score_b_score"])
    scores = scores.copy()
    scores["match_label"] = scores["match_label"].astype(str).str.strip()
    return df.merge(
        scores[["match_label", "actual_score_a", "actual_score_b"]],
        on="match_label",
        how="left",
        suffixes=("", "_score"),
    ).assign(
        actual_score_a=lambda d: d["actual_score_a_score"].combine_first(d["actual_score_a"]),
        actual_score_b=lambda d: d["actual_score_b_score"].combine_first(d["actual_score_b"]),
    ).drop(columns=["actual_score_a_score", "actual_score_b_score"])


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
        if not scores.empty:
            df = _merge_scores_into_matches(df, scores)

    df["is_finished"] = df["actual_score_a"].notna() & df["actual_score_b"].notna()
    return df


def load_scores():
    df = pd.read_csv(SCORES_FILE)
    if "match_id" in df.columns:
        numeric_ids = pd.to_numeric(df["match_id"], errors="coerce")
        if numeric_ids.notna().all():
            df["match_id"] = numeric_ids.astype(int)
        else:
            df = df.drop(columns=["match_id"])
    df["match_label"] = df["match_label"].astype(str).str.strip()
    df["actual_score_a"] = pd.to_numeric(df["actual_score_a"], errors="coerce")
    df["actual_score_b"] = pd.to_numeric(df["actual_score_b"], errors="coerce")
    return df


def _generate_unique_id(existing):
    while True:
        candidate = "".join(random.choices(ID_ALPHABET, k=ID_LENGTH))
        if candidate not in existing:
            return candidate


def _load_users_from_secrets():
    """Read the optional `users` registry from Streamlit secrets (deployment)."""
    try:
        import streamlit as st

        if not hasattr(st, "secrets") or "users" not in st.secrets:
            return []
        entries = []
        for item in st.secrets["users"]:
            data = dict(item)
            pid = str(data.get("participant_id", "")).strip().upper()
            if not pid:
                continue
            entries.append(
                {
                    "participant_id": pid,
                    "username": str(data.get("username", "") or "").strip(),
                    "first_signed_in_at": str(data.get("first_signed_in_at", "") or "").strip(),
                }
            )
        return entries
    except Exception:
        return []


def load_users():
    if USERS_FILE.exists():
        df = pd.read_csv(USERS_FILE)
    else:
        df = pd.DataFrame(columns=USER_COLUMNS)

    for col in USER_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["participant_id"] = df["participant_id"].fillna("").astype(str).str.strip().str.upper()
    df["username"] = df["username"].fillna("").astype(str).str.strip()
    df["first_signed_in_at"] = df["first_signed_in_at"].fillna("").astype(str).str.strip()
    df = df[df["participant_id"] != ""]

    records = {}
    for _, row in df.iterrows():
        records[row["participant_id"]] = {
            "participant_id": row["participant_id"],
            "username": row["username"],
            "first_signed_in_at": row["first_signed_in_at"],
        }

    # Merge in any IDs defined in Streamlit secrets (used on deployment).
    for entry in _load_users_from_secrets():
        pid = entry["participant_id"]
        if pid not in records:
            records[pid] = entry
        else:
            if not records[pid].get("username"):
                records[pid]["username"] = entry.get("username", "")
            if not records[pid].get("first_signed_in_at"):
                records[pid]["first_signed_in_at"] = entry.get("first_signed_in_at", "")

    if ADMIN_USER_ID not in records:
        records[ADMIN_USER_ID] = {
            "participant_id": ADMIN_USER_ID,
            "username": ADMIN_USERNAME,
            "first_signed_in_at": "",
        }

    out = pd.DataFrame(list(records.values()))
    for col in USER_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[USER_COLUMNS].reset_index(drop=True)


def is_username_taken(username, users=None):
    cleaned = str(username).strip().lower()
    if not cleaned:
        return False
    if users is None:
        users = load_users()
    existing = users["username"].astype(str).str.strip().str.lower().tolist()
    return cleaned in existing


def assign_login_id(participant_id=""):
    """Admin action: create a new login ID (blank username). Returns (ok, message, id)."""
    participant_id = str(participant_id).strip().upper()
    users = load_users()
    existing = set(users["participant_id"].astype(str).str.upper().tolist())

    if participant_id:
        if participant_id in existing:
            return False, "That ID already exists.", participant_id
    else:
        participant_id = _generate_unique_id(existing | {ADMIN_USER_ID})

    new_row = {"participant_id": participant_id, "username": "", "first_signed_in_at": ""}
    updated = pd.concat([users, pd.DataFrame([new_row])], ignore_index=True)
    updated = updated.drop_duplicates(subset=["participant_id"], keep="first")
    updated.to_csv(USERS_FILE, index=False)
    return True, "Login ID assigned.", participant_id


def set_username(participant_id, username):
    """First-login action: lock in a unique username for an assigned ID."""
    participant_id = str(participant_id).strip().upper()
    username = str(username).strip()

    if not username:
        return False, "Enter a username."

    users = load_users()
    if participant_id not in users["participant_id"].values:
        return False, "Participant ID not found. Contact the admin."

    current = str(
        users.loc[users["participant_id"] == participant_id, "username"].iloc[0]
    ).strip()
    if current:
        return False, "A username is already set for this ID."
    if is_username_taken(username, users):
        return False, "That username is already taken. Please choose another."

    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    users.loc[users["participant_id"] == participant_id, "username"] = username
    users.loc[users["participant_id"] == participant_id, "first_signed_in_at"] = now
    users.to_csv(USERS_FILE, index=False)
    return True, "Username set."


def users_to_toml():
    """Render the current users registry as a TOML snippet for deployment secrets."""
    users = load_users()
    lines = ["users = ["]
    for _, row in users.iterrows():
        pid = str(row["participant_id"]).strip().replace('"', '\\"')
        uname = str(row["username"]).strip().replace('"', '\\"')
        first = str(row["first_signed_in_at"]).strip().replace('"', '\\"')
        lines.append(
            f'    {{ participant_id = "{pid}", username = "{uname}", '
            f'first_signed_in_at = "{first}" }},'
        )
    lines.append("]")
    return "\n".join(lines)


def _first_signed_in_for_user(participant_id, users, predictions):
    participant_id = participant_id.strip().upper()
    user_row = users[users["participant_id"] == participant_id]
    if not user_row.empty:
        stored = str(user_row["first_signed_in_at"].iloc[0]).strip()
        if stored:
            return stored
    if predictions.empty:
        return "—"
    user_preds = predictions[predictions["participant_id"].astype(str).str.upper() == participant_id]
    if user_preds.empty or "saved_at" not in user_preds.columns:
        return "—"
    return str(user_preds["saved_at"].min())


PREDICTION_COLUMNS = [
    "participant_id",
    "username",
    "match_id",
    "match_label",
    "predicted_score_a",
    "predicted_score_b",
    "predicted_outcome",
    "saved_at",
]


def load_predictions():
    if PREDICTIONS_CSV.exists():
        df = pd.read_csv(PREDICTIONS_CSV)
        result = df if not df.empty else pd.DataFrame(columns=PREDICTION_COLUMNS)
        if df.empty and PREDICTIONS_XLSX.exists():
            try:
                xlsx_df = pd.read_excel(PREDICTIONS_XLSX)
                if not xlsx_df.empty:
                    save_predictions(result)
            except FileNotFoundError:
                pass
        return result
    try:
        return pd.read_excel(PREDICTIONS_XLSX)
    except FileNotFoundError:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)


def filter_actual_predictions(predictions, matches):
    if predictions.empty or matches.empty:
        return predictions.iloc[0:0].copy()

    valid_ids = set(matches["match_id"].astype(int))
    df = predictions.copy()
    df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce")
    df = df[df["match_id"].notna()]
    df["match_id"] = df["match_id"].astype(int)
    df = df[df["match_id"].isin(valid_ids)]
    return df.reset_index(drop=True)


def save_predictions(df):
    df.to_csv(PREDICTIONS_CSV, index=False)
    df.to_excel(PREDICTIONS_XLSX, index=False)


def save_scores(df):
    df.to_csv(SCORES_FILE, index=False)


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
    if predicted_outcome != actual_outcome:
        return WRONG_PREDICTION_POINTS

    if (actual_a - actual_b) == (predicted_a - predicted_b):
        return CORRECT_OUTCOME_AND_GD_POINTS

    return CORRECT_OUTCOME_POINTS


def build_leaderboard(predictions, matches):
    columns = [
        "Rank",
        "Participant ID",
        "Username",
        "Matches Predicted",
        "Correct Predictions",
        "Total Points",
    ]
    if predictions.empty:
        return pd.DataFrame(columns=columns)

    users = load_users()
    username_by_id = users.set_index("participant_id")["username"].astype(str).str.strip().to_dict()

    scores = []
    for pid, group in predictions.groupby("participant_id"):
        total = 0
        matches_predicted = 0
        correct_predictions = 0
        pid_key = str(pid).strip().upper()
        name = username_by_id.get(pid_key, "")
        if not name and "username" in group.columns:
            name = str(group["username"].iloc[0]).strip()
        for _, row in group.iterrows():
            match_row = matches[matches["match_id"] == int(row["match_id"])]
            if match_row.empty:
                continue
            matches_predicted += 1
            points = compute_score(row, match_row.iloc[0])
            if points is not None:
                total += points
                if points > 0:
                    correct_predictions += 1
        scores.append(
            {
                "Participant ID": pid_key,
                "Username": name or "—",
                "Matches Predicted": matches_predicted,
                "Correct Predictions": correct_predictions,
                "Total Points": total,
            }
        )

    if not scores:
        return pd.DataFrame(columns=columns)

    leaderboard = pd.DataFrame(scores).sort_values(
        by=["Total Points", "Correct Predictions", "Matches Predicted"],
        ascending=False,
    )
    leaderboard.insert(0, "Rank", range(1, len(leaderboard) + 1))
    return leaderboard


def _prediction_performance(row, match_row):
    if not match_row["is_finished"]:
        return {
            "points": None,
            "win": "—",
            "draw": "—",
            "goals": "—",
            "result": "Pending",
        }

    points = compute_score(row, match_row)
    actual_a = int(match_row["actual_score_a"])
    actual_b = int(match_row["actual_score_b"])
    predicted_a = int(row["predicted_score_a"])
    predicted_b = int(row["predicted_score_b"])
    actual_outcome = get_prediction_key(actual_a, actual_b)
    predicted_outcome = get_prediction_key(predicted_a, predicted_b)
    win_correct = actual_outcome in ["A", "B"] and predicted_outcome == actual_outcome
    draw_correct = actual_outcome == "Draw" and predicted_outcome == "Draw"
    goals_correct = (predicted_a == actual_a) and (predicted_b == actual_b)

    return {
        "points": points if points is not None else 0,
        "win": "✅" if win_correct else "❌",
        "draw": "✅" if draw_correct else "❌",
        "goals": "✅" if goals_correct else "❌",
        "result": f"{actual_a}-{actual_b}",
    }


def build_admin_user_summary(predictions, matches):
    users = load_users()
    registered = users[
        (users["username"] != "")
        & (users["participant_id"] != ADMIN_USER_ID)
    ]
    participant_ids = registered["participant_id"].tolist()

    rows = []
    for pid in sorted(participant_ids):
        pid = str(pid).strip().upper()
        user_row = users[users["participant_id"] == pid]
        username = user_row["username"].iloc[0] if not user_row.empty else ""
        if not username and not predictions.empty:
            user_preds_lookup = predictions[predictions["participant_id"].astype(str).str.upper() == pid]
            if not user_preds_lookup.empty and "username" in user_preds_lookup.columns:
                username = str(user_preds_lookup["username"].iloc[0]).strip()

        user_preds = (
            predictions[predictions["participant_id"].astype(str).str.upper() == pid]
            if not predictions.empty
            else predictions
        )
        matches_predicted = len(user_preds)
        correct = 0
        wrong = 0
        pending = 0
        total_points = 0

        for _, pred in user_preds.iterrows():
            match_row = matches[matches["match_id"] == int(pred["match_id"])]
            if match_row.empty:
                continue
            match_row = match_row.iloc[0]
            perf = _prediction_performance(pred, match_row)
            if perf["points"] is None:
                pending += 1
            elif perf["points"] > 0:
                correct += 1
                total_points += perf["points"]
            else:
                wrong += 1
                total_points += perf["points"]

        rows.append(
            {
                "Participant ID": pid,
                "Username": username or "—",
                "First signed in": _first_signed_in_for_user(pid, users, predictions),
                "Matches predicted": matches_predicted,
                "Correct": correct,
                "Wrong": wrong,
                "Pending": pending,
                "Total points": total_points,
            }
        )

    return pd.DataFrame(rows)


def build_admin_user_detail(participant_id, predictions, matches):
    participant_id = participant_id.strip().upper()
    if predictions.empty:
        return pd.DataFrame()

    user_preds = predictions[
        predictions["participant_id"].astype(str).str.upper() == participant_id
    ].copy()
    if user_preds.empty:
        return pd.DataFrame()

    user_preds["saved_at"] = pd.to_datetime(user_preds["saved_at"], errors="coerce")
    user_preds = user_preds.sort_values(["saved_at", "match_id"], na_position="last")

    rows = []
    for _, pred in user_preds.iterrows():
        match_row = matches[matches["match_id"] == int(pred["match_id"])]
        if match_row.empty:
            continue
        match_row = match_row.iloc[0]
        perf = _prediction_performance(pred, match_row)
        saved_at = pred["saved_at"]
        rows.append(
            {
                "Match ID": int(pred["match_id"]),
                "Match": match_row["match_label"],
                "Predicted at": saved_at.strftime("%Y-%m-%d %H:%M") if pd.notna(saved_at) else "—",
                "Prediction": f"{int(pred['predicted_score_a'])}-{int(pred['predicted_score_b'])}",
                "Actual result": perf["result"],
                "Win": perf["win"],
                "Draw": perf["draw"],
                "Goals": perf["goals"],
                "Points": perf["points"] if perf["points"] is not None else "Pending",
            }
        )

    return pd.DataFrame(rows)
