"""The Lift band of the projects card, live: the iPhone's lock screen shows the time of the request."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import SVG, send  # noqa: E402
import build  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        shape = {} if parse_qs(urlparse(self.path).query).get('v') == ['2'] else build.LEGACY  # ?v=2: the README in use; without it, the one before
        send(self, build.projects_card(only=2, **shape)[1].encode(), headers=[SVG])
