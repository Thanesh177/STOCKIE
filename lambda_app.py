import json
import os
import numpy as np
import yfinance as yf
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

MODEL_PATH = os.environ.get("MODEL_PATH", "stoc.h5")
LOOKBACK = int(os.environ.get("LOOKBACK", "60"))

_model = None

def load_model_once():
    global _model
    if _model is None:
        # compile=False is good for inference-only loads
        _model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    return _model

def get_close_prices(ticker: str):
    t = ticker.upper().strip()

    df = yf.download(
        t,
        period="2y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        raise ValueError(f"No price data returned from yfinance for ticker {t}")

    # yfinance sometimes returns multi-index columns
    if isinstance(df.columns, type(getattr(np, "array", object)())):
        pass

    # robust close extraction
    close = None
    for col in ["Close", ("Close", t), ("Adj Close", t), "Adj Close"]:
        if col in df.columns:
            close = df[col]
            break

    if close is None:
        # fallback if columns are MultiIndex like ('Close','AAPL')
        if hasattr(df.columns, "levels") and "Close" in df.columns.levels[0]:
            close = df["Close"]
            if hasattr(close, "columns") and close.shape[1] == 1:
                close = close.iloc[:, 0]

    if close is None:
        raise ValueError("Could not find Close column in yfinance response")

    close = close.dropna().astype(float).to_numpy().reshape(-1, 1)
    if len(close) < LOOKBACK:
        raise ValueError(f"Not enough data. Need at least {LOOKBACK} rows.")
    return close

def predict_next(ticker: str):
    close_prices = get_close_prices(ticker)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(close_prices)

    x_input = scaled[-LOOKBACK:].reshape(1, LOOKBACK, 1)

    model = load_model_once()
    pred_scaled = model.predict(x_input, verbose=0)

    predicted = scaler.inverse_transform(pred_scaled).flatten().tolist()
    actual = close_prices[-LOOKBACK:].flatten().tolist()

    # ensure plain floats for JSON
    actual = [float(x) for x in actual]
    predicted = [float(x) for x in predicted]
    return actual, predicted

def handler(event, context):
    try:
        body = event.get("body") or "{}"
        if isinstance(body, str):
            body = json.loads(body)

        ticker = (body.get("ticker") or "").strip()
        if not ticker:
            return {"statusCode": 400, "body": json.dumps({"error": "ticker is required"})}

        actual, predicted = predict_next(ticker)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "ticker": ticker.upper(),
                "actual_prices": actual,
                "predicted_prices": predicted,
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }