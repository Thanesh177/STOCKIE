import unittest
from unittest.mock import patch

import web_scrapping


class FinnhubTests(unittest.TestCase):
    def setUp(self):
        web_scrapping.finnhub_cache.clear()

    @patch("web_scrapping.requests.get")
    def test_profile_uses_finnhub(self, get_mock):
        get_mock.return_value.json.return_value = {
            "name": "Apple Inc", "finnhubIndustry": "Technology", "exchange": "NASDAQ",
            "country": "US", "marketCapitalization": 3000000, "weburl": "https://apple.com",
        }
        profile = web_scrapping.summary("AAPL")
        self.assertEqual(profile["Company"], "Apple Inc")
        self.assertEqual(profile["Market Capitalization"], "$3,000,000M")
        self.assertIn("stock/profile2", get_mock.call_args.args[0])

    @patch("web_scrapping.requests.get")
    def test_news_uses_finnhub(self, get_mock):
        get_mock.return_value.json.return_value = [{"headline": "Apple update", "url": "https://example.com"}]
        news = web_scrapping.data("AAPL")
        self.assertEqual(news, [{"title": "Apple update", "url": "https://example.com"}])
        self.assertIn("company-news", get_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
