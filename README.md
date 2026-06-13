# Football Prediction App

A simple one-page Streamlit app for lab football match prediction.

```bash
cd streamlit-app
python3 -m pip install -r requirements.txt
streamlit run app.py
```

## Scoring

- **3 points** — exact prediction (both scores correct).
- **2 points** — correct winner and correct goal difference, but not the exact score.
- **1 point** — correct winner only (goal difference differs).
- **0 points** — incorrect outcome (or no prediction submitted).
