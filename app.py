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
    save_user_name,
    save_scores,
    build_leaderboard,
    compute_score,
)
from scoring_rules import SCORING_DESCRIPTION

ensure_data_files()

page_icon = "icons/coronavirus.png"
ballicon ="icons/kicking-ball.png"
st.set_page_config(page_title="Football Predictions", page_icon=page_icon, layout="centered")

st.markdown(
    """
    <style>
        .stApp .main .block-container {
            max-width: 900px;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        @media (max-width: 768px) {
            .stApp .main .block-container {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

balcol,title_col,icon_col = st.columns([2,8,2])
title_col.markdown("# Football World Cup 2026")
icon_col.image(page_icon, width='stretch')
balcol.image(ballicon, width='stretch')

matches = load_matches()
users = load_users()
predictions = load_predictions()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.participant_id = ""
    st.session_state.username = ""

st.header("IVI Predictions")
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
            st.session_state.logged_in = True
            st.session_state.participant_id = auto_login_id
            st.session_state.username = existing_name
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
                    if existing_name == "" and username.strip() != "" and normalized_id != "ADMIN01":
                        save_user_name(normalized_id, username.strip())
                        existing_name = username.strip()
                    
                    st.session_state.logged_in = True
                    st.session_state.participant_id = normalized_id
                    st.session_state.username = existing_name
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
    st.rerun()

st.divider()

if is_admin:
    st.subheader("Admin panel")
    st.info("Admin can view all user predictions, leaderboard details, and update match scores.")

    scores = load_scores()
    st.markdown("**Current match score settings**")
    st.dataframe(scores, use_container_width=True, hide_index=True)

    with st.form(key="admin_score_update"):
        update_cols = st.columns(4)
        selected_match = update_cols[0].selectbox(
            "Match ID", scores["match_id"].tolist(), key="admin_match_id"
        )
        new_score_a = update_cols[1].number_input(
            "Team A score", min_value=0, max_value=20, value=0, key="admin_score_a"
        )
        new_score_b = update_cols[2].number_input(
            "Team B score", min_value=0, max_value=20, value=0, key="admin_score_b"
        )
        if update_cols[3].form_submit_button("Update score"):
            scores.loc[scores["match_id"] == selected_match, ["actual_score_a", "actual_score_b"]] = [new_score_a, new_score_b]
            save_scores(scores)
            st.success(f"Updated scores for match ID {selected_match}.")
            st.experimental_rerun()

    admin_preds = predictions.copy()
    if not admin_preds.empty:
        admin_preds = admin_preds.merge(
            matches[["match_id", "match_label", "actual_score_a", "actual_score_b"]],
            on="match_id",
            how="left",
        )
        admin_preds["Points"] = admin_preds.apply(
            lambda row: compute_score(row, matches[matches["match_id"] == int(row["match_id"])].iloc[0]),
            axis=1,
        )
        admin_preds["Actual score"] = admin_preds.apply(
            lambda row: f"{int(row['actual_score_a'])}-{int(row['actual_score_b'])}" if pd.notna(row['actual_score_a']) and pd.notna(row['actual_score_b']) else "Pending",
            axis=1,
        )
        st.subheader("All user predictions")
        st.dataframe(
            admin_preds[
                ["participant_id", "username", "match_label", "predicted_score_a", "predicted_score_b", "predicted_outcome", "Actual score", "Points"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

now = datetime.now()
upcoming = matches[~matches["is_finished"] & (matches["prediction_deadline"] >= now)].copy()
upcoming = upcoming.sort_values(by=["round_number", "group", "match_date"])
finished = matches[matches["is_finished"]].sort_values(by="match_date", ascending=False)

st.subheader("Upcoming matches")
if upcoming.empty:
    st.info("No upcoming matches are available for prediction at this time.")
else:
    # Build round options keeping named rounds (e.g. 'Round of 32') and sort by earliest match date per round
    round_order = (
        upcoming.groupby("round_number")["match_date"].min().sort_values().index.tolist()
    )
    round_options = [str(r) for r in round_order]
    def _round_label(r):
        try:
            # show numeric rounds as 'Round N'
            if str(r).isdigit():
                return f"Round {int(r)}"
        except Exception:
            pass
        return str(r)

    selected_round = st.selectbox(
        "Select round",
        round_options,
        format_func=_round_label,
    )
    group_options = upcoming[upcoming["round_number"].astype(str) == str(selected_round)]["group"].sort_values().unique().tolist()

    selected_group = st.selectbox("Select group", group_options)

    selected_matches = upcoming[
        (upcoming["round_number"].astype(str) == str(selected_round))
        & (upcoming["group"] == selected_group)
    ]

    st.markdown(f"**Round {selected_round} — {selected_group}**")
    if selected_matches.empty:
        st.info("No upcoming matches in this group.")
    else:
        for _, match in selected_matches.iterrows():
            match_id = int(match["match_id"])
            match_label = match["match_label"]
            match_time = match["match_date"].strftime("%d/%m/%Y %H:%M")
            deadline_time = match["prediction_deadline"].strftime("%d/%m/%Y %H:%M")
            with st.expander(f"{match_label} — {match_time}", expanded=True):
                cols = st.columns([2, 2, 2, 1])
                cols[0].markdown(
                    f"**Match ID:** {match_id}  \n"
                    f"**Match date:** {match_time}  \n"
                    f"**Deadline:** {deadline_time}"
                )
                cols[1].markdown(
                    f"**Teams:** {match['team_a']} vs {match['team_b']}  \n"
                    f"**Group:** {match['group']}  \n"
                    f"**Location:** {match.get('location', '') or 'TBD'}"
                )
                user_preds = predictions[
                    (predictions["participant_id"] == participant_id)
                    & (predictions["match_id"] == match_id)
                ]
                default_a = int(user_preds["predicted_score_a"].iloc[0]) if not user_preds.empty else 0
                default_b = int(user_preds["predicted_score_b"].iloc[0]) if not user_preds.empty else 0
                cols[2].markdown(
                    f"**Your current prediction:** {default_a} - {default_b}"
                )
                if match["prediction_deadline"] < now:
                    cols[3].warning("Deadline passed")
                with st.form(key=f"form_{match_id}"):
                    st.markdown("**Enter your prediction:**")
                    left, right = st.columns(2)
                    score_a = left.number_input(
                        f"{match['team_a']} goals",
                        min_value=0,
                        max_value=20,
                        value=default_a,
                        key=f"score_a_{match_id}",
                    )
                    score_b = right.number_input(
                        f"{match['team_b']} goals",
                        min_value=0,
                        max_value=20,
                        value=default_b,
                        key=f"score_b_{match_id}",
                    )
                    predicted_outcome = "A" if score_a > score_b else ("B" if score_b > score_a else "Draw")
                    st.markdown(
                        f"**Predicted outcome:** {match['team_a'] if predicted_outcome == 'A' else match['team_b'] if predicted_outcome == 'B' else 'Draw'}"
                    )
                    submit = st.form_submit_button("Save prediction")
                    if submit:
                        if match["prediction_deadline"] < now:
                            st.error("Prediction deadline has passed.")
                        else:
                            add_or_update_prediction(
                                participant_id,
                                username,
                                match_id,
                                int(score_a),
                                int(score_b),
                                match_label,
                            )
                            st.success("Prediction saved.")
                            st.rerun()

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
                "Match": row["match_label"],
                "Day": row["Day"],
                "Played at": row["match_date"],
                "Actual score": f"{int(row['actual_score_a'])}-{int(row['actual_score_b'])}",
                "Predicted": total_predictions,
                "Exact correct": exact_predictions,
            }
        )
    finished_display = pd.DataFrame(rows)
    st.dataframe(finished_display, use_container_width=True, hide_index=True)
st.divider()

st.subheader("My previous predictions")
user_preds = predictions[predictions["participant_id"] == participant_id]
if user_preds.empty:
    st.info("You have not saved any predictions yet.")
else:
    history = []
    for _, row in user_preds.iterrows():
        match_row = matches[matches["match_id"] == int(row["match_id"])]
        if match_row.empty:
            continue
        match_row = match_row.iloc[0]
        points = compute_score(row, match_row)
        
        if match_row["is_finished"]:
            actual_a = int(match_row["actual_score_a"])
            actual_b = int(match_row["actual_score_b"])
            predicted_a = int(row["predicted_score_a"])
            predicted_b = int(row["predicted_score_b"])
            
            actual_outcome = "A" if actual_a > actual_b else ("B" if actual_b > actual_a else "Draw")
            predicted_outcome = "A" if predicted_a > predicted_b else ("B" if predicted_b > predicted_a else "Draw")
            
            win_correct = actual_outcome in ["A", "B"] and predicted_outcome == actual_outcome
            draw_correct = actual_outcome == "Draw" and predicted_outcome == "Draw"
            goals_correct = (predicted_a == actual_a) and (predicted_b == actual_b)
            
            history.append(
                {
                    "Match": row["match_label"],
                    "Result": f"{actual_a}-{actual_b}",
                    "Your prediction": f"{predicted_a}-{predicted_b}",
                    "Win": "✅" if win_correct else "❌",
                    "Draw": "✅" if draw_correct else "❌",
                    "Goals": "✅" if goals_correct else "❌",
                    "Points": points if points is not None else 0,
                }
            )
        else:
            history.append(
                {
                    "Match": row["match_label"],
                    "Result": "Pending",
                    "Your prediction": f"{int(row["predicted_score_a"])}-{int(row["predicted_score_b"])}",
                    "Win": "—",
                    "Draw": "—",
                    "Goals": "—",
                    "Points": "Pending",
                }
            )
    
    history_df = pd.DataFrame(history)
    if not history_df.empty:
        history_df = history_df[["Match", "Result", "Your prediction", "Win", "Draw", "Goals", "Points"]]
    st.dataframe(history_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Leaderboard")
leaderboard = build_leaderboard(predictions, matches)
if leaderboard.empty:
    st.info("No scored predictions yet.")
else:
    st.dataframe(leaderboard)

st.markdown(
    "---\n## Scoring Rules\n" + SCORING_DESCRIPTION
)
