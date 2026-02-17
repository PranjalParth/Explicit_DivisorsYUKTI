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


# ================= AI HELP GUIDE ENGINE =================
def generate_recommendations(final_score, breakdown, region, water_source, insurance):

    recommendations = []

    if final_score > 75:
        recommendations.append("Immediate strategic intervention required to prevent severe financial distress.")

    # WEATHER
    if breakdown["weather"] > 70:
        recommendations.append("Adopt climate-resilient crop varieties.")
        recommendations.append("Implement water harvesting or drip irrigation systems.")

    # FINANCIAL
    if breakdown["financial"] > 70:
        recommendations.append("Reassess input costs and explore government subsidy programs.")
        recommendations.append("Consider restructuring loan repayment schedules.")

    # MARKET
    if breakdown["market"] > 70:
        recommendations.append("Utilize storage facilities to avoid distress selling.")
        recommendations.append("Explore contract farming or forward price agreements.")

    # PEST
    if breakdown["pest"] > 75:
        recommendations.append("Adopt Integrated Pest Management (IPM) practices.")
        recommendations.append("Increase pest surveillance and early detection.")

    # SOIL
    if breakdown["soil"] > 75:
        recommendations.append("Conduct soil health testing and nutrient profiling.")
        recommendations.append("Adopt crop rotation and organic soil conditioning.")

    # REGION SPECIFIC
    if region == "Dryland":
        recommendations.append("Consider drought-resistant crop alternatives.")

    if region == "Coastal":
        recommendations.append("Develop contingency planning for extreme weather events.")

    # WATER SOURCE SPECIFIC
    if water_source == "Rainfed":
        recommendations.append("Improve irrigation reliability to reduce rainfall dependency.")

    # INSURANCE
    if insurance == "No":
        recommendations.append("Enroll in crop insurance schemes to buffer financial shocks.")

    if len(recommendations) == 0:
        recommendations.append("Farm conditions are stable. Continue current management practices.")

    return recommendations


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
        if hasattr(model, "predict_proba"):
            ml_probability = model.predict_proba(input_array)[0][1] * 100
        else:
            ml_probability = model.predict(input_array)[0] * 100

        ml_probability = round(float(ml_probability), 2)

        # ================= EXTRACT INPUTS =================
        season = data.get("Season", "NORMAL").upper()
        crop = data.get("Crop_Type", "").strip().lower()
        region = data.get("Region", "Normal")
        water_source = data.get("Water_Source", "Rainfed")
        insurance = data.get("Insurance", "No")

        rainfall = safe_float(data.get("Rainfall_Deviation"))
        market_vol = safe_float(data.get("Market_Volatility"))
        input_cost = safe_float(data.get("Input_Cost"))
        loan_amount = safe_float(data.get("Loan_Amount"))
        storage = safe_float(data.get("Storage_Access"))
        income = safe_float(data.get("Income_Stability"))

        if loan_amount <= 0:
            loan_amount = 1

        adjustment_notes = []

        # ================= BASE RISK CALCULATION =================
        weather_risk = min(max(abs(rainfall) * 2, 5), 100)
        market_risk = min(max(abs(market_vol) * 120, 5), 100)

        cost_ratio = input_cost / loan_amount
        financial_risk = min(max(cost_ratio * 100, 5), 100)

        if storage == 1:
            financial_risk *= 0.85

        if income == 0:
            market_risk *= 1.1

        pest_risk = min(max((abs(rainfall) * 1.5) + (ml_probability * 0.4), 5), 100)
        soil_risk = min(max(abs(rainfall) * 1.2, 5), 100)

        # ================= REGION EFFECT =================
        if region == "Coastal":
            weather_risk *= 1.15
            adjustment_notes.append("Coastal region increases exposure to storm volatility.")

        elif region == "Dryland":
            soil_risk *= 1.20
            financial_risk *= 1.10
            pest_risk *= 1.15
            adjustment_notes.append("Dryland region increases drought and pest pressure.")

        # ================= WATER SOURCE EFFECT =================
        if water_source == "Rainfed":
            weather_risk *= 1.25
            adjustment_notes.append("Rainfed irrigation increases rainfall dependency.")

        elif water_source == "Canal":
            weather_risk *= 0.95
            adjustment_notes.append("Canal irrigation stabilizes rainfall dependency.")

        elif water_source == "Drip":
            weather_risk *= 0.85
            financial_risk *= 0.95
            adjustment_notes.append("Drip irrigation improves efficiency and reduces risk.")

        # ================= INSURANCE EFFECT =================
        insurance_buffer = 0

        if insurance == "Yes":
            financial_risk *= 0.80
            market_risk *= 0.90
            insurance_buffer = 5
            adjustment_notes.append("Crop insurance provides financial protection.")

        # Cap risks
        weather_risk = min(weather_risk, 100)
        market_risk = min(market_risk, 100)
        financial_risk = min(financial_risk, 100)
        pest_risk = min(pest_risk, 100)
        soil_risk = min(soil_risk, 100)

        # ================= SEASONAL WEIGHTING =================
        if season == "MONSOON":
            weights = {"weather": 0.50, "market": 0.15, "financial": 0.15, "pest": 0.10, "soil": 0.10}
        elif season == "HARVEST":
            weights = {"weather": 0.15, "market": 0.50, "financial": 0.15, "pest": 0.10, "soil": 0.10}
        else:
            weights = {"weather": 0.20, "market": 0.20, "financial": 0.20, "pest": 0.20, "soil": 0.20}

        # ================= FINAL SCORE =================
        weighted_score = (
            weather_risk * weights["weather"] +
            market_risk * weights["market"] +
            financial_risk * weights["financial"] +
            pest_risk * weights["pest"] +
            soil_risk * weights["soil"]
        )

        final_score = (weighted_score * 0.7) + (ml_probability * 0.3)
        final_score -= insurance_buffer

        if crop in ["strawberry", "grapes"]:
            final_score += 10
            adjustment_notes.append("High-value crops increase market volatility exposure.")

        final_score = round(min(max(final_score, 0), 100), 2)

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
            "weather": "Weather variability is the primary instability driver.",
            "market": "Market price volatility is heavily impacting stability.",
            "financial": "Loan-to-input ratio indicates financial stress exposure.",
            "pest": "Elevated pest exposure risk detected.",
            "soil": "Soil instability contributes to yield uncertainty."
        }

        summary = summary_map.get(highest_driver)

        # ================= ALERT ENGINE =================
        alerts = []

        if final_score > 75:
            alerts.append({"type": "critical",
                           "title": "High Distress Risk",
                           "message": "Overall farm stability exceeds safe threshold."})
        elif final_score >= 40:
            alerts.append({"type": "warning",
                           "title": "Moderate Risk Detected",
                           "message": "Farm exposed to elevated instability factors."})

        if weather_risk > 70:
            alerts.append({"type": "warning",
                           "title": "Weather Vulnerability",
                           "message": "High rainfall variability exposure."})

        if financial_risk > 70:
            alerts.append({"type": "critical",
                           "title": "Financial Stress",
                           "message": "High input cost relative to loan amount."})

        if market_risk > 70:
            alerts.append({"type": "warning",
                           "title": "Market Volatility",
                           "message": "Significant market price instability detected."})

        if pest_risk > 75:
            alerts.append({"type": "warning",
                           "title": "Pest Exposure",
                           "message": "Elevated pest outbreak probability."})

        if soil_risk > 75:
            alerts.append({"type": "warning",
                           "title": "Soil Instability",
                           "message": "Soil variability contributing to yield risk."})

        # ================= AI HELP GUIDE =================
        recommendations = generate_recommendations(
            final_score,
            breakdown,
            region,
            water_source,
            insurance
        )

        return jsonify({
            "risk_score": final_score,
            "risk_level": risk_level,
            "breakdown": breakdown,
            "summary": summary,
            "season": season,
            "adjustments": adjustment_notes,
            "alerts": alerts,
            "recommendations": recommendations
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
