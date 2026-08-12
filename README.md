# MacroLab — Fitness & Metabolic Calculator

A web-based fitness calculator that helps users estimate their metabolic and nutrition numbers — BMR, TDEE, macros, protein needs, and body fat percentage — all in one place.

🔗 **Live demo:** [https://fitness-calculator-k8xr.onrender.com/](https://fitness-calculator-k8xr.onrender.com/)

> Hosted on Render's free tier — if the app hasn't been used in a while, the first load may take 30–50 seconds while the server wakes up.

## Features

- **BMR & TDEE calculator** — uses the Mifflin-St Jeor equation, adjusted by activity level, to estimate daily calorie burn
- **Protein target calculator** — evidence-based protein range (1.4–2.4 g/kg) based on your goal (fat loss, maintenance, muscle gain)
- **Macro split calculator** — splits daily calories into protein, fat, and carbs based on your targets
- **Body fat estimator** — U.S. Navy tape method estimate from basic body measurements
- Supports both **metric** and **imperial** units

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript (vanilla, no framework)
- **Deployment:** Render

## Project Structure

```
fitness-calculator/
├── app.py                 # Flask app & API routes
├── utils.py                # Shared helper functions
├── calculators/             # Core calculation logic
│   ├── bmr.py
│   ├── tdee.py
│   ├── protein.py
│   ├── macros.py
│   └── bodyfat.py
├── templates/
│   └── index.html          # Main frontend page
├── static/
│   ├── css/style.css
│   └── js/main.js
└── requirements.txt
```

## Running Locally

1. Clone the repo:
   ```
   git clone https://github.com/Ibadullah-51/fitness-calculator.git
   cd fitness-calculator
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the app:
   ```
   python app.py
   ```

4. Open `http://127.0.0.1:5000` in your browser.

## Deployment

This app is deployed on [Render](https://render.com) as a single Flask web service.

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`

## Disclaimer

All calculated values (BMR, TDEE, macros, body fat, etc.) are estimates for general guidance only and are not a substitute for professional medical or nutritional advice.
