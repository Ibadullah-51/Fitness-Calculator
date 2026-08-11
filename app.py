"""
Flask application: routes + JSON API for the fitness calculator.

Architecture in one sentence: each route reads and validates the incoming JSON
(using helpers from utils.py), calls a pure function from the calculators
package, and returns the result as JSON. No math lives in this file.

Run locally with:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, request, jsonify, render_template

# Import the pure calculation functions.
from calculators import (
    calculate_bmr,
    calculate_tdee,
    calculate_goals,
    calculate_protein,
    calculate_macros,
    calculate_bodyfat,
)

# Import validation helpers and the custom error type.
from utils import (
    ValidationError,
    require_json,
    get_number,
    get_choice,
    normalize_weight,
    normalize_length,
)

# The activity / goal / gender option sets, pulled from the calculators so
# there's a single source of truth (no risk of the API and the math disagreeing).
from calculators.tdee import ACTIVITY_MULTIPLIERS
from calculators.protein import PROTEIN_RANGES

app = Flask(__name__)

# Sets of allowed string values, used by get_choice() for validation.
VALID_GENDERS = {"male", "female"}
VALID_UNITS = {"metric", "imperial"}
VALID_ACTIVITY = set(ACTIVITY_MULTIPLIERS.keys())
VALID_GOALS = set(PROTEIN_RANGES.keys())  # fat_loss / maintenance / muscle_gain


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
# Register ONE handler for our ValidationError. Any route that raises it (or
# any helper it calls) will land here and produce a consistent 400 response.
@app.errorhandler(ValidationError)
def handle_validation_error(err):
    return jsonify({"ok": False, "error": str(err)}), 400


# Catch-all for unexpected server errors so we never leak a stack trace as HTML.
@app.errorhandler(500)
def handle_server_error(err):
    return jsonify({"ok": False, "error": "Internal server error."}), 500


# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the single-page frontend (templates/index.html)."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API: BMR
# ---------------------------------------------------------------------------
@app.route("/api/bmr", methods=["POST"])
def api_bmr():
    """
    Body (JSON):
        age, gender, height, weight, units

    height/weight are interpreted according to `units`:
        metric   -> height in cm, weight in kg
        imperial -> height in inches, weight in lb
    """
    data = require_json(request.get_json(silent=True))

    units = get_choice(data, "units", VALID_UNITS)
    gender = get_choice(data, "gender", VALID_GENDERS)
    age = get_number(data, "age", minimum=10, maximum=120)

    # Read height/weight in whatever units were sent, then normalize to metric.
    raw_height = get_number(data, "height", minimum=1)
    raw_weight = get_number(data, "weight", minimum=1)
    height_cm = normalize_length(raw_height, units)
    weight_kg = normalize_weight(raw_weight, units)

    # Sanity-check the normalized (metric) values are in a human range.
    if not (50 <= height_cm <= 260):
        raise ValidationError("Height is outside a realistic range.")
    if not (20 <= weight_kg <= 400):
        raise ValidationError("Weight is outside a realistic range.")

    bmr = calculate_bmr(weight_kg, height_cm, int(age), gender)
    return jsonify({"ok": True, "bmr": bmr})


# ---------------------------------------------------------------------------
# API: TDEE (+ calorie goals)
# ---------------------------------------------------------------------------
@app.route("/api/tdee", methods=["POST"])
def api_tdee():
    """
    Body (JSON):
        bmr, activity_level

    Returns TDEE plus a full set of calorie goals derived from it.
    """
    data = require_json(request.get_json(silent=True))

    bmr = get_number(data, "bmr", minimum=500, maximum=5000)
    activity_level = get_choice(data, "activity_level", VALID_ACTIVITY)

    tdee = calculate_tdee(bmr, activity_level)
    goals = calculate_goals(tdee, bmr)

    return jsonify({"ok": True, "tdee": tdee, "goals": goals})


# ---------------------------------------------------------------------------
# API: Protein
# ---------------------------------------------------------------------------
@app.route("/api/protein", methods=["POST"])
def api_protein():
    """
    Body (JSON):
        weight, units, goal

    goal is one of: fat_loss / maintenance / muscle_gain.
    """
    data = require_json(request.get_json(silent=True))

    units = get_choice(data, "units", VALID_UNITS)
    goal = get_choice(data, "goal", VALID_GOALS)

    raw_weight = get_number(data, "weight", minimum=1)
    weight_kg = normalize_weight(raw_weight, units)
    if not (20 <= weight_kg <= 400):
        raise ValidationError("Weight is outside a realistic range.")

    result = calculate_protein(weight_kg, goal)
    return jsonify({"ok": True, "protein": result})


# ---------------------------------------------------------------------------
# API: Macros
# ---------------------------------------------------------------------------
@app.route("/api/macros", methods=["POST"])
def api_macros():
    """
    Body (JSON):
        goal_calories, protein_g, fat_pct

    fat_pct is the fraction (0-1) of the REMAINING calories assigned to fat.
    Accepts a 0-100 percentage too and converts it.
    """
    data = require_json(request.get_json(silent=True))

    goal_calories = get_number(data, "goal_calories", minimum=800, maximum=8000)
    protein_g = get_number(data, "protein_g", minimum=0, maximum=500)
    fat_pct = get_number(data, "fat_pct", minimum=0, maximum=100)

    # Allow the client to send either 0-1 or 0-100; normalize to a 0-1 fraction.
    if fat_pct > 1:
        fat_pct = fat_pct / 100

    result = calculate_macros(int(goal_calories), int(protein_g), fat_pct)
    return jsonify({"ok": True, "macros": result})


# ---------------------------------------------------------------------------
# API: Body fat (bonus)
# ---------------------------------------------------------------------------
@app.route("/api/bodyfat", methods=["POST"])
def api_bodyfat():
    """
    Body (JSON):
        gender, units, height, neck, waist, hip (hip required for women)

    All measurements are in cm (metric) or inches (imperial) per `units`.
    """
    data = require_json(request.get_json(silent=True))

    units = get_choice(data, "units", VALID_UNITS)
    gender = get_choice(data, "gender", VALID_GENDERS)

    height_cm = normalize_length(get_number(data, "height", minimum=1), units)
    neck_cm = normalize_length(get_number(data, "neck", minimum=1), units)
    waist_cm = normalize_length(get_number(data, "waist", minimum=1), units)

    # Hip is only needed for women; read it conditionally.
    hip_cm = None
    if gender == "female":
        hip_cm = normalize_length(get_number(data, "hip", minimum=1), units)

    # calculate_bodyfat may raise ValueError for impossible measurements;
    # translate that into our ValidationError so it becomes a clean 400.
    try:
        result = calculate_bodyfat(gender, height_cm, neck_cm, waist_cm, hip_cm)
    except ValueError as e:
        raise ValidationError(str(e))

    return jsonify({"ok": True, "bodyfat": result})


if __name__ == "__main__":
    # debug=True gives auto-reload and helpful error pages during development.
    # Turn this OFF before deploying anywhere public.
    app.run(debug=True, port=5000)
