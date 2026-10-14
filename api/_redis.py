"""Shared by the functions in api/ (the underscore keeps Vercel from serving it): Upstash Redis over REST,
and the uncacheable response. Needs UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN, or the
KV_REST_API_URL / KV_REST_API_TOKEN pair that Vercel's Upstash integration creates."""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'profile'))  # build.py: not a package, and `profile` is a stdlib name


def redis(*commands):
    """Runs the commands as one pipeline; their results, or None if Redis is unset, unreachable or errs."""
    url = os.environ.get('UPSTASH_REDIS_REST_URL') or os.environ.get('KV_REST_API_URL')
    token = os.environ.get('UPSTASH_REDIS_REST_TOKEN') or os.environ.get('KV_REST_API_TOKEN')
    if not (url and token):
        return None
    req = urllib.request.Request(f"{url.rstrip('/')}/pipeline", data=json.dumps(commands).encode(),
                                 headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=3) as res:
            out = json.load(res)
    except (OSError, ValueError):
        return None
    return None if any('error' in o for o in out) else [o.get('result') for o in out]


def send(handler, body, status=200, headers=()):
    """GitHub's image proxy keeps a copy unless told not to; every view has to reach us."""
    handler.send_response(status)
    for k, v in (('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0'), *headers):
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body)


SVG = ('Content-Type', 'image/svg+xml; charset=utf-8')
