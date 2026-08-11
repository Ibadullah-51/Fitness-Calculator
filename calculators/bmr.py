"""
BMR (Basal Metabolic Rate) calculation.

BMR is the number of calories your body burns at complete rest just to keep
you alive (breathing, circulation, cell repair, etc.). It's the foundation
that every other number in this app builds on.

We use the Mifflin-St Jeor equation, which is the modern standard and more
accurate for the general population than the older Harris-Benedict formula.

All inputs here are expected to already be in METRIC units:
    - weight in kilograms
    - height in centimeters
    - age in years

Unit conversion (imperial -> metric) happens BEFORE this function is called,
so this module never has to worry about pounds or inches. That keeps the math
in one place and easy to trust.
"""


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Calculate Basal Metabolic Rate using the Mifflin-St Jeor equation.

    The equation is identical for men and women EXCEPT for the final constant:
        Men:   +5
        Women: -161

    Args:
        weight_kg: bodyweight in kilograms
        height_cm: height in centimeters
        age:       age in years
        gender:    "male" or "female"

    Returns:
        BMR in kcal/day, rounded to the nearest whole calorie.
    """
    # The part of the formula that is the same regardless of gender.
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)

    # Apply the gender-specific constant.
    if gender == "male":
        bmr = base + 5
    else:  # "female"
        bmr = base - 161

    # Calories are never reported as fractions in a fitness context, so round.
    return round(bmr)
