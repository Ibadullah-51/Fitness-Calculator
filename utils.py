"""
Shared validation + unit-conversion helpers.

The goal of this module is to let each route in app.py pull clean, validated,
metric-unit numbers out of the incoming JSON in just a few lines, while giving
the user a clear error message the moment something is wrong.

The key idea is a custom exception, ValidationError. Any helper that finds bad
input raises it with a human-readable message. app.py catches it in one place
and turns it into a tidy 400 JSON response -- so validation code never has to
know anything about HTTP.
"""

# Conversion constants for the imperial -> metric toggle.
LB_PER_KG = 2.20462
CM_PER_INCH = 2.54


class ValidationError(Exception):
    """Raised when user input is missing, wrong type, or out of range."""
    pass


def get_number(data: dict, field: str, minimum=None, maximum=None) -> float:
    """
    Pull a required numeric field out of the request data.

    Checks, in order: present -> numeric -> within [minimum, maximum].

    Args:
        data:    the parsed JSON dict from the request.
        field:   the key to look up.
        minimum: optional lower bound (inclusive).
        maximum: optional upper bound (inclusive).

    Returns:
        The value as a float.

    Raises:
        ValidationError: with a specific message if any check fails.
    """
    if field not in data or data[field] is None or data[field] == "":
        raise ValidationError(f"Missing required field: '{field}'.")

    # Accept numbers sent as strings (e.g. "70") by trying to cast to float.
    try:
        value = float(data[field])
    except (TypeError, ValueError):
        raise ValidationError(f"Field '{field}' must be a number.")

    if minimum is not None and value < minimum:
        raise ValidationError(f"Field '{field}' must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ValidationError(f"Field '{field}' must be at most {maximum}.")

    return value


def get_choice(data: dict, field: str, allowed: set) -> str:
    """
    Pull a required field that must be one of a fixed set of string options.

    Args:
        data:    parsed JSON dict.
        field:   key to look up.
        allowed: the set of acceptable values.

    Returns:
        The validated string.

    Raises:
        ValidationError: if missing or not in the allowed set.
    """
    if field not in data or data[field] is None or data[field] == "":
        raise ValidationError(f"Missing required field: '{field}'.")

    value = str(data[field]).lower().strip()
    if value not in allowed:
        # Sort for a stable, readable error message.
        options = ", ".join(sorted(allowed))
        raise ValidationError(
            f"Field '{field}' must be one of: {options}. Got '{value}'."
        )
    return value


def require_json(data) -> dict:
    """
    Make sure the request actually contained a JSON object (dict).

    Flask's request.get_json() returns None if the body wasn't valid JSON or
    the Content-Type header was missing, so we check for that explicitly.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            "Request body must be a JSON object. "
            "Did you set 'Content-Type: application/json'?"
        )
    return data


# ----------------------------------------------------------------------------
# Unit conversion: imperial -> metric.
# The calculators only ever work in metric, so we convert at the edge (here),
# right after reading the raw input, and never again.
# ----------------------------------------------------------------------------

def lb_to_kg(pounds: float) -> float:
    """Convert pounds to kilograms."""
    return pounds / LB_PER_KG


def in_to_cm(inches: float) -> float:
    """Convert inches to centimeters."""
    return inches * CM_PER_INCH


def normalize_weight(value: float, units: str) -> float:
    """Return weight in kg, converting from lb if the user is in imperial."""
    return lb_to_kg(value) if units == "imperial" else value


def normalize_length(value: float, units: str) -> float:
    """Return a length in cm, converting from inches if imperial."""
    return in_to_cm(value) if units == "imperial" else value
