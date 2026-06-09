EXACT_SCORE_POINTS = 3
CORRECT_OUTCOME_AND_GD_POINTS = 2
CORRECT_OUTCOME_POINTS = 1
WRONG_PREDICTION_POINTS = 0

SCORING_DESCRIPTION = """
Scoring rules for the football prediction app:

- **{} points — Exact prediction**
  Awarded when both scores are correct:
  predicted home goals == actual home goals AND predicted away goals == actual away goals.
  Example: predicted 2-1 and the actual result is 2-1.
- **{} points — Correct winner and correct goal difference (not exact)**
  Awarded when the predicted outcome (win/draw/loss) matches the actual outcome AND
  the predicted goal difference equals the actual goal difference, but the score is not exact.
  Example: predicted 2-1 (diff +1) and the actual result is 3-2 (diff +1).
- **{} point — Correct winner only**
  Awarded when the predicted outcome matches the actual outcome, but the goal
  difference is different (and the score is not exact).
  Example: predicted 1-0 and the actual result is 3-0.
- **{} points — Incorrect outcome**
  Awarded when the predicted outcome (win/draw/loss) does not match the actual outcome.

If no prediction is submitted, the user receives 0 points for that match.
""".format(
    EXACT_SCORE_POINTS,
    CORRECT_OUTCOME_AND_GD_POINTS,
    CORRECT_OUTCOME_POINTS,
    WRONG_PREDICTION_POINTS,
)
