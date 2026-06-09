import streamlit as st
import pandas as pd
from datetime import datetime

from process_data import (
    ensure_data_files,
    load_matches,
    load_users,
    load_predictions,
    load_scores,
    add_or_update_prediction,
    lock_user_on_login,
    save_scores,
    build_leaderboard,
    build_admin_user_summary,
    build_admin_user_detail,
    compute_score,
    filter_actual_predictions,
    display_team_name,
    display_match_label,
)
from scoring_rules import SCORING_DESCRIPTION

ensure_data_files()

page_icon = "icons/coronavirus.png"
ballicon ="icons/kicking-ball.png"
st.set_page_config(page_title="IVI WorldCup Soccer Predictions", page_icon=page_icon, layout="wide")

st.markdown(
    """
    <style>
        .stApp .main .block-container {
            max-width: 1400px;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .group-header {
            font-size: 0.95rem;
            font-weight: 700;
            color: #1f4e79;
            margin-bottom: 0.35rem;
            text-align: center;
        }
        .match-card-title {
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.15rem;
        }
        .match-id-badge {
            display: inline-block;
            background: #1f4e79;
            color: #fff;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.1rem 0.45rem;
            border-radius: 4px;
            margin-right: 0.35rem;
            vertical-align: middle;
        }
        div[data-testid="stFormSubmitButton"] button {
            background-color: #1565c0 !important;
            border-color: #1565c0 !important;
            color: #ffffff !important;
            width: 100% !important;
            min-width: 4.5rem !important;
            min-height: 2.4rem !important;
            height: auto !important;
            padding: 0.4rem 0.75rem !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #0d47a1 !important;
            border-color: #0d47a1 !important;
        }
        div[data-testid="stFormSubmitButton"] button p,
        div[data-testid="stFormSubmitButton"] button span,
        div[data-testid="stFormSubmitButton"] button div {
            writing-mode: horizontal-tb !important;
            text-orientation: mixed !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow: visible !important;
            line-height: 1.2 !important;
            letter-spacing: normal !important;
        }
        .round-section {
            margin-top: 0.25rem;
            margin-bottom: 0.25rem;
        }
        div[data-testid="stExpander"] details summary p {
            font-weight: 600;
        }
        /* Responsive group rows: wrap instead of squeezing */
        section[data-testid="stMain"] div[data-testid="element-container"]:has(.group-grid-marker)
            + div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.75rem 0.5rem !important;
            align-items: stretch !important;
        }
        section[data-testid="stMain"] div[data-testid="element-container"]:has(.group-grid-marker)
            + div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 260px !important;
            flex: 1 1 260px !important;
            width: auto !important;
        }
        @media (max-width: 1100px) {
            section[data-testid="stMain"] div[data-testid="element-container"]:has(.group-grid-marker)
                + div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 calc(50% - 0.5rem) !important;
                min-width: min(100%, 260px) !important;
            }
        }
        @media (max-width: 620px) {
            .stApp .main .block-container {
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }
            .group-header {
                font-size: 0.85rem;
            }
            .match-card-title {
                font-size: 0.8rem;
            }
            section[data-testid="stMain"] div[data-testid="element-container"]:has(.group-grid-marker)
                + div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

GROUP_ROWS = [
    ["Group A", "Group B", "Group C", "Group D"],
    ["Group E", "Group F", "Group G", "Group H"],
    ["Group I", "Group J", "Group K", "Group L"],
]
def _round_sort_key(round_number):
    round_key = str(round_number)
    if round_key.isdigit():
        return (0, int(round_key))
    return (1, round_key)


def _round_label(round_number):
    round_key = str(round_number)
    if round_key.isdigit():
        return f"Round {int(round_key)}"
    return round_key

def _short_group_name(group):
    return group.replace("Group ", "Group  ")


def _parse_score(text, team_name, *, required=False):
    cleaned = str(text).strip()
    if cleaned == "":
        if required:
            raise ValueError(f"Enter a score for {team_name}.")
        return 0
    if len(cleaned) > 1 and cleaned[0] == "0":
        raise ValueError(
            f"Enter {team_name} score without leading zeros (e.g. use 1, not 01)."
        )
    if not cleaned.isdigit():
        raise ValueError(f"Enter a whole number for {team_name}.")
    value = int(cleaned)
    if value < 0 or value > 20:
        raise ValueError(f"{team_name} score must be between 0 and 20.")
    return value


def render_match_card(
    match,
    participant_id,
    username,
    predictions,
    now,
    *,
    key_prefix="",
    save_fn=add_or_update_prediction,
):
    match_id = int(match["match_id"])
    match_label = match["match_label"]
    match_time = match["match_date"].strftime("%d/%m %H:%M")
    deadline_time = match["prediction_deadline"].strftime("%d/%m %H:%M")
    user_preds = predictions[
        (predictions["participant_id"] == participant_id)
        & (predictions["match_id"] == match_id)
    ]
    has_saved_pick = not user_preds.empty
    saved_a = int(user_preds["predicted_score_a"].iloc[0]) if has_saved_pick else None
    saved_b = int(user_preds["predicted_score_b"].iloc[0]) if has_saved_pick else None
    deadline_passed = match["prediction_deadline"] < now
    team_a = display_team_name(match["team_a"])
    team_b = display_team_name(match["team_b"])

    with st.form(key=f"form_{key_prefix}{match_id}"):
        st.markdown(
            (
                f'<p class="match-card-title">'
                f'<span class="match-id-badge">ID {match_id}</span>'
                f'{team_a} vs {team_b}</p>'
            ),
            unsafe_allow_html=True,
        )
        st.caption(f"Kick-off: {match_time} · Deadline: {deadline_time}")
        if has_saved_pick:
            st.markdown(f"**Your pick:** {saved_a} – {saved_b}")
        else:
            st.markdown("**Your pick:** Not saved yet")
        if deadline_passed:
            st.warning("Deadline passed", icon="⏰")

        left, right = st.columns(2)
        score_a_text = left.text_input(
            team_a,
            value=str(saved_a) if has_saved_pick else "",
            placeholder="0",
            key=f"score_a_{key_prefix}{match_id}",
        )
        score_b_text = right.text_input(
            team_b,
            value=str(saved_b) if has_saved_pick else "",
            placeholder="0",
            key=f"score_b_{key_prefix}{match_id}",
        )

        submitted = st.form_submit_button("Save", type="primary", use_container_width=True)
        if submitted:
            if deadline_passed:
                st.error("Prediction deadline has passed.")
            else:
                try:
                    score_a = _parse_score(score_a_text, team_a, required=True)
                    score_b = _parse_score(score_b_text, team_b, required=True)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    save_fn(
                        participant_id,
                        username,
                        match_id,
                        score_a,
                        score_b,
                        match_label,
                    )
                    st.success("Saved.")
                    st.rerun()


def render_group_card(group, group_matches, participant_id, username, predictions, now, *, key_prefix="", save_fn=add_or_update_prediction):
    with st.container(border=True):
        st.markdown(
            f'<p class="group-header">{_short_group_name(group)}</p>',
            unsafe_allow_html=True,
        )
        if group_matches.empty:
            st.caption("No matches")
        else:
            for match_idx, (_, match) in enumerate(group_matches.iterrows()):
                if match_idx > 0:
                    st.divider()
                render_match_card(
                    match,
                    participant_id,
                    username,
                    predictions,
                    now,
                    key_prefix=key_prefix,
                    save_fn=save_fn,
                )


def render_round_grid(
    round_matches,
    participant_id,
    username,
    predictions,
    now,
    *,
    group_rows=GROUP_ROWS,
    key_prefix="",
    save_fn=add_or_update_prediction,
):
    for group_row in group_rows:
        st.markdown('<div class="group-grid-marker"></div>', unsafe_allow_html=True)
        cols = st.columns(len(group_row))
        for col_idx, group in enumerate(group_row):
            group_matches = round_matches[round_matches["group"] == group].sort_values(
                "match_date"
            )
            with cols[col_idx]:
                render_group_card(
                    group,
                    group_matches,
                    participant_id,
                    username,
                    predictions,
                    now,
                    key_prefix=key_prefix,
                    save_fn=save_fn,
                )


def _admin_match_select_options(matches):
    pending = matches[~matches["is_finished"]]
    rows = (
        pending[["match_id", "match_label"]]
        .drop_duplicates(subset=["match_id"])
        .sort_values("match_id")
    )
    labels = []
    match_id_by_label = {}
    for _, row in rows.iterrows():
        match_id = int(row["match_id"])
        label = f"{match_id} — {display_match_label(row['match_label'])}"
        labels.append(label)
        match_id_by_label[label] = match_id
    return labels, match_id_by_label


def render_admin_panel(matches, predictions):
    st.subheader("Admin control & view")

    summary = build_admin_user_summary(predictions, matches)
    st.markdown("**All signed-in participants**")
    if summary.empty:
        st.info("No registered participants yet.")
    else:
        display_table(summary)

    st.divider()
    st.markdown("**Participant detail**")
    if summary.empty:
        st.caption("Register participants to inspect individual predictions.")
    else:
        participant_ids = summary["Participant ID"].tolist()
        selected_id = st.selectbox(
            "Select participant ID",
            participant_ids,
            key="admin_selected_participant",
        )
        selected_username = summary.loc[
            summary["Participant ID"] == selected_id, "Username"
        ].iloc[0]
        st.markdown(
            f"**{selected_id}** ({selected_username}) — match-by-match predictions and performance"
        )
        detail = build_admin_user_detail(selected_id, predictions, matches)
        if detail.empty:
            st.info(f"No predictions recorded for {selected_id}.")
        else:
            detail["Match"] = detail["Match"].map(display_match_label)
            display_table(detail)

    st.divider()
    st.markdown("**Update match scores**")
    scores = load_scores()
    st.caption("Current score settings used to calculate points.")
    display_table(scores)

    match_labels, match_id_by_label = _admin_match_select_options(matches)

    if not match_labels:
        st.info("All matches have scores recorded. Nothing left to update.")
    else:
        with st.form(key="admin_score_update"):
            update_cols = st.columns(4)
            selected_label = update_cols[0].selectbox(
                "Match", match_labels, key="admin_match_id"
            )
            selected_match = match_id_by_label[selected_label]
            score_a_text = update_cols[1].text_input(
                "Team A score", value="0", key="admin_score_a"
            )
            score_b_text = update_cols[2].text_input(
                "Team B score", value="0", key="admin_score_b"
            )
            submitted = update_cols[3].form_submit_button("Update score")
            if submitted:
                try:
                    new_score_a = _parse_score(score_a_text, "Team A")
                    new_score_b = _parse_score(score_b_text, "Team B")
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if scores.empty or "match_id" not in scores.columns:
                        scores = pd.DataFrame(
                            columns=["match_id", "match_label", "actual_score_a", "actual_score_b"]
                        )
                    match_row = matches[matches["match_id"] == selected_match].iloc[0]
                    scores = pd.concat(
                        [
                            scores,
                            pd.DataFrame(
                                [
                                    {
                                        "match_id": selected_match,
                                        "match_label": match_row["match_label"],
                                        "actual_score_a": new_score_a,
                                        "actual_score_b": new_score_b,
                                    }
                                ]
                            ),
                        ],
                        ignore_index=True,
                    )
                    save_scores(scores)
                    st.success(f"Updated scores for match ID {selected_match}.")
                    st.rerun()


def display_table(df):
    st.dataframe(df, width="stretch", height="content", hide_index=True)


def display_leaderboard(leaderboard, is_admin):
    if is_admin:
        display_cols = [
            "Rank",
            "Participant ID",
            "Username",
            "Matches Predicted",
            "Correct Predictions",
            "Total Points",
        ]
    else:
        display_cols = [
            "Rank",
            "Username",
            "Matches Predicted",
            "Correct Predictions",
            "Total Points",
        ]
    visible_cols = [col for col in display_cols if col in leaderboard.columns]
    display_table(leaderboard[visible_cols])


icon_col,title_col = st.columns([1, 10])
title_col.markdown("# 2026 World Cup Fun Play")
icon_col.image(page_icon, width='content')
#balcol.image(ballicon, width='stretch')

matches = load_matches()
users = load_users()
predictions = filter_actual_predictions(load_predictions(), matches)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.participant_id = ""
    st.session_state.username = ""

#st.header("IVI Predictions")
st.markdown(
    "This is a single-page private prediction app. Use your assigned participant ID; no personal email is required."
)

# Check for auto-login via URL parameter
auto_login_id = st.query_params.get("id", "").strip().upper()
if auto_login_id and not st.session_state.logged_in:
    user_match = users[users["participant_id"] == auto_login_id]
    if not user_match.empty:
        existing_name = user_match["username"].iloc[0]
        if existing_name and existing_name != "":
            if lock_user_on_login(auto_login_id, existing_name):
                st.session_state.logged_in = True
                st.session_state.participant_id = auto_login_id
                st.session_state.username = existing_name
                st.session_state.is_admin = auto_login_id == "ADMIN01"
                st.rerun()

if not st.session_state.logged_in:
    st.markdown("### Participant login")
    login_col1, login_col2 = st.columns([2, 3])
    participant_id = login_col1.text_input("Participant ID", max_chars=8, key="login_id", placeholder="e.g., P001")
    normalized_id = participant_id.strip().upper()
    user_match = users[users["participant_id"] == normalized_id] if normalized_id else pd.DataFrame()
    needs_username = not user_match.empty and user_match["username"].iloc[0] == "" if not user_match.empty else False

    if normalized_id == "ADMIN01":
        login_col2.markdown(
            "**Admin login.** Just enter `ADMIN01` to continue."
        )
        username = "Admin"
    elif needs_username:
        username = login_col2.text_input(
            "Choose a username (this can only be set once)", key="login_name"
        )
    else:
        login_col2.markdown(
            "**Username is already set.** Just enter your Participant ID to login."
        )
        username = ""
    
    button_col1, button_col2 = st.columns([1, 1])
    login_clicked = button_col1.button("Login", key="login_button")
    stay_logged_in = button_col2.checkbox("Remember me (bookmark this link)", key="remember_me")

    if login_clicked:
        if normalized_id == "":
            st.error("Enter your participant ID.")
        else:
            user_match = users[users["participant_id"] == normalized_id]
            if user_match.empty:
                st.error(
                    "❌ Participant ID not found. Ask your admin for a valid ID."
                )
            else:
                existing_name = user_match["username"].iloc[0]
                if existing_name == "" and username.strip() == "":
                    st.error("❌ First login requires a username.")
                else:
                    login_username = existing_name if existing_name else username.strip()
                    if normalized_id == "ADMIN01":
                        login_username = existing_name or "Admin"
                    if not lock_user_on_login(normalized_id, login_username):
                        st.error(
                            "❌ This participant ID is already registered to another user."
                        )
                    else:
                        users = load_users()
                        locked_name = users.loc[
                            users["participant_id"] == normalized_id, "username"
                        ].iloc[0]
                        st.session_state.logged_in = True
                        st.session_state.participant_id = normalized_id
                        st.session_state.username = locked_name
                        st.session_state.is_admin = normalized_id == "ADMIN01"

                        if stay_logged_in:
                            st.query_params["id"] = normalized_id

                        st.rerun()
    
    st.markdown(
        "- Use your assigned participant ID (e.g., `P001`, `P002`, ..., `P010`).\n"
        "- Username is only required on first login and cannot be changed later."
    )
    st.markdown(
        "- Each ID can only be used by one person. Once you register, the ID is locked to you."
    )
    st.markdown(
        "- Check **Remember me** to get a link you can bookmark for instant login."
    )
    st.info(
        "❓ **First time?** Ask the admin for your participant ID."
    )
    st.stop()

participant_id = st.session_state.participant_id
username = st.session_state.username
is_admin = st.session_state.get("is_admin", False)

header_col1, header_col2 = st.columns([3, 1])
header_col1.markdown(
    f"**Logged in as:** `{participant_id}`  \n**Name:** {username or 'Not set yet'}"
)
if header_col2.button("Logout", key="logout_button"):
    st.session_state.logged_in = False
    st.session_state.participant_id = ""
    st.session_state.username = ""
    st.session_state.is_admin = False
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()

st.divider()

if is_admin:
    render_admin_panel(matches, predictions)
    st.markdown("---\n## Scoring Rules\n" + SCORING_DESCRIPTION)
    st.stop()

now = datetime.now()
upcoming = matches[~matches["is_finished"] & (matches["prediction_deadline"] >= now)].copy()
upcoming = upcoming.sort_values(by=["round_number", "group", "match_date"])
finished = matches[matches["is_finished"]].sort_values(by="match_date", ascending=False)

st.subheader("Upcoming matches")
st.badge("Match times have been converted to Central European local time",color="blue")

if upcoming.empty:
    st.info("No upcoming matches are available for prediction at this time.")
else:
    round_dates = upcoming.groupby("round_number")["match_date"].min()
    round_order = sorted(round_dates.index.tolist(), key=_round_sort_key)

    for round_number in round_order:
        round_key = str(round_number)
        round_matches = upcoming[upcoming["round_number"].astype(str) == round_key]
        match_count = len(round_matches)
        expander_label = f"{_round_label(round_number)} — {match_count} matches"
        with st.expander(expander_label, expanded=False):
            render_round_grid(
                round_matches,
                participant_id,
                username,
                predictions,
                now,
            )

st.divider()

st.subheader("Completed matches")
if finished.empty:
    st.info("No completed matches have been recorded yet.")
else:
    finished_display = finished[[
        "match_id",
        "match_label",
        "match_date",
        "actual_score_a",
        "actual_score_b",
    ]].copy()
    finished_display["Day"] = finished_display["match_date"].dt.strftime("%A")
    finished_display["match_date"] = finished_display["match_date"].dt.strftime("%Y-%m-%d %H:%M")

    predictions_by_match = predictions.copy()
    predictions_by_match["match_id"] = pd.to_numeric(predictions_by_match["match_id"], errors="coerce").astype("Int64")
    predictions_by_match["predicted_score_a"] = pd.to_numeric(predictions_by_match["predicted_score_a"], errors="coerce").astype("Int64")
    predictions_by_match["predicted_score_b"] = pd.to_numeric(predictions_by_match["predicted_score_b"], errors="coerce").astype("Int64")

    rows = []
    for _, row in finished_display.iterrows():
        match_id = int(row["match_id"])
        match_preds = predictions_by_match[predictions_by_match["match_id"] == match_id]
        total_predictions = len(match_preds)
        exact_predictions = int(
            ((match_preds["predicted_score_a"] == int(row["actual_score_a"]))
             & (match_preds["predicted_score_b"] == int(row["actual_score_b"]))).sum()
        )
        rows.append(
            {
                "Match": display_match_label(row["match_label"]),
                "Day": row["Day"],
                "Played at": row["match_date"],
                "Actual score": f"{int(row['actual_score_a'])}-{int(row['actual_score_b'])}",
                "Predicted": total_predictions,
                "Exact correct": exact_predictions,
            }
        )
    finished_display = pd.DataFrame(rows)
    display_table(finished_display)
st.divider()

st.subheader("My Predictions")
user_preds = predictions[
    predictions["participant_id"].astype(str).str.upper() == participant_id.upper()
].copy()
if not user_preds.empty and "saved_at" in user_preds.columns:
    user_preds["saved_at"] = pd.to_datetime(user_preds["saved_at"], errors="coerce")
    user_preds = user_preds.sort_values(["saved_at", "match_id"], ascending=False, na_position="last")

history = []
for _, row in user_preds.iterrows():
    match_row = matches[matches["match_id"] == int(row["match_id"])]
    if match_row.empty:
        continue
    match_row = match_row.iloc[0]
    predicted_a = int(row["predicted_score_a"])
    predicted_b = int(row["predicted_score_b"])

    if not match_row["is_finished"]:
        history.append(
            {
                "Match": display_match_label(row["match_label"]),
                "Result": "Pending",
                "My prediction": f"{predicted_a}-{predicted_b}",
                "Win": "—",
                "Draw": "—",
                "Goals": "—",
                "Points": "Pending",
            }
        )
        continue

    points = compute_score(row, match_row)
    actual_a = int(match_row["actual_score_a"])
    actual_b = int(match_row["actual_score_b"])

    actual_outcome = "A" if actual_a > actual_b else ("B" if actual_b > actual_a else "Draw")
    predicted_outcome = "A" if predicted_a > predicted_b else ("B" if predicted_b > predicted_a else "Draw")

    win_correct = actual_outcome in ["A", "B"] and predicted_outcome == actual_outcome
    draw_correct = actual_outcome == "Draw" and predicted_outcome == "Draw"
    goals_correct = (predicted_a == actual_a) and (predicted_b == actual_b)

    history.append(
        {
            "Match": display_match_label(row["match_label"]),
            "Result": f"{actual_a}-{actual_b}",
            "My prediction": f"{predicted_a}-{predicted_b}",
            "Win": "✅" if win_correct else "❌",
            "Draw": "✅" if draw_correct else "❌",
            "Goals": "✅" if goals_correct else "❌",
            "Points": points if points is not None else 0,
        }
    )

if not history:
    st.info("No predictions saved yet. Make picks in Upcoming matches above.")
else:
    history_df = pd.DataFrame(history)
    history_df = history_df[["Match", "Result", "My prediction", "Win", "Draw", "Goals", "Points"]]
    display_table(history_df)

st.divider()

st.subheader("Leaderboard")
leaderboard = build_leaderboard(predictions, matches)
if leaderboard.empty:
    st.info("No predictions recorded yet.")
else:
    display_leaderboard(leaderboard, is_admin)

st.markdown(
    "---\n## Scoring Rules\n" + SCORING_DESCRIPTION
)
