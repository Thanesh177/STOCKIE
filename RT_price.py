from flask import Flask, render_template, jsonify, request
from functools import lru_cache
import yfinance as yf
import matplotlib
import datetime as dt
import os
import requests

# Internal modules
from web_scrapping import summary, event, data as fetch_news

# --- Prediction API configuration ---
# In AWS App Runner set env var:
#   PREDICTION_API_URL = "https://wkw282o5ke.execute-api.us-east-2.amazonaws.com"  (base)
# or
#   PREDICTION_API_URL = "https://wkw282o5ke.execute-api.us-east-2.amazonaws.com/predict" (full)
PREDICTION_API_URL: str | None = os.environ.get(
    "PREDICTION_API_URL",
    "http://127.0.0.1:9000/predict",  # local default
)


def _to_float_list(values):
    """Convert numpy/pandas scalars to plain Python floats for JSON serialization."""
    if values is None:
        return []
    out = []
    for v in list(values):
        try:
            out.append(float(v))
        except Exception:
            continue
    return out


def get_prediction_from_service(ticker: str):
    """Call the external ML prediction service with the given ticker.

    Supports either response shape:
      1) {"actual_prices": [...], "predicted_prices": [...]}  (our frontend)
      2) {"last_60_actual": [...], "predicted": [...], "next_price": number} (your Lambda)

    Raises RuntimeError with a useful message on failure.
    """
    if not PREDICTION_API_URL:
        raise RuntimeError("PREDICTION_API_URL environment variable is not set")

    t = (ticker or "").strip().upper()
    if not t:
        raise RuntimeError("ticker is required")

    # Allow passing base URL (auto-append /predict)
    url = PREDICTION_API_URL.rstrip("/")
    if not url.endswith("/predict"):
        url = f"{url}/predict"

    try:
        resp = requests.post(
            url,
            json={"ticker": t},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Prediction service request failed: {e}")

    if not resp.ok:
        body_preview = (resp.text or "").strip()
        if len(body_preview) > 1200:
            body_preview = body_preview[:1200] + "…"
        try:
            err_json = resp.json()
            if isinstance(err_json, dict) and err_json.get("error"):
                raise RuntimeError(f"Prediction service HTTP {resp.status_code}: {err_json['error']}")
        except Exception:
            pass
        raise RuntimeError(f"Prediction service HTTP {resp.status_code}: {body_preview or 'No body'}")

    try:
        data = resp.json()
    except Exception:
        body_preview = (resp.text or "").strip()
        if len(body_preview) > 1200:
            body_preview = body_preview[:1200] + "…"
        raise RuntimeError(f"Prediction service returned non-JSON: {body_preview or 'No body'}")

    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(str(data["error"]))

    actual = (data.get("actual_prices") if isinstance(data, dict) else None) or (
        data.get("last_60_actual") if isinstance(data, dict) else None
    )
    predicted = (data.get("predicted_prices") if isinstance(data, dict) else None) or (
        data.get("predicted") if isinstance(data, dict) else None
    )

    if actual is None:
        raise RuntimeError("Prediction service response missing actual prices")

    if predicted is None:
        if isinstance(data, dict) and "next_price" in data:
            predicted = [data["next_price"]]
        else:
            raise RuntimeError("Prediction service response missing predicted prices")

    return actual, predicted


# --- Matplotlib config ---
matplotlib.use("agg")

# --- Flask setup ---
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/middle")
def middle():
    return render_template("mid.html")


@app.route("/get_stock_data", methods=["POST"])
def get_stock_data():
    """Return last open/close price for a ticker."""
    try:
        body = request.get_json() or {}
        ticker = body.get("ticker")
        if not ticker:
            return jsonify({"error": "Ticker is required"}), 400

        data = yf.Ticker(ticker).history(period="1Y")
        if data.empty:
            return jsonify({"error": "No data available."}), 404

        return jsonify(
            {
                "currentPrice": float(data.iloc[-1].Close),
                "openPrice": float(data.iloc[-1].Open),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Browser-friendly page: always HTML
@app.route("/predict/<ticker>", methods=["GET"])
def predict_ticker(ticker):
    ticker = (ticker or "").upper().strip()

    # Client-side JS will call POST /predict (same-origin) for chart + prediction.
    predict_api_url = "/predict"

    if not ticker:
        return (
            render_template(
                "new.html",
                stock_data=None,
                news=[],
                next_day_prediction=None,
                s=None,
                predictions=[],
                plot_data=None,
                ticker="",
                predict_api_url=predict_api_url,
                predict_error="Ticker is required",
            ),
            400,
        )

    stock_data = None
    event_data = None
    news_data = []

    try:
        stock_data = summary(ticker)
    except Exception:
        stock_data = None

    try:
        event_data = event(ticker)
    except Exception:
        event_data = None

    try:
        news_data = fetch_news(ticker)
    except Exception:
        news_data = []

    return render_template(
        "new.html",
        stock_data=stock_data,
        news=news_data,
        next_day_prediction=None,
        s=event_data,
        predictions=[],
        plot_data=None,
        ticker=ticker,
        predict_api_url=predict_api_url,
        predict_error=None,
    )


# JSON endpoint consumed by app.js (same-origin). It calls API Gateway server-side.
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json() or {}
    ticker = (data.get("ticker") or "").upper().strip()

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        actual_prices, predicted_prices = get_prediction_from_service(ticker)

        actual_prices = _to_float_list(actual_prices)
        predicted_prices = _to_float_list(predicted_prices)
        next_close = predicted_prices[0] if predicted_prices else None

        return jsonify(
            {
                "ticker": ticker,
                "actual_prices": actual_prices,
                "predicted_prices": predicted_prices,
                "predicted_next_close": next_close,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "running"}), 200


@lru_cache(maxsize=100)
def fetch_stock_data(ticker: str):
    start = dt.datetime(2012, 1, 1)
    end = dt.datetime.now()
    try:
        return yf.download(tickers=[ticker], start=start, end=end, threads=False)
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)