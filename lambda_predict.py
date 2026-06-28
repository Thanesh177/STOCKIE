import json
import traceback
from typing import Any, Dict

from prediction import make_prediction


def cors_headers() -> Dict[str, str]:
    return {
        "content-type": "application/json",
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "OPTIONS,POST",
        "access-control-allow-headers": "Content-Type",
    }


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Support API Gateway REST (v1), HTTP API (v2), and direct invocation."""
    body = event.get("body")

    # API GW may send body as a JSON string
    if isinstance(body, str) and body.strip():
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError("Request body must be valid JSON") from e

    # Sometimes tools send already-decoded dict
    if isinstance(body, dict):
        return body

    # Direct invoke: {"ticker":"AAPL"}
    return event


def handler(event, context):
    try:
        method = (
            (event.get("requestContext") or {}).get("http", {}).get("method")
            or event.get("httpMethod")
            or "POST"
        )

        # CORS preflight
        if method == "OPTIONS":
            return {"statusCode": 200, "headers": cors_headers(), "body": ""}

        if method != "POST":
            return {
                "statusCode": 405,
                "headers": cors_headers(),
                "body": json.dumps({"error": "Method not allowed"}),
            }

        body = parse_body(event)
        ticker = str(body.get("ticker", "")).upper().strip()
        if not ticker:
            return {
                "statusCode": 400,
                "headers": cors_headers(),
                "body": json.dumps({"error": "ticker is required"}),
            }

        actual, predicted = make_prediction(ticker)

        # Many LSTM models return 1-step prediction (length 1)
        next_price = predicted[-1] if predicted else None

        # FRONTEND-CONTRACT:
        # Use these keys because your JS chart expects arrays named this way.
        payload = {
            "ticker": ticker,
            "actual_prices": actual,           # last 60 closes
            "predicted_prices": predicted,     # model outputs
            "next_day_prediction": next_price, # convenience value
        }

        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps(payload),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers(),
            "body": json.dumps(
                {
                    "error": str(e),
                    "trace": traceback.format_exc(),
                }
            ),
        }