"""Small local uvicorn-compatible runner for PRISM cloud demos.

It is intentionally tiny: enough for `uvicorn main:app --reload` in environments
where external package installation is blocked. If real uvicorn is installed,
users can still use it; this fallback is installed by requirements.txt.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import asyncio


def main() -> None:
    sys.path.insert(0, os.getcwd())
    os.environ["PRISM_FORCE_MINI_FASTAPI"] = "1"
    parser = argparse.ArgumentParser(prog="uvicorn")
    parser.add_argument("target", help="ASGI target, e.g. main:app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Accepted for compatibility; reload is not needed in fallback mode.")
    args, _unknown = parser.parse_known_args()

    module_name, app_name = args.target.split(":", 1)
    app = getattr(importlib.import_module(module_name), app_name)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            self._handle()

        def _handle(self) -> None:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length) if length else b""
            if not hasattr(app, "dispatch"):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Fallback runner requires the local PRISM app object.")
                return
            status, payload, content_type = asyncio.run(app.dispatch(self.command, self.path.split("?", 1)[0], body))
            self.send_response(status)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(payload)))
            self.send_header("access-control-allow-origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"{self.address_string()} - {fmt % args}")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"PRISM fallback server running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
