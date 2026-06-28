from flask import Flask, request, jsonify
from prediction import make_prediction  # we'll use your existing model logic

app = Flask(__name__)


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True) or {}
    ticker = data.get("ticker")

    if not ticker:
        return jsonify({"error": "ticker is required"}), 400

    try:
        actual, predicted = make_prediction(ticker)

        actual = [float(x) for x in actual]
        predicted = [float(x) for x in predicted]

        return jsonify({
            "ticker": ticker,
            "actual_prices": actual,
            "predicted_prices": predicted
        })
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
