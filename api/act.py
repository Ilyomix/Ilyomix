"""A click on the pet card: records feed, pet, play or a switch (?do=choose&pet=fox) in Redis, plays the
button being pressed for a moment (a README can't react to the mouse: its SVGs are images), then sends the
visitor back to the card on the profile, which now shows the reaction. It records what was done and when,
nothing about who did it or where from."""
import datetime as dt
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _redis import redis, send  # noqa: E402
import build  # noqa: E402

BACK = os.environ.get('PET_BACK', 'https://github.com/Ilyomix#pet')  # README.md anchors the card as "pet"; PET_BACK for local tests
HOLD_MS = 800  # how long the press shows; location.replace keeps this page out of the back button's history


def page(svg):
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex"><title>Back to the profile</title>'
            '<style>html{color-scheme:dark}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0d1117}'
            'svg{width:min(92vw,520px);height:auto}</style>' + svg
            + f'<script>setTimeout(function(){{location.replace({json.dumps(BACK)})}},{HOLD_MS})</script>'
            f'<noscript><meta http-equiv="refresh" content="1;url={html.escape(BACK)}"></noscript>')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        do, kind = q.get('do', [''])[0], q.get('pet', [''])[0]
        at = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        forget = ['HDEL', 'profile-pet', 'last_where']  # the city the card used to show: dropped on the next click
        if do in ('feed', 'pet', 'play'):
            redis(['HINCRBY', 'profile-pet', do, 1], ['HSET', 'profile-pet', 'last_action', do, 'last_at', at], forget)
        elif do == 'choose' and kind in build.PETS:
            redis(['HSET', 'profile-pet', 'chosen', kind, 'last_action', 'choose', 'last_kind', kind, 'last_at', at], forget)
        else:
            return send(self, b'', 302, [('Location', BACK)])  # anything else is ignored, and the visitor goes straight back
        send(self, page(build.pet_press(do, kind)).encode(), headers=[('Content-Type', 'text/html; charset=utf-8')])
