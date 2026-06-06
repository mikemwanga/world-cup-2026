from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

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
USERS_REGISTRY_FILE = DATA_DIR / ".users.toml"
USERS_REGISTRY_EXAMPLE = DATA_DIR / "users.toml.example"
USERS_STATE_FILE = DATA_DIR / "users_state.toml"
SCORES_FILE = DATA_DIR / "scores.csv"
PREDICTIONS_CSV = DATA_DIR / "predictions.csv"
PREDICTIONS_XLSX = DATA_DIR / "predictions.xlsx"
ADMIN_USER_ID = "ADMIN01"
ADMIN_USERNAME = "Admin"

DEMO_ROUND = "Round0"
DEMO_KICKOFF_MINUTES = 20
DEMO_DEADLINE_MINUTES = 10
DEMO_MATCH_DEFINITIONS = [
    {
        "match_id": 9001,
        "group": "Group A",
        "team_a": "Demo Lions",
        "team_b": "Demo Tigers",
        "location": "Demo Stadium",
    },
    {
        "match_id": 9002,
        "group": "Group A",
        "team_a": "Demo Eagles",
        "team_b": "Demo Bears",
        "location": "Demo Stadium",
    },
    {
        "match_id": 9003,
        "group": "Group B",
        "team_a": "Demo Sharks",
        "team_b": "Demo Wolves",
        "location": "Demo Arena",
    },
    {
        "match_id": 9004,
        "group": "Group B",
        "team_a": "Demo Hawks",
        "team_b": "Demo Foxes",
        "location": "Demo Arena",
    },
]

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

    if not USERS_REGISTRY_EXAMPLE.exists():
        _write_users_registry_example()

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


def build_demo_matches(now=None):
    if now is None:
        now = datetime.now()
    kickoff = now + timedelta(minutes=DEMO_KICKOFF_MINUTES)
    deadline = now + timedelta(minutes=DEMO_DEADLINE_MINUTES)
    rows = []
    for match_def in DEMO_MATCH_DEFINITIONS:
        rows.append(
            {
                "match_id": match_def["match_id"],
                "round_number": DEMO_ROUND,
                "match_date": kickoff,
                "prediction_deadline": deadline,
                "location": match_def["location"],
                "team_a": match_def["team_a"],
                "team_b": match_def["team_b"],
                "group": match_def["group"],
                "result": "",
                "actual_score_a": pd.NA,
                "actual_score_b": pd.NA,
                "match_label": f"{match_def['team_a']} vs {match_def['team_b']}",
            }
        )
    return pd.DataFrame(rows)


def load_matches():
    source_file = MATCHES_FILE
    if DATA_FIFA_FILE.exists():
        source_file = DATA_FIFA_FILE
    elif ORIGINAL_FIFA_FILE.exists():
        source_file = ORIGINAL_FIFA_FILE

    df = pd.read_csv(source_file)
    df = _normalize_matches_df(df)
    demo_df = build_demo_matches()
    df = pd.concat([demo_df, df], ignore_index=True)

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


def _read_toml(path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _toml_escape(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _normalize_user_entry(entry):
    if not isinstance(entry, dict):
        return None
    participant_id = str(entry.get("participant_id", "")).strip().upper()
    if not participant_id:
        return None
    username = entry.get("username", "")
    if username is None:
        username = ""
    first_signed_in_at = entry.get("first_signed_in_at", "")
    if first_signed_in_at is None:
        first_signed_in_at = ""
    return {
        "participant_id": participant_id,
        "username": str(username).strip(),
        "first_signed_in_at": str(first_signed_in_at).strip(),
    }


def _parse_users_toml_data(data):
    users_data = data.get("users", [])
    entries = []

    if isinstance(users_data, list):
        for item in users_data:
            normalized = _normalize_user_entry(item)
            if normalized:
                entries.append(normalized)
    elif isinstance(users_data, dict):
        for participant_id, value in users_data.items():
            if isinstance(value, dict):
                normalized = _normalize_user_entry(
                    {
                        "participant_id": participant_id,
                        "username": value.get("username", ""),
                        "first_signed_in_at": value.get("first_signed_in_at", ""),
                    }
                )
            else:
                normalized = _normalize_user_entry(
                    {"participant_id": participant_id, "username": value}
                )
            if normalized:
                entries.append(normalized)

    return entries


def _load_users_registry_entries():
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "users" in st.secrets:
            secret_users = st.secrets["users"]
            if isinstance(secret_users, list):
                entries = [
                    normalized
                    for item in secret_users
                    if (normalized := _normalize_user_entry(dict(item)))
                ]
                if entries:
                    return entries
            elif isinstance(secret_users, dict):
                return _parse_users_toml_data({"users": secret_users})
    except Exception:
        pass

    for path in (USERS_REGISTRY_FILE, USERS_REGISTRY_EXAMPLE):
        if path.exists():
            entries = _parse_users_toml_data(_read_toml(path))
            if entries:
                return entries

    return [
        {
            "participant_id": participant_id,
            "username": "" if participant_id != ADMIN_USER_ID else ADMIN_USERNAME,
            "first_signed_in_at": "",
        }
        for participant_id in DEFAULT_USER_IDS + [ADMIN_USER_ID]
    ]


def _load_users_state_entries():
    if not USERS_STATE_FILE.exists():
        return {}

    data = _read_toml(USERS_STATE_FILE)
    state = {}
    for participant_id, value in data.items():
        if not isinstance(value, dict):
            continue
        normalized = _normalize_user_entry(
            {
                "participant_id": participant_id,
                "username": value.get("username", ""),
                "first_signed_in_at": value.get("first_signed_in_at", ""),
            }
        )
        if normalized:
            state[normalized["participant_id"]] = normalized
    return state


def _save_users_state(state):
    lines = []
    for participant_id in sorted(state):
        entry = state[participant_id]
        username = entry.get("username", "").strip()
        first_signed_in_at = entry.get("first_signed_in_at", "").strip()
        if not username and not first_signed_in_at:
            continue
        lines.append(f"[{participant_id}]")
        if username:
            lines.append(f'username = "{_toml_escape(username)}"')
        if first_signed_in_at:
            lines.append(f'first_signed_in_at = "{_toml_escape(first_signed_in_at)}"')
        lines.append("")
    USERS_STATE_FILE.write_text("\n".join(lines).strip() + ("\n" if lines else ""), encoding="utf-8")


def _write_users_registry_example():
    example = """# Copy to data/.users.toml for local dev, or paste the users array into
# Streamlit Cloud secrets (Settings -> Secrets).

users = [
    { participant_id = "P001", username = "MJ" },
    { participant_id = "P002", username = "PS2" },
    { participant_id = "YWNWA", username = "" },
    { participant_id = "ADMIN01", username = "Admin" },
]
"""
    USERS_REGISTRY_EXAMPLE.write_text(example, encoding="utf-8")


def load_users():
    registry = _load_users_registry_entries()
    state = _load_users_state_entries()
    rows = []
    for entry in registry:
        participant_id = entry["participant_id"]
        merged = {
            "participant_id": participant_id,
            "username": entry.get("username", ""),
            "first_signed_in_at": entry.get("first_signed_in_at", ""),
        }
        if participant_id in state:
            if state[participant_id].get("username"):
                merged["username"] = state[participant_id]["username"]
            if state[participant_id].get("first_signed_in_at"):
                merged["first_signed_in_at"] = state[participant_id]["first_signed_in_at"]
        rows.append(merged)

    df = pd.DataFrame(rows)
    df["participant_id"] = df["participant_id"].astype(str).str.upper()
    df["username"] = df["username"].fillna("").astype(str).str.strip()
    df["first_signed_in_at"] = df["first_signed_in_at"].fillna("").astype(str).str.strip()
    return df


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


def save_user_name(participant_id, username):
    participant_id = participant_id.strip().upper()
    registry_ids = {
        entry["participant_id"] for entry in _load_users_registry_entries()
    }
    if participant_id not in registry_ids:
        return False

    users = load_users()
    existing = ""
    if participant_id in users["participant_id"].values:
        existing = str(
            users.loc[users["participant_id"] == participant_id, "username"].iloc[0]
        ).strip()
    if existing:
        return False

    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    state = _load_users_state_entries()
    state[participant_id] = {
        "participant_id": participant_id,
        "username": username.strip(),
        "first_signed_in_at": now,
    }
    _save_users_state(state)
    return True


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
