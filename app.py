from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np

app = Flask(__name__)

# ================= LOAD MODEL =================
model = joblib.load("model/risk_model.pkl")

# ================= LOAD FEATURE ORDER =================
with open("model/feature_order.txt", "r") as f:
    feature_order = [line.strip() for line in f.readlines()]


# ================= SAFE FLOAT =================
def safe_float(value):
    try:
        if value == "" or value is None:
            return 0.0
        return float(value)
    except:
        return 0.0


# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")


# ================= PREDICT =================
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        # ================= PREPARE MODEL INPUT =================
        input_data = []

        for feature in feature_order:
            value = data.get(feature, 0)

            if value in ["Yes", "Stable"]:
                value = 1
            elif value in ["No", "Unstable"]:
                value = 0

            value = safe_float(value)
            input_data.append(value)

        input_array = np.array([input_data])

        # ================= ML BASE PROBABILITY =================
        ml_probability = model.predict_proba(input_array)[0][1] * 100
        ml_probability = round(float(ml_probability), 2)

        # ================= EXTRACT INPUTS =================
        season = data.get("Season", "Normal")

        rainfall = safe_float(data.get("Rainfall_Deviation"))
        market_vol = safe_float(data.get("Market_Volatility"))
        input_cost = safe_float(data.get("Input_Cost"))
        loan_amount = safe_float(data.get("Loan_Amount"))
        storage = safe_float(data.get("Storage_Access"))
        income = safe_float(data.get("Income_Stability"))

        if loan_amount <= 0:
            loan_amount = 1

        # ================= CALCULATE RAW RISKS =================

        # Weather Risk
        weather_risk = min(max(abs(rainfall) * 2, 5), 100)

        # Market Risk
        market_risk = min(max(abs(market_vol) * 120, 5), 100)

        # Financial Risk
        cost_ratio = input_cost / loan_amount
        financial_risk = min(max(cost_ratio * 100, 5), 100)

        if storage == 1:
            financial_risk *= 0.85

        if income == 0:
            market_risk *= 1.1

        financial_risk = min(financial_risk, 100)
        market_risk = min(market_risk, 100)

        # Pest Risk
        pest_risk = min(max((abs(rainfall) * 1.5) + (ml_probability * 0.4), 5), 100)

        # Soil Risk
        soil_risk = min(max(abs(rainfall) * 1.2, 5), 100)

        # ================= DYNAMIC SEASON WEIGHTING =================

        if season == "Monsoon":
            weights = {
                "weather": 0.50,
                "market": 0.15,
                "financial": 0.15,
                "pest": 0.10,
                "soil": 0.10
            }

        elif season == "Harvest":
            weights = {
                "weather": 0.15,
                "market": 0.50,
                "financial": 0.15,
                "pest": 0.10,
                "soil": 0.10
            }

        else:  # Normal
            weights = {
                "weather": 0.20,
                "market": 0.20,
                "financial": 0.20,
                "pest": 0.20,
                "soil": 0.20
            }

        # ================= FINAL WEIGHTED SCORE =================

        weighted_score = (
            weather_risk * weights["weather"] +
            market_risk * weights["market"] +
            financial_risk * weights["financial"] +
            pest_risk * weights["pest"] +
            soil_risk * weights["soil"]
        )

        # Blend ML signal (30%) + Weighted Engine (70%)
        final_score = (weighted_score * 0.7) + (ml_probability * 0.3)
        final_score = round(min(final_score, 100), 2)

        # ================= RISK LEVEL =================
        if final_score > 70:
            risk_level = "HIGH"
        elif final_score >= 40:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        breakdown = {
            "weather": round(weather_risk, 1),
            "market": round(market_risk, 1),
            "financial": round(financial_risk, 1),
            "pest": round(pest_risk, 1),
            "soil": round(soil_risk, 1)
        }

        # ================= SUMMARY =================
        highest_driver = max(breakdown, key=breakdown.get)

        summary_map = {
            "weather": "Seasonal weather variability is the dominant instability factor.",
            "market": "Market volatility is significantly impacting projected returns.",
            "financial": "Loan-to-input ratio indicates financial stress risk.",
            "pest": "Elevated pest exposure risk detected.",
            "soil": "Soil variability contributing to production uncertainty."
        }

        summary = summary_map.get(highest_driver)

        return jsonify({
            "risk_score": final_score,
            "risk_level": risk_level,
            "breakdown": breakdown,
            "summary": summary,
            "season": season
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
