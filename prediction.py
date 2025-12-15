import os
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf

# Global model cache and scaler
MODEL = None
SCALER = MinMaxScaler(feature_range=(0, 1))
MODEL_PATH = os.path.join(os.path.dirname(__file__), "stoc.h5")  # model file baked into the image

def load_model_local():
    """Load Keras model from local file inside the container."""
    global MODEL
    if MODEL is not None:
        return MODEL

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

    MODEL = load_model(MODEL_PATH)
    return MODEL

def _load_price_series_from_yfinance(ticker: str, period: str = "5y"):
    """
    Load historical closing prices for the given ticker using yfinance.
    """
    t = ticker.upper().strip()
    if not t:
        raise ValueError("Ticker symbol is required")

    # Fetch historical data (yf.download is usually faster/cleaner in Lambda)
    df = yf.download(t, period=period, interval="1d", progress=False, threads=False)

    if df is None or df.empty:
        raise ValueError(f"No price data returned from yfinance for ticker {t}")

    # yfinance can sometimes return MultiIndex columns like ('Close', 'AAPL')
    # or return df['Close'] as a DataFrame. Normalize this into a 1-D Series.
    close_obj = None

    if isinstance(df.columns, pd.MultiIndex):
        # Try the most common layouts
        for key in [("Close", t), ("Adj Close", t), ("Close",), ("Adj Close",)]:
            try:
                close_obj = df[key]
                if close_obj is not None:
                    break
            except Exception:
                pass
        if close_obj is None:
            # Fallback: find any column whose first level is Close
            try:
                close_cols = [c for c in df.columns if str(c[0]).lower() == "close"]
                if close_cols:
                    close_obj = df[close_cols[0]]
            except Exception:
                close_obj = None
    else:
        # Standard single-index columns
        if "Close" in df.columns:
            close_obj = df["Close"]
        elif "Adj Close" in df.columns:
            close_obj = df["Adj Close"]

    if close_obj is None:
        raise ValueError(f"yfinance data for {t} does not contain a Close-like column")

    # If Close came back as a DataFrame (e.g., multiple tickers), pick the ticker column if present
    if isinstance(close_obj, pd.DataFrame):
        if t in close_obj.columns:
            close_series = close_obj[t]
        else:
            close_series = close_obj.iloc[:, 0]
    else:
        close_series = close_obj

    # Ensure numeric close prices and drop non-numeric rows
    close_series = pd.to_numeric(close_series, errors="coerce").dropna()

    if close_series.empty:
        raise ValueError(f"No numeric closing price data for ticker {t}")

    close_prices = close_series.to_numpy(dtype=np.float32).reshape(-1, 1)
    if close_prices.size == 0:
        raise ValueError(f"No price data available for ticker {t}")

    return close_prices

def make_prediction(ticker: str):
    """
    Make a prediction for the given ticker using the Keras model and
    historical prices fetched from yfinance.
    """
    # 1. Load prices from yfinance
    close_prices = _load_price_series_from_yfinance(ticker)

    # Fit scaler on this ticker's history (per-request). This matches your current local behavior.
    scaled = SCALER.fit_transform(close_prices.astype(np.float32))

    # Make sure this matches your training window size
    lookback = 60
    if len(scaled) < lookback:
        raise ValueError("Not enough data to predict")

    x_input = scaled[-lookback:].reshape(1, lookback, 1).astype(np.float32)

    # 3. Model & predict
    model = load_model_local()
    pred_scaled = model.predict(x_input, verbose=0)

    # 4. Inverse transform predictions
    predicted = SCALER.inverse_transform(pred_scaled).flatten()
    actual = close_prices[-lookback:].flatten()

    # Convert to plain Python floats for JSON-serializable output
    actual = [float(x) for x in actual]
    predicted = [float(x) for x in predicted]

    return actual, predicted
