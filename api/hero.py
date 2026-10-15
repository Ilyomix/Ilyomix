"""The profile header, live: counts the view in Redis and greets the visitor by number."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import SVG, redis, send  # noqa: E402
import build  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        n = (redis(['INCR', 'profile-visits']) or [None])[0]
        send(self, build.hero(n if isinstance(n, int) else None)[1].encode(), headers=[SVG])
