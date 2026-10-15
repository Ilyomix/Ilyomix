"""The live top of the pet card, drawn from the state api/act.py keeps in Redis. Its buttons and pet switch
are static files (profile/pet-actions-*.svg, pet-switch-*.svg), so they never wait on this function."""
import datetime as dt
import functools
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import SVG, redis, send  # noqa: E402
import build  # noqa: E402


@functools.lru_cache(maxsize=8)
def card(fields, minute):
    """One render per state and minute: a burst of views shares it."""
    return build.pet_panel(build.pet_state(dict(fields)), minute)[1]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):  # an old ?part= link still gets the scene
        flat = (redis(['HGETALL', 'profile-pet']) or [None])[0] or []
        svg = card(tuple(zip(flat[::2], flat[1::2])), dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0))
        send(self, svg.encode(), headers=[SVG])
