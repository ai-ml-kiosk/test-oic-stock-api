import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from oic_stock_alert.app import StockAlertApp
from oic_stock_alert.config import Settings
from oic_stock_alert.server import StockAlertHandler


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handler = type("TestStockAlertHandler", (StockAlertHandler,), {})
        cls.handler.app = StockAlertApp(Settings(port=0))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.handler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health(self):
        status, body = self._get("/health")
        self.assertEqual(200, status)
        self.assertEqual("ok", body["status"])
        self.assertEqual("oic-stock-alert", body["service"])

    def test_alert_triggered_response(self):
        status, body = self._post(
            "/v1/alerts/evaluate",
            {
                "requestId": "oic-run-1",
                "source": {"system": "OIC", "integrationName": "StockAlertIntegration", "instanceId": "300000123"},
                "symbol": "ORCL",
                "rules": [{"ruleId": "orcl-above-150", "metric": "lastPrice", "operator": "gte", "threshold": 150.0, "severity": "high", "message": "ORCL crossed target price"}],
                "options": {"includeDiagnostics": True},
            },
        )
        self.assertEqual(200, status)
        self.assertEqual("ALERT_TRIGGERED", body["decision"]["code"])
        self.assertEqual("ALERT_TRIGGERED", body["oic"]["switchBranch"])
        self.assertTrue(body["oic"]["notificationRecommended"])
        self.assertEqual("300000123", body["oic"]["trackingId"])
        self.assertIn("diagnostics", body)

    def test_no_alert_response(self):
        status, body = self._post(
            "/v1/alerts/evaluate",
            {
                "requestId": "oic-run-2",
                "symbol": "ORCL",
                "rules": [{"ruleId": "orcl-above-200", "metric": "lastPrice", "operator": "gte", "threshold": 200.0}],
            },
        )
        self.assertEqual(200, status)
        self.assertEqual("NO_ALERT", body["decision"]["code"])
        self.assertEqual("NO_ALERT", body["oic"]["switchBranch"])
        self.assertFalse(body["oic"]["notificationRecommended"])

    def test_invalid_symbol_response(self):
        status, body = self._post(
            "/v1/alerts/evaluate",
            {
                "requestId": "oic-run-3",
                "symbol": "BAD SYMBOL",
                "rules": [{"ruleId": "r1", "metric": "lastPrice", "operator": "gte", "threshold": 150.0}],
            },
            expected_error=True,
        )
        self.assertEqual(400, status)
        self.assertEqual("VALIDATION_ERROR", body["error"]["code"])
        self.assertEqual("INPUT_ERROR", body["oic"]["switchBranch"])

    def test_quote_unavailable_response(self):
        status, body = self._post(
            "/v1/alerts/evaluate",
            {
                "requestId": "oic-run-4",
                "symbol": "MISSING",
                "rules": [{"ruleId": "r1", "metric": "lastPrice", "operator": "gte", "threshold": 150.0}],
            },
            expected_error=True,
        )
        self.assertEqual(502, status)
        self.assertEqual("QUOTE_NOT_FOUND", body["error"]["code"])
        self.assertEqual("QUOTE_UNAVAILABLE", body["oic"]["switchBranch"])

    def test_provider_timeout_response(self):
        status, body = self._post(
            "/v1/alerts/evaluate",
            {
                "requestId": "oic-run-5",
                "symbol": "TIMEOUT",
                "rules": [{"ruleId": "r1", "metric": "lastPrice", "operator": "gte", "threshold": 150.0}],
            },
            expected_error=True,
        )
        self.assertEqual(504, status)
        self.assertEqual("PROVIDER_TIMEOUT", body["oic"]["switchBranch"])
        self.assertTrue(body["oic"]["retryRecommended"])

    def _get(self, path):
        with urlopen(f"{self.base_url}{path}", timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _post(self, path, payload, expected_error=False):
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if not expected_error:
                raise
            try:
                return error.code, json.loads(error.read().decode("utf-8"))
            finally:
                error.close()


if __name__ == "__main__":
    unittest.main()
