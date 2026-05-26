import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oic_stock_alert.env_loader import apply_env_defaults, load_env_file


class EnvLoaderTests(unittest.TestCase):
    def test_load_env_file_ignores_comments_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                """
                # local provider settings
                QUOTE_PROVIDER_MODE = live

                QUOTE_PROVIDER_NAME=alpha_vantage
                QUOTE_PROVIDER_API_KEY="secret-value"
                """,
                encoding="utf-8",
            )

            values = load_env_file(env_path)

        self.assertEqual("live", values["QUOTE_PROVIDER_MODE"])
        self.assertEqual("alpha_vantage", values["QUOTE_PROVIDER_NAME"])
        self.assertEqual("secret-value", values["QUOTE_PROVIDER_API_KEY"])

    def test_apply_env_defaults_does_not_override_process_environment(self):
        original = os.environ.get("QUOTE_PROVIDER_MODE")
        os.environ["QUOTE_PROVIDER_MODE"] = "mock"
        try:
            apply_env_defaults({"QUOTE_PROVIDER_MODE": "live"})
            self.assertEqual("mock", os.environ["QUOTE_PROVIDER_MODE"])
        finally:
            if original is None:
                os.environ.pop("QUOTE_PROVIDER_MODE", None)
            else:
                os.environ["QUOTE_PROVIDER_MODE"] = original


if __name__ == "__main__":
    unittest.main()
