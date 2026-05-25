import socket
import unittest
from unittest.mock import patch

from oic_stock_alert.alpha_vantage_provider import get_alpha_vantage_quote, normalize_global_quote
from oic_stock_alert.config import Settings
from oic_stock_alert.errors import ProviderError, ProviderTimeoutError, QuoteNotFoundError
from oic_stock_alert.quote_provider import get_quote


GLOBAL_QUOTE = {
    "Global Quote": {
        "01. symbol": "IBM",
        "02. open": "182.0000",
        "03. high": "184.2500",
        "04. low": "181.5000",
        "05. price": "183.4500",
        "06. volume": "1234567",
        "07. latest trading day": "2026-05-26",
        "08. previous close": "181.0000",
        "09. change": "2.4500",
        "10. change percent": "1.3536%",
    }
}


class AlphaVantageProviderTests(unittest.TestCase):
    def test_normalize_global_quote(self):
        quote = normalize_global_quote(GLOBAL_QUOTE)

        self.assertEqual("IBM", quote["symbol"])
        self.assertEqual(183.45, quote["lastPrice"])
        self.assertEqual(184.25, quote["dayHigh"])
        self.assertEqual(181.5, quote["dayLow"])
        self.assertEqual(1234567, quote["volume"])
        self.assertEqual(1.3536, quote["changePercent"])
        self.assertEqual("alpha_vantage", quote["provider"])
        self.assertEqual("2026-05-26T00:00:00Z", quote["asOf"])

    def test_empty_global_quote_maps_to_quote_not_found(self):
        with self.assertRaises(QuoteNotFoundError):
            normalize_global_quote({"Global Quote": {}})

    def test_rate_limit_note_maps_to_provider_error(self):
        with self.assertRaises(ProviderError):
            normalize_global_quote({"Note": "Thank you for using Alpha Vantage."})

    def test_information_maps_to_provider_error(self):
        with self.assertRaises(ProviderError):
            normalize_global_quote({"Information": "Invalid API key."})

    def test_malformed_quote_maps_to_provider_error(self):
        with self.assertRaises(ProviderError):
            normalize_global_quote({"Global Quote": {"01. symbol": "IBM"}})

    def test_live_mode_requires_api_key(self):
        settings = Settings(quote_provider_mode="live", quote_provider_name="alpha_vantage", quote_provider_api_key=None)
        with self.assertRaises(ProviderError) as context:
            get_quote("IBM", settings)
        self.assertNotIn("apikey", str(context.exception).lower())
        self.assertNotIn("secret", str(context.exception).lower())

    def test_live_mode_rejects_unsupported_provider(self):
        settings = Settings(quote_provider_mode="live", quote_provider_name="other", quote_provider_api_key="secret")
        with self.assertRaises(ProviderError):
            get_quote("IBM", settings)

    def test_timeout_maps_to_provider_timeout(self):
        settings = Settings(
            quote_provider_mode="live",
            quote_provider_name="alpha_vantage",
            quote_provider_api_key="secret",
            quote_provider_timeout_ms=1500,
        )
        with patch("oic_stock_alert.alpha_vantage_provider.urlopen", side_effect=socket.timeout()):
            with self.assertRaises(ProviderTimeoutError):
                get_alpha_vantage_quote("IBM", settings)


if __name__ == "__main__":
    unittest.main()
