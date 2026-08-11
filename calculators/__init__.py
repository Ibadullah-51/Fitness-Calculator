"""
The `calculators` package holds all the pure math for the app.

By importing the main functions here, the rest of the app can write:

    from calculators import calculate_bmr, calculate_tdee

instead of the longer:

    from calculators.bmr import calculate_bmr

Nothing in this package knows anything about Flask or HTTP -- these are just
plain functions that take numbers and return numbers/dicts. That makes them
trivial to unit-test in isolation.
"""

from calculators.bmr import calculate_bmr
from calculators.tdee import calculate_tdee, calculate_goals
from calculators.protein import calculate_protein
from calculators.macros import calculate_macros
from calculators.bodyfat import calculate_bodyfat

# __all__ defines what `from calculators import *` would pull in. Good hygiene.
__all__ = [
    "calculate_bmr",
    "calculate_tdee",
    "calculate_goals",
    "calculate_protein",
    "calculate_macros",
    "calculate_bodyfat",
]
