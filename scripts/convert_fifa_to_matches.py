"""Convert fifa-world-cup-2026-original.csv into data/matches.csv using existing normalizer."""
from pathlib import Path
from process_data import ROOT, DATA_DIR, ORIGINAL_FIFA_FILE, MATCHES_FILE, _normalize_matches_df
import pandas as pd


def main():
    if not ORIGINAL_FIFA_FILE.exists():
        print(f"Original file not found: {ORIGINAL_FIFA_FILE}")
        return
    df = pd.read_csv(ORIGINAL_FIFA_FILE)
    df = _normalize_matches_df(df)
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(MATCHES_FILE, index=False)
    print(f"Wrote {MATCHES_FILE} with {len(df)} matches.")


if __name__ == "__main__":
    main()
