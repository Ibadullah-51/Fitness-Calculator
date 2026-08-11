"""
TDEE (Total Daily Energy Expenditure) and calorie-goal calculations.

TDEE = BMR x an activity multiplier. It estimates the total calories you burn
in a day once you factor in movement and exercise. This is your "maintenance"
number: eat this much and your weight stays roughly stable.

From TDEE we then derive calorie GOALS for fat loss and muscle gain by nudging
that number up or down by a percentage.
"""

# Activity multipliers. These are the widely-used standard values.
# Keeping them in a dict makes the code self-documenting and easy to extend.
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,     # desk job, little or no exercise
    "light": 1.375,       # light exercise 1-3 days/week
    "moderate": 1.55,     # moderate exercise 3-5 days/week
    "active": 1.725,      # hard exercise 6-7 days/week
    "very_active": 1.9,   # physical job or training twice a day
}

# Calorie-goal offsets expressed as a MULTIPLIER of TDEE.
# Using percentages (rather than fixed kcal like -500) means the deficit/surplus
# scales sensibly with body size.
GOAL_MULTIPLIERS = {
    "fat_loss_mild": 0.90,        # -10%
    "fat_loss_moderate": 0.80,    # -20%
    "fat_loss_aggressive": 0.75,  # -25%
    "maintenance": 1.00,          #   0%
    "muscle_gain_mild": 1.10,     # +10%
    "muscle_gain_moderate": 1.15, # +15%
}


def calculate_tdee(bmr: float, activity_level: str) -> int:
    """
    Multiply BMR by the chosen activity multiplier to get maintenance calories.

    Args:
        bmr:            Basal Metabolic Rate in kcal/day.
        activity_level: one of the keys in ACTIVITY_MULTIPLIERS.

    Returns:
        TDEE in kcal/day, rounded to a whole number.
    """
    multiplier = ACTIVITY_MULTIPLIERS[activity_level]
    return round(bmr * multiplier)


def calculate_goals(tdee: int, bmr: float) -> dict:
    """
    Build a dictionary of calorie targets for every goal.

    We pass in BMR as well so we can apply a SAFETY FLOOR: an aggressive cut
    should never push someone below their BMR, since eating under your resting
    needs for long stretches is generally a bad idea. If a percentage-based
    target dips under BMR, we clamp it up to BMR instead.

    Args:
        tdee: maintenance calories.
        bmr:  basal metabolic rate (used only as the safety floor).

    Returns:
        A dict mapping each goal name to a small dict with:
            calories -> the target intake
            delta    -> difference from maintenance (negative = deficit)
    """
    goals = {}
    for name, multiplier in GOAL_MULTIPLIERS.items():
        target = round(tdee * multiplier)

        # Safety floor: never recommend eating below BMR.
        floored = False
        if target < bmr:
            target = round(bmr)
            floored = True

        goals[name] = {
            "calories": target,
            "delta": target - tdee,   # e.g. -400 means a 400 kcal deficit
            "floored": floored,       # frontend can show a note if True
        }
    return goals
