"""
Protein requirement calculation.

Protein needs are best expressed relative to bodyweight. The evidence-based
sweet spot for people who train is roughly 1.6-2.2 g/kg of bodyweight
(from resistance-training meta-analyses). We shift within that band by goal:

    - In a fat-loss deficit you want MORE protein to preserve muscle, so we
      push toward the higher end.
    - At maintenance you can sit a little lower.
    - For muscle gain the mid-to-upper range is plenty.

Protein provides 4 kcal per gram.
"""

# Each goal maps to a (low, high, recommended) tuple in grams per kg.
# "recommended" is the single number we surface as the headline figure.
PROTEIN_RANGES = {
    "fat_loss":    {"low": 1.8, "high": 2.4, "recommended": 2.2},
    "maintenance": {"low": 1.4, "high": 2.0, "recommended": 1.6},
    "muscle_gain": {"low": 1.6, "high": 2.2, "recommended": 1.8},
}

CALORIES_PER_GRAM_PROTEIN = 4


def calculate_protein(weight_kg: float, goal: str) -> dict:
    """
    Compute recommended daily protein intake in grams.

    Args:
        weight_kg: bodyweight in kilograms (converted upstream if imperial).
        goal:      one of "fat_loss", "maintenance", "muscle_gain".

    Returns:
        A dict with the low/high range, the single recommended value (all in
        grams), the g/kg factors used, and the calories those grams represent.
    """
    factors = PROTEIN_RANGES[goal]

    # Multiply the per-kg factors by bodyweight to get absolute grams.
    low_g = round(weight_kg * factors["low"])
    high_g = round(weight_kg * factors["high"])
    recommended_g = round(weight_kg * factors["recommended"])

    return {
        "recommended_g": recommended_g,
        "range_g": {"low": low_g, "high": high_g},
        "g_per_kg": factors,  # echo back the factors so the UI can explain them
        "calories": recommended_g * CALORIES_PER_GRAM_PROTEIN,
    }
