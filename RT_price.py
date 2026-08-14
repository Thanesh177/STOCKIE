from flask import Flask, render_template, jsonify, request
import logging
import os
import re
import threading
import time
from pathlib import Path
import requests

# Internal modules
from web_scrapping import summary, event, data as fetch_news

def load_local_market_data_config() -> None:
    """Load local configuration without overriding deployed environment values."""
    env_path = Path(__file__).with_name(".env")
    if not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        key = key.strip()
        if separator and key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


load_local_market_data_config()

# --- API configuration ---
# In AWS App Runner set env var:
#   PREDICTION_API_URL = "https://wkw282o5ke.execute-api.us-east-2.amazonaws.com"  (base)
# or
#   PREDICTION_API_URL = "https://wkw282o5ke.execute-api.us-east-2.amazonaws.com/predict" (full)

PREDICTION_API_URL = os.environ.get("PREDICTION_API_URL")
PREDICTION_MODE = os.environ.get("PREDICTION_MODE", "remote").lower()
PREDICTION_TIMEOUT_SECONDS = float(os.environ.get("PREDICTION_TIMEOUT_SECONDS", "15"))
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")
TWELVE_DATA_QUOTE_URL = "https://api.twelvedata.com/quote"
QUOTE_CACHE_SECONDS = int(os.environ.get("QUOTE_CACHE_SECONDS", "60"))
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]{0,14}$")
quote_cache: dict[str, tuple[float, dict[str, float]]] = {}
quote_cache_lock = threading.Lock()

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def normalize_ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not TICKER_RE.fullmatch(ticker):
        raise ValueError("Ticker must be 1-15 valid symbol characters")
    return ticker


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


def get_stock_quote(ticker: str) -> dict[str, float]:
    """Return a Twelve Data quote, using a short cache to control API consumption."""
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("Market data service is not configured")

    now = time.monotonic()
    with quote_cache_lock:
        cached = quote_cache.get(ticker)
        if cached and cached[0] > now:
            return cached[1]

    try:
        response = requests.get(
            TWELVE_DATA_QUOTE_URL,
            params={"symbol": ticker, "apikey": TWELVE_DATA_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError("Market data service request failed") from exc
    except ValueError as exc:
        raise RuntimeError("Market data service returned invalid data") from exc

    if payload.get("status") == "error" or payload.get("code"):
        raise RuntimeError("Market data is unavailable for this symbol")

    try:
        quote = {"currentPrice": float(payload["close"]), "openPrice": float(payload["open"])}
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Market data response is incomplete") from exc

    with quote_cache_lock:
        quote_cache[ticker] = (now + QUOTE_CACHE_SECONDS, quote)
    return quote


def get_prediction_from_service(ticker: str):
    """Call the external ML prediction service with the given ticker.

    Supports either response shape:
      1) {"actual_prices": [...], "predicted_prices": [...]}  (our frontend)
      2) {"last_60_actual": [...], "predicted": [...], "next_price": number} (your Lambda)

    Raises RuntimeError with a useful message on failure.
    """
    t = normalize_ticker(ticker)

    if PREDICTION_MODE == "local":
        try:
            from prediction import make_prediction

            return make_prediction(t)
        except Exception as exc:
            raise RuntimeError(f"Local prediction failed: {exc}") from exc

    if not PREDICTION_API_URL:
        raise RuntimeError("Set PREDICTION_API_URL for the deployed prediction service, or PREDICTION_MODE=local on your computer")

    # Allow passing base URL (auto-append /predict)
    url = PREDICTION_API_URL.rstrip("/")
    if not url.endswith("/predict"):
        url = f"{url}/predict"

    try:
        resp = requests.post(
            url,
            json={"ticker": t},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=PREDICTION_TIMEOUT_SECONDS,
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


# --- Flask setup ---
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", "16384"))
app.config["JSON_SORT_KEYS"] = False


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' https://code.jquery.com https://cdnjs.cloudflare.com "
        "https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Request body is too large"}), 413


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
        body = request.get_json(silent=True) or {}
        ticker = normalize_ticker(body.get("ticker"))

        return jsonify(get_stock_quote(ticker))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Stock lookup failed")
        return jsonify({"error": "Unable to retrieve stock data"}), 502


# Browser-friendly page: always HTML
@app.route("/predict/<ticker>", methods=["GET"])
def predict_ticker(ticker):
    try:
        ticker = normalize_ticker(ticker)
    except ValueError as exc:
        return render_template("error.html", message=str(exc)), 400

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
    data = request.get_json(silent=True) or {}
    try:
        ticker = normalize_ticker(data.get("ticker"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

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
    except Exception:
        logger.exception("Prediction request failed", extra={"ticker": ticker})
        return jsonify({"error": "Prediction service is temporarily unavailable"}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
