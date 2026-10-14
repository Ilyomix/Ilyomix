"""The Cadran band of the projects card, live: the downloads cadranapp.com counts in the same Redis, and
the Titan clock on its iMac set to the time of the request."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import SVG, redis, send  # noqa: E402
import build  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        n = (redis(['GET', 'download_clicks']) or [None])[0]
        send(self, build.projects_card(int(n) if str(n).isdigit() else None, only=1)[0].encode(), headers=[SVG])
