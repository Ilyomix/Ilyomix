"""One slice of the pet card (?part=1..8), drawn from the state api/act.py keeps in Redis."""
import datetime as dt
import functools
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import SVG, redis, send  # noqa: E402
import build  # noqa: E402


@functools.lru_cache(maxsize=4)
def card(fields, minute):
    """A page view asks for all eight slices: one render per state and minute serves them."""
    return build.pet_panel(build.pet_state(dict(fields)), minute)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        part = parse_qs(urlparse(self.path).query).get('part', ['1'])[0]
        flat = (redis(['HGETALL', 'profile-pet']) or [None])[0] or []
        svgs = card(tuple(zip(flat[::2], flat[1::2])), dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0))
        i = int(part) - 1 if part.isdigit() and 1 <= int(part) <= len(svgs) else 0
        send(self, svgs[i].encode(), headers=[SVG])
