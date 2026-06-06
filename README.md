# Football Prediction App

A simple one-page Streamlit app for lab football match prediction.

## How it works

- Users log in with an assigned participant ID, not an email.
- Predictions are saved to an Excel backend file.
- Each user can only submit predictions under their own ID.
- The page shows upcoming matches, prediction entry, previous predictions, and leaderboard.

## Run locally

```bash
cd streamlit-app
python3 -m pip install -r requirements.txt
streamlit run app.py
```

## Data files

- `data/users.toml.example` — template for participant IDs and usernames.
- `data/.users.toml` — local user registry (gitignored; copy from the example).
- `data/users_state.toml` — first-login usernames and sign-in times (gitignored).
- `data/matches.csv` stores demo matches and any actual results.
- `data/predictions.xlsx` stores saved predictions.

### User registry (TOML / Streamlit secrets)

For deployment, add this to **Streamlit Cloud secrets** (not GitHub):

```toml
users = [
    { participant_id = "P001", username = "MJ" },
    { participant_id = "P002", username = "PS2" },
    { participant_id = "YWNWA", username = "" },
    { participant_id = "ADMIN01", username = "Admin" },
]
```

Locally, copy `data/users.toml.example` to `data/.users.toml`, or use `.streamlit/secrets.toml` with the same `users` array.

## Notes

- Default participant IDs: P001..P010.
- First login with an unused ID asks for a display name.
- Scores are calculated as:
  - exact result = 5 points
  - correct outcome = 2 points
  - wrong prediction = -1 point
