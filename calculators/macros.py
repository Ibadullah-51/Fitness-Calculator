"""
Macronutrient split calculation.

The philosophy here: PROTEIN is fixed first because it's the priority nutrient
for body composition. Whatever calories are left after protein get divided
between FAT and CARBS according to a single ratio the user controls with a
slider on the frontend.

Energy densities:
    protein = 4 kcal/g
    carbs   = 4 kcal/g
    fat     = 9 kcal/g
"""

KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARBS = 4
KCAL_PER_G_FAT = 9

# We clamp the fat percentage to a sensible window. Too little dietary fat can
# harm hormonal health; too much leaves no room for performance-fueling carbs.
MIN_FAT_PCT = 0.15
MAX_FAT_PCT = 0.60


def calculate_macros(goal_calories: int, protein_g: int, fat_pct: float) -> dict:
    """
    Split total daily calories into protein / fat / carbs.

    Args:
        goal_calories: the day's total calorie target.
        protein_g:     grams of protein (already decided by the protein calc).
        fat_pct:       fraction (0.0-1.0) of the REMAINING calories to assign
                       to fat. Carbs get whatever is left.

    Returns:
        A dict describing each macro in grams, calories, and percent of total
        daily calories -- ready to feed straight into a chart.
    """
    # Clamp the fat percentage into the safe window before doing anything.
    fat_pct = max(MIN_FAT_PCT, min(MAX_FAT_PCT, fat_pct))

    # 1. Protein is fixed. Work out its calorie cost.
    protein_kcal = protein_g * KCAL_PER_G_PROTEIN

    # 2. Whatever calories remain get shared between fat and carbs.
    remaining_kcal = goal_calories - protein_kcal

    # Guard against a nonsensical case where protein alone exceeds the target
    # (can happen with a very aggressive deficit + high bodyweight).
    if remaining_kcal < 0:
        remaining_kcal = 0

    fat_kcal = remaining_kcal * fat_pct
    carb_kcal = remaining_kcal * (1 - fat_pct)

    # 3. Convert each calorie bucket back into grams.
    fat_g = round(fat_kcal / KCAL_PER_G_FAT)
    carb_g = round(carb_kcal / KCAL_PER_G_CARBS)

    # 4. Percentages of the TOTAL day, handy for the donut/bar chart.
    def pct_of_total(kcal):
        return round((kcal / goal_calories) * 100) if goal_calories else 0

    return {
        "calories": goal_calories,
        "fat_pct_of_remaining": round(fat_pct * 100),
        "protein": {
            "grams": protein_g,
            "calories": round(protein_kcal),
            "percent": pct_of_total(protein_kcal),
        },
        "fat": {
            "grams": fat_g,
            "calories": round(fat_kcal),
            "percent": pct_of_total(fat_kcal),
        },
        "carbs": {
            "grams": carb_g,
            "calories": round(carb_kcal),
            "percent": pct_of_total(carb_kcal),
        },
    }
