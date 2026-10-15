import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from glycolens import narrate

REPORT = {"stats": {"tir": 82.5, "tbr": 1.2}, "findings": [{"text": "Breakfast: 5 of 6 meals ended high"}],
          "suggestions": [], "watching": [], "changes": []}


def test_numbers_ok():
    assert narrate.numbers_ok("TIR was 82.5% with 5 of 6 breakfasts high.", json.dumps(REPORT))
    assert not narrate.numbers_ok("TIR was 90%.", json.dumps(REPORT))


@pytest.fixture
def server():
    replies = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = json.dumps({"choices": [{"message": {"content": replies[0]}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", replies
    httpd.shutdown()


def test_good_summary_is_kept_and_think_tags_stripped(server):
    url, replies = server
    replies.append("<think>hmm</think>82.5% in range; breakfast ran high on 5 of 6 days.")
    assert narrate.summarise(REPORT, url, "qwen") == "82.5% in range; breakfast ran high on 5 of 6 days."


def test_invented_number_is_rejected(server):
    url, replies = server
    replies.append("You were in range 95% of the time.")
    assert narrate.summarise(REPORT, url, "qwen") is None


def test_lm_studio_down_gives_none():
    assert narrate.summarise(REPORT, "http://127.0.0.1:9", "qwen", timeout=2) is None
