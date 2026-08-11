"""
Body-fat percentage estimator using the U.S. Navy circumference method.

This estimates body-fat % from simple tape-measure circumferences. It's not as
accurate as a DEXA scan (expect roughly +/-3-4% error), but it's free and
repeatable, which makes it useful for tracking change over time.

IMPORTANT: the Navy formula was derived using INCHES. To keep things correct we
convert every centimeter measurement to inches inside this module, then apply
the imperial version of the formula.

Measurements needed:
    Men:   waist, neck, height
    Women: waist, hip, neck, height   (women need the extra hip measurement)
"""

import math

CM_PER_INCH = 2.54


def _cm_to_in(cm: float) -> float:
    """Convert a centimeter measurement to inches."""
    return cm / CM_PER_INCH


def calculate_bodyfat(
    gender: str,
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    hip_cm: float = None,
) -> dict:
    """
    Estimate body-fat percentage with the U.S. Navy method.

    Args:
        gender:    "male" or "female".
        height_cm: height in centimeters.
        neck_cm:   neck circumference in centimeters.
        waist_cm:  waist circumference in centimeters.
        hip_cm:    hip circumference in centimeters (REQUIRED for women only).

    Returns:
        A dict with the estimated body-fat percent and a category label.

    Raises:
        ValueError: if a female calculation is missing the hip measurement, or
                    if measurements are physically impossible (e.g. neck wider
                    than waist would make the logarithm undefined).
    """
    # Convert everything to inches up front.
    height_in = _cm_to_in(height_cm)
    neck_in = _cm_to_in(neck_cm)
    waist_in = _cm_to_in(waist_cm)

    if gender == "male":
        # The log term requires waist > neck; otherwise it's undefined.
        if waist_in - neck_in <= 0:
            raise ValueError("Waist must be larger than neck for this estimate.")

        bf = (
            495
            / (
                1.0324
                - 0.19077 * math.log10(waist_in - neck_in)
                + 0.15456 * math.log10(height_in)
            )
            - 450
        )
    else:  # female
        if hip_cm is None:
            raise ValueError("Hip measurement is required for female estimates.")

        hip_in = _cm_to_in(hip_cm)

        # The female log term requires (waist + hip) > neck.
        if waist_in + hip_in - neck_in <= 0:
            raise ValueError("Measurements are outside the valid range.")

        bf = (
            495
            / (
                1.29579
                - 0.35004 * math.log10(waist_in + hip_in - neck_in)
                + 0.22100 * math.log10(height_in)
            )
            - 450
        )

    bf = round(bf, 1)

    return {
        "body_fat_percent": bf,
        "category": _category(bf, gender),
        "method": "U.S. Navy circumference method",
        "note": "Estimate only; roughly +/-3-4% vs lab methods like DEXA.",
    }


def _category(bf: float, gender: str) -> str:
    """
    Map a body-fat percentage to a rough descriptive category.

    The healthy ranges differ between men and women because women naturally
    carry more essential fat.
    """
    if gender == "male":
        if bf < 6:
            return "Essential fat"
        elif bf < 14:
            return "Athletic"
        elif bf < 18:
            return "Fitness"
        elif bf < 25:
            return "Average"
        else:
            return "Above average"
    else:
        if bf < 14:
            return "Essential fat"
        elif bf < 21:
            return "Athletic"
        elif bf < 25:
            return "Fitness"
        elif bf < 32:
            return "Average"
        else:
            return "Above average"
