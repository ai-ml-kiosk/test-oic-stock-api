import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oic_stock_alert.evaluator import build_decision, evaluate_rules
from oic_stock_alert.validation import validate_request
from oic_stock_alert.errors import UnsupportedRuleError, ValidationError


QUOTE = {
    "symbol": "ORCL",
    "lastPrice": 152.31,
    "currency": "USD",
    "change": 2.14,
    "changePercent": -3.2,
    "dayHigh": 153.2,
    "dayLow": 149.7,
    "volume": 12654321,
    "asOf": "2026-05-25T05:30:00Z",
    "provider": "mock",
}


class EvaluatorTests(unittest.TestCase):
    def test_last_price_gte_threshold_triggers(self):
        rules = [{"ruleId": "r1", "metric": "lastPrice", "operator": "gte", "threshold": 150.0, "severity": "high", "message": ""}]
        evaluations = evaluate_rules(rules, QUOTE)
        self.assertTrue(evaluations[0]["triggered"])

    def test_last_price_lt_threshold_does_not_trigger(self):
        rules = [{"ruleId": "r1", "metric": "lastPrice", "operator": "lt", "threshold": 150.0, "severity": "high", "message": ""}]
        evaluations = evaluate_rules(rules, QUOTE)
        self.assertFalse(evaluations[0]["triggered"])

    def test_change_percent_abs_gte_threshold_triggers(self):
        rules = [{"ruleId": "r1", "metric": "changePercent", "operator": "absGte", "threshold": 3.0, "severity": "warning", "message": ""}]
        evaluations = evaluate_rules(rules, QUOTE)
        self.assertTrue(evaluations[0]["triggered"])

    def test_aggregate_uses_highest_triggered_severity(self):
        rules = [
            {"ruleId": "r1", "metric": "lastPrice", "operator": "gte", "threshold": 150.0, "severity": "warning", "message": ""},
            {"ruleId": "r2", "metric": "volume", "operator": "gte", "threshold": 1.0, "severity": "critical", "message": ""},
        ]
        decision = build_decision("ORCL", evaluate_rules(rules, QUOTE))
        self.assertEqual("ALERT_TRIGGERED", decision["code"])
        self.assertEqual("critical", decision["severity"])

    def test_duplicate_rule_ids_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_request({"symbol": "ORCL", "rules": [{"ruleId": "dup", "metric": "lastPrice", "operator": "gte", "threshold": 1}, {"ruleId": "dup", "metric": "lastPrice", "operator": "gte", "threshold": 1}]})

    def test_unsupported_metric_is_rejected(self):
        with self.assertRaises(UnsupportedRuleError):
            validate_request({"symbol": "ORCL", "rules": [{"ruleId": "bad", "metric": "peRatio", "operator": "gte", "threshold": 1}]})


if __name__ == "__main__":
    unittest.main()
