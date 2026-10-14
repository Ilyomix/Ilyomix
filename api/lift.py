"""The Lift band of the projects card, live: the iPhone's lock screen shows the time of the request."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import SVG, send  # noqa: E402
import build  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send(self, build.projects_card(only=2)[0].encode(), headers=[SVG])
