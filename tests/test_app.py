import unittest
from unittest.mock import patch

from RT_price import app, quote_cache


class AppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        quote_cache.clear()
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_invalid_tickers_are_rejected(self):
        for ticker in ("", "<script>", "A" * 16):
            with self.subTest(ticker=ticker):
                response = self.client.post("/get_stock_data", json={"ticker": ticker})
                self.assertEqual(response.status_code, 400)

    @patch("RT_price.requests.get")
    def test_stock_data_success(self, get_mock):
        get_mock.return_value.json.return_value = {"open": "100.0", "close": "102.5"}
        response = self.client.post("/get_stock_data", json={"ticker": "aapl"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"currentPrice": 102.5, "openPrice": 100.0})
        self.assertEqual(get_mock.call_args.kwargs["params"]["symbol"], "AAPL")

    @patch("RT_price.get_prediction_from_service", return_value=([1, 2], [3]))
    def test_prediction_success(self, _prediction_mock):
        response = self.client.post("/predict", json={"ticker": "MSFT"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["predicted_next_close"], 3.0)


if __name__ == "__main__":
    unittest.main()
