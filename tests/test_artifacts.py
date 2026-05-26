import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oic_stock_alert.app import StockAlertApp
from oic_stock_alert.config import Settings


ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class ArtifactTests(unittest.TestCase):
    def test_json_artifacts_are_parseable(self):
        json_files = sorted(ARTIFACTS_DIR.rglob("*.json"))
        self.assertGreater(len(json_files), 0)
        for json_file in json_files:
            with self.subTest(json_file=json_file):
                with json_file.open(encoding="utf-8") as handle:
                    json.load(handle)

    def test_sample_alert_request_matches_runtime_branch(self):
        payload = self._load_json("samples/evaluate-alert-triggered.request.json")
        status, response = StockAlertApp(Settings()).evaluate(payload)
        self.assertEqual(200, status)
        self.assertEqual("ALERT_TRIGGERED", response["decision"]["code"])
        self.assertEqual("ALERT_TRIGGERED", response["oic"]["switchBranch"])

    def test_sample_no_alert_request_matches_runtime_branch(self):
        payload = self._load_json("samples/evaluate-no-alert.request.json")
        status, response = StockAlertApp(Settings()).evaluate(payload)
        self.assertEqual(200, status)
        self.assertEqual("NO_ALERT", response["decision"]["code"])
        self.assertEqual("NO_ALERT", response["oic"]["switchBranch"])

    def test_response_samples_expose_expected_oic_branches(self):
        expected = {
            "samples/evaluate-alert-triggered.response.json": "ALERT_TRIGGERED",
            "samples/evaluate-no-alert.response.json": "NO_ALERT",
            "samples/validation-error.response.json": "INPUT_ERROR",
            "samples/provider-timeout.response.json": "PROVIDER_TIMEOUT",
        }
        for relative_path, branch in expected.items():
            with self.subTest(relative_path=relative_path):
                payload = self._load_json(relative_path)
                self.assertEqual(branch, payload["oic"]["switchBranch"])

    def _load_json(self, relative_path):
        with (ARTIFACTS_DIR / relative_path).open(encoding="utf-8") as handle:
            return json.load(handle)


if __name__ == "__main__":
    unittest.main()
