EXACT_SCORE_POINTS = 5
CORRECT_OUTCOME_POINTS = 2
WRONG_PREDICTION_POINTS = -1

SCORING_DESCRIPTION = """
Scoring rules for the football prediction app:

- Exact score prediction: {} points
  Example: predicted 1-1 and actual result 1-1.
  Example: predicted 1-3 and actual result 1-3.
- Correct outcome prediction: {} points
  Example: predicted win for Team A, Team B, or draw correctly.
  This applies when the exact score is not matched.
- Wrong prediction: {} points
  Example: predicted Team A but Team B actually won, or predicted draw but result was not draw.

If no prediction is submitted, the user receives 0 points for that match.
""".format(EXACT_SCORE_POINTS, CORRECT_OUTCOME_POINTS, WRONG_PREDICTION_POINTS)
