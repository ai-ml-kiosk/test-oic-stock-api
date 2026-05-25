"""HTTP server entry point using the Python standard library."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .app import StockAlertApp, parse_json_body
from .config import load_settings
from .errors import StockAlertError, ValidationError
from .mapper import build_error_response
from .validation import resolve_request_id


class StockAlertHandler(BaseHTTPRequestHandler):
    app = StockAlertApp()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, self.app.health())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "error": {"code": "NOT_FOUND", "message": "Route not found"}})

    def do_POST(self) -> None:
        if self.path != "/v1/alerts/evaluate":
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "error": {"code": "NOT_FOUND", "message": "Route not found"}})
            return

        request_id = self.headers.get("X-Request-Id")
        try:
            content_type = self.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise ValidationError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = parse_json_body(body)
            status_code, response = self.app.evaluate(payload, request_id)
            self._send_json(status_code, response)
        except StockAlertError as error:
            response = build_error_response(error, resolve_request_id(None, request_id))
            self._send_json(error.status_code, response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.send_response(int(status_code))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    settings = load_settings()
    StockAlertHandler.app = StockAlertApp(settings)
    server = ThreadingHTTPServer(("", settings.port), StockAlertHandler)
    print(f"oic-stock-alert listening on http://localhost:{settings.port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

