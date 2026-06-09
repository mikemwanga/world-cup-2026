# Football Prediction App

A simple one-page Streamlit app for lab football match prediction.

## How it works

- The **admin (`ADMIN01`) assigns each person a login ID** from the Admin panel, then shares it with them.
- A user logs in with their assigned ID and, on first login, chooses a **unique username** (set once, shown on the leaderboard).
- Assigned IDs and usernames are stored in `data/users.csv`.
- For deployment, the Admin panel shows a `.toml` snippet to paste into Streamlit Cloud secrets so logins persist.
- Only the username is shown on the leaderboard. Predictions are linked to the participant ID.
- The page shows upcoming matches, prediction entry, previous predictions, and leaderboard.

## Run locally

```bash
cd streamlit-app
python3 -m pip install -r requirements.txt
streamlit run app.py
```
## Data files

- `data/users.csv` — assigned participants (`participant_id`, `username`, `first_signed_in_at`); gitignored.
- `data/matches.csv` — match schedule and any actual results.
- `data/predictions.csv` / `.xlsx` — saved predictions.

## Scoring

- **3 points** — exact prediction (both scores correct).
- **2 points** — correct winner and correct goal difference, but not the exact score.
- **1 point** — correct winner only (goal difference differs).
- **0 points** — incorrect outcome (or no prediction submitted).
