"""A click on the pet card: records feed, pet, play or a switch (?do=choose&pet=fox) in Redis, then sends
the visitor straight back to the card on the profile, which now shows the reaction."""
import datetime as dt
import os
import re
import sys
import unicodedata
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import redis, send  # noqa: E402
import build  # noqa: E402

BACK = os.environ.get('PET_BACK', 'https://github.com/Ilyomix#pet')  # README.md anchors the card as "pet"; PET_BACK for local tests


def where(headers):
    """'LYON, FR' from Vercel's geolocation headers (the city arrives percent-encoded), in the LED font's letters."""
    def plain(v):
        return re.sub(r'[^A-Z .-]', '', unicodedata.normalize('NFKD', unquote(v or '')).encode('ascii', 'ignore').decode().upper()).strip()
    city, country = plain(headers.get('x-vercel-ip-city'))[:16], plain(headers.get('x-vercel-ip-country'))[:2]
    return ', '.join(x for x in (city, country) if x)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        do, kind = q.get('do', [''])[0], q.get('pet', [''])[0]
        at, place = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), where(self.headers)
        if do in ('feed', 'pet', 'play'):
            redis(['HINCRBY', 'profile-pet', do, 1], ['HSET', 'profile-pet', 'last_action', do, 'last_at', at, 'last_where', place])
        elif do == 'choose' and kind in build.PETS:
            redis(['HSET', 'profile-pet', 'chosen', kind, 'last_action', 'choose', 'last_kind', kind, 'last_at', at, 'last_where', place])
        send(self, b'', 302, [('Location', BACK)])  # anything else is ignored, and the visitor still goes back
