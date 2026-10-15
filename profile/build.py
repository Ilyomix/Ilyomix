#!/usr/bin/env python3
"""Builds the animated LED panels used by README.md.

    python3 profile/build.py                         rebuild every panel
    python3 profile/build.py art AVATAR LIFT_ICON    re-import pixel art from images (needs Pillow)
    api/hero.py, api/pet.py, api/act.py              serve `hero` (with the visitor number) and `pet_panel` live from Vercel
    python3 profile/build.py stats                   refresh github.json (needs the gh CLI, logged in or with GH_TOKEN)
    python3 profile/build.py titles [FONT]           re-render the titles (needs Pillow; JetBrains Mono,
                                                     the variable font Crypto LED Board ships)

Fonts and palette come from Crypto LED Board (src/led/font*.ts, palette.ts). A panel is a
grid of LED dots: content is drawn as cell-aligned colour runs under one dot mask, so
anything moved by whole cells lands on the dots. Text colours are checked against WCAG AA
(4.5:1) on the panel background, and all motion is CSS so it stops under
prefers-reduced-motion.
"""
import colorsys
import copy
import datetime as dt
import functools
import json
import math
import re
import sys
from pathlib import Path

OUT = Path(__file__).parent
IMG = OUT / 'img'  # what README.md shows
TODAY = dt.date.today()

# --- fonts: Crypto LED Board src/led/font5x7.ts, font3x5.ts, font7x9.ts --------------

FONT_5X7 = {k: v.split() for k, v in {
    ' ': '00000 00000 00000 00000 00000 00000 00000',
    'A': '01110 10001 10001 11111 10001 10001 10001', 'B': '11110 10001 10001 11110 10001 10001 11110',
    'C': '01111 10000 10000 10000 10000 10000 01111', 'D': '11110 10001 10001 10001 10001 10001 11110',
    'E': '11111 10000 10000 11110 10000 10000 11111', 'F': '11111 10000 10000 11110 10000 10000 10000',
    'G': '01111 10000 10000 10111 10001 10001 01110', 'H': '10001 10001 10001 11111 10001 10001 10001',
    'I': '11111 00100 00100 00100 00100 00100 11111', 'J': '00111 00010 00010 00010 00010 10010 01100',
    'K': '10001 10010 10100 11000 10100 10010 10001', 'L': '10000 10000 10000 10000 10000 10000 11111',
    'M': '10001 11011 10101 10101 10001 10001 10001', 'N': '10001 11001 10101 10011 10001 10001 10001',
    'O': '01110 10001 10001 10001 10001 10001 01110', 'P': '11110 10001 10001 11110 10000 10000 10000',
    'Q': '01110 10001 10001 10001 10101 10011 01110', 'R': '11110 10001 10001 11110 10100 10010 10001',
    'S': '01111 10000 10000 01110 00001 00001 11110', 'T': '11111 00100 00100 00100 00100 00100 00100',
    'U': '10001 10001 10001 10001 10001 10001 01110', 'V': '10001 10001 10001 10001 10001 01010 00100',
    'W': '10001 10001 10001 10101 10101 10101 01010', 'X': '10001 10001 01010 00100 01010 10001 10001',
    'Y': '10001 10001 01010 00100 00100 00100 00100', 'Z': '11111 00001 00010 00100 01000 10000 11111',
    '0': '01110 10001 10011 10101 11001 10001 01110', '1': '00100 01100 00100 00100 00100 00100 01110',
    '2': '01110 10001 00001 00010 00100 01000 11111', '3': '11110 00001 00001 01110 00001 00001 11110',
    '4': '00010 00110 01010 10010 11111 00010 00010', '5': '11111 10000 10000 11110 00001 00001 11110',
    '6': '01110 10000 10000 11110 10001 10001 01110', '7': '11111 00001 00010 00100 01000 01000 01000',
    '8': '01110 10001 10001 01110 10001 10001 01110', '9': '01110 10001 10001 01111 00001 00001 01110',
    '/': '00001 00010 00100 01000 10000 00000 00000', '.': '00000 00000 00000 00000 00000 00110 00110',
    ',': '00000 00000 00000 00000 00110 00100 01000', ':': '00000 00110 00110 00000 00110 00110 00000',
    '-': '00000 00000 00000 11111 00000 00000 00000', '+': '00000 00100 00100 11111 00100 00100 00000',
    '?': '01110 10001 00001 00010 00100 00000 00100', '&': '01100 10010 10100 01000 10101 10010 01101',
    "'": '00100 00100 01000 00000 00000 00000 00000', '_': '00000 00000 00000 00000 00000 00000 11111',
    '#': '01010 01010 11111 01010 11111 01010 01010',
    # Added for this profile, same grid.
    '!': '00100 00100 00100 00100 00100 00000 00100',
    '·': '00000 00000 00000 00100 00000 00000 00000', '@': '01110 10001 10111 10101 10111 10000 01111',
    '▲': '00000 00000 00100 01110 11111 00000 00000', '▼': '00000 00000 11111 01110 00100 00000 00000',
    '◆': '00000 00100 01110 11111 01110 00100 00000', '↗': '00000 00111 00011 00101 01000 10000 00000',
}.items()}

FONT_3X5 = {k: v.split() for k, v in {
    ' ': '000 000 000 000 000',
    'A': '010 101 111 101 101', 'B': '110 101 110 101 110', 'C': '011 100 100 100 011', 'D': '110 101 101 101 110',
    'E': '111 100 110 100 111', 'F': '111 100 110 100 100', 'G': '011 100 101 101 011', 'H': '101 101 111 101 101',
    'I': '111 010 010 010 111', 'J': '001 001 001 101 010', 'K': '101 101 110 101 101', 'L': '100 100 100 100 111',
    'M': '10001 11011 10101 10001 10001', 'N': '1001 1101 1011 1001 1001', 'O': '010 101 101 101 010', 'P': '110 101 110 100 100',
    'Q': '010 101 101 010 001', 'R': '110 101 110 101 101', 'S': '011 100 010 001 110', 'T': '111 010 010 010 010',
    'U': '101 101 101 101 111', 'V': '101 101 101 101 010', 'W': '10001 10001 10101 11011 10001', 'X': '101 101 010 101 101',
    'Y': '101 101 010 010 010', 'Z': '111 001 010 100 111',
    '0': '111 101 101 101 111', '1': '010 110 010 010 111', '2': '110 001 010 100 111', '3': '110 001 010 001 110',
    '4': '101 101 111 001 001', '5': '111 100 110 001 110', '6': '011 100 111 101 111', '7': '111 001 010 010 010',
    '8': '111 101 111 101 111', '9': '111 101 111 001 110',
    '.': '000 000 000 000 010', ',': '000 000 000 010 100', ':': '000 010 000 010 000', '-': '000 000 111 000 000',
    '/': '001 001 010 100 100', '+': '000 010 111 010 000', '&': '010 101 010 101 011', '?': '110 001 010 000 010',
    "'": '010 010 000 000 000', '(': '001 010 010 010 001', ')': '100 010 010 010 100',
    # Added for this profile, same grid.
    '·': '0 0 1 0 0', '!': '1 1 1 0 1', '↗': '0111 0011 0101 1000 0000', '@': '0110 1001 1011 1000 0111',
    '%': '101 001 010 100 101',
}.items()}

FONT_7X9 = {k: v.split() for k, v in {
    '0': '0011100 0100010 1000001 1001001 1010001 1100001 1000001 0100010 0011100',
    '1': '0001000 0011000 0101000 0001000 0001000 0001000 0001000 0001000 0111110',
    '2': '0011100 0100010 1000001 0000001 0000010 0001100 0010000 0100000 1111111',
    '3': '0111100 1000010 0000001 0000010 0001100 0000010 0000001 1000010 0111100',
    '4': '0000110 0001010 0010010 0100010 1000010 1111111 0000010 0000010 0000010',
    '5': '1111111 1000000 1000000 1111100 0000010 0000001 1000001 0100010 0011100',
    '6': '0011100 0100000 1000000 1111100 1000010 1000001 1000001 0100010 0011100',
    '7': '1111111 0000001 0000010 0000100 0001000 0010000 0010000 0010000 0010000',
    '8': '0011100 0100010 1000001 0100010 0011100 0100010 1000001 0100010 0011100',
    '9': '0011100 0100010 1000001 1000001 0100011 0011111 0000001 0000010 0011100',
    # Added for this profile, same grid.
    ':': '000 000 010 010 000 010 010 000 000', '-': '0000000 0000000 0000000 0000000 1111111 0000000 0000000 0000000 0000000',
}.items()}

FONTS = {'5x7': FONT_5X7, '3x5': FONT_3X5, '7x9': FONT_7X9}

# --- colour: Crypto LED Board palette.ts, plus one accent per project -------------------

BG, OFF = '#030201', '#16110C'
CREAM, MUTED, RULE = '#FFF1D6', '#BDB3A1', '#3A3128'   # RULE is decoration only, never text
CADRAN, LIFT, BOARD, PET = '#FF7B00', '#7FA6FF', '#FF6A00', '#FF8FB0'  # Cadran: cadranapp.com's --color-accent
GREEN, RED = '#089981', '#F23645'
INK = set()  # every colour used for text, checked against WCAG AA at the end


def luminance(hex_):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return .2126 * lin(r) + .7152 * lin(g) + .0722 * lin(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + .05) / (lb + .05)


def hexc(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(v))) for v in rgb)


def rgb(hex_):
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def num(v):
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


# --- drawing on the grid ----------------------------------------------------------------

def text_width(s, font='5x7', scale=1, track=None):
    glyphs, track = FONTS[font], scale if track is None else track
    s = s.upper()
    return sum(len(glyphs.get(ch, glyphs.get('?', glyphs['0']))[0]) * scale for ch in s) + (len(s) - 1) * track


def text(s, col, row, color, font='5x7', scale=1, track=None, anchor='start', decor=False):
    """Cells lit by `s`. `anchor='end'` puts the last lit column at col - 1. `decor` skips the contrast check."""
    glyphs, track = FONTS[font], scale if track is None else track
    s = s.upper()
    if anchor == 'end':
        col -= text_width(s, font, scale, track)
    if not decor:
        INK.add(color)
    cells = {}
    for ch in s:
        g = glyphs.get(ch, glyphs.get('?', glyphs['0']))
        for r, bits in enumerate(g):
            for c, b in enumerate(bits):
                if b == '1':
                    for i in range(scale):
                        for j in range(scale):
                            cells[(col + c * scale + i, row + r * scale + j)] = color
        col += len(g[0]) * scale + track
    return cells


def sprite(rows, palette, col=0, row=0, scale=1):
    """Pixel art from strings; '.' is transparent."""
    cells = {}
    for r, line in enumerate(rows):
        for c, k in enumerate(line):
            if k != '.':
                for i in range(scale):
                    for j in range(scale):
                        cells[(col + c * scale + i, row + r * scale + j)] = palette[k]
    return cells


def hline(c0, c1, row, color):
    return {(c, row): color for c in range(c0, c1 + 1)}


def frame(c0, r0, c1, r1, color):
    cells = hline(c0, c1, r0, color) | hline(c0, c1, r1, color)
    return cells | {(c, r): color for r in range(r0, r1 + 1) for c in (c0, c1)}


def line(a, b, color):
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err, out = dx + dy, {}
    while True:
        out[(x0, y0)] = color
        if (x0, y0) == (x1, y1):
            return out
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def raster(w, h, paint, col=0, row=0, step=8):
    """Vector art sampled once per LED, so edges stay crisp: paint(x, y) in 0..1 returns an RGB tuple or None (dark)."""
    cells = {}
    for r in range(h):
        for c in range(w):
            v = paint((c + .5) / w, (r + .5) / h)
            if v:
                cells[(col + c, row + r)] = hexc([round(a / step) * step for a in v])  # coarse steps keep the colour count small
    return cells


def rounded(x, y, rad):
    """Inside a unit square with rounded corners."""
    dx, dy = max(rad - x, 0, x - (1 - rad)), max(rad - y, 0, y - (1 - rad))
    return dx * dx + dy * dy <= rad * rad


def polar(center, r, deg):
    a = math.radians(deg)
    return round(center[0] + r * math.sin(a)), round(center[1] - r * math.cos(a))


# The LEDs' glow is a blur over the lit dots. WebKit (Safari, and the GitHub app's web view) works SVG filters out on a
# low-resolution buffer, which turns a phone-sized panel to mush whatever the blur's radius. Media queries inside an
# <img>'s SVG see the size it is shown at, so below SHARP_BELOW of its natural width an image drops the glow and lights
# larger dots instead; each image switches by its own scale, so slices and full bands stay alike.
SHARP_BELOW = .6


@functools.lru_cache(maxsize=16)
def card_edge(p, x, width, height, corner):
    """Panel.edge for one card size, cached: it depends on the geometry alone. Each row of the card is one
    span of cells, so a cell is on the ring when it ends its span or the row above or below doesn't cover
    it: worked out row by row, since a cold instance on Vercel pays for it on its first view."""
    m = round(x / p)
    gw, gh = round(width / p), round(height / p)
    cuts = [corner[min(gy, gh - 1 - gy)] if min(gy, gh - 1 - gy) < len(corner) else 0 for gy in range(gh)]
    shape = ''.join(f'M{num(c * p)} {num(gy * p)}h{num((gw - 2 * c) * p)}v{num(p)}h{num(-(gw - 2 * c) * p)}Z'
                    for gy, c in enumerate(cuts))
    ring = {}
    for gy, c in enumerate(cuts):
        up, down = (cuts[gy - 1] if gy else gw), (cuts[gy + 1] if gy < gh - 1 else gw)  # gw: no row there
        for gx in range(c, gw - c):
            if gx in (c, gw - c - 1) or not (up <= gx < gw - up and down <= gx < gw - down):
                ring[(gx - m, gy - m)] = RULE
    return shape, ring


class Panel:
    CORNER = [4, 2, 1, 1]  # LEDs cut from the first rows at each corner of a card: a pixel-art rounding

    def __init__(self, cols, rows, width=882, pitch=3):
        self.p, self.cols, self.rows, self.width = pitch, cols, rows, width
        self.x = self.y = (width - cols * pitch) / 2
        self.height = rows * pitch + 2 * self.y

    def at_row(self, row):
        """The same panel with its row 0 moved down to `row`: a band draws in its own coordinates."""
        band = copy.copy(self)
        band.y += row * self.p
        return band

    def px(self, n):
        return num(n * self.p)

    def box(self, col, row, cols, rows):
        return (f'x="{num(self.x + col * self.p)}" y="{num(self.y + row * self.p)}" '
                f'width="{self.px(cols)}" height="{self.px(rows)}"')

    def runs(self, cells):
        cells, out, i = sorted(cells, key=lambda c: (c[1], c[0])), '', 0
        while i < len(cells):
            c, r = cells[i]
            j = i
            while j + 1 < len(cells) and cells[j + 1] == (cells[j][0] + 1, r):
                j += 1
            n = (j - i + 1) * self.p
            out += f'M{num(self.x + c * self.p)} {num(self.y + r * self.p)}h{num(n)}v{num(self.p)}h{num(-n)}Z'
            i = j + 1
        return out

    def draw(self, cells):
        by = {}
        for cell, color in cells.items():
            by.setdefault(color, []).append(cell)
        return ''.join(f'<path fill="{c}" d="{self.runs(v)}"/>' for c, v in sorted(by.items()))

    def edge(self):
        """The card's outline on the LED grid, which also covers the margin: its stepped shape as a path,
        and the ring of LEDs along it in panel coordinates."""
        return card_edge(self.p, self.x, self.width, self.height, tuple(self.CORNER))

    def svg(self, title, body, style='', defs='', view=None):
        """`view=(x, y, width, height)` crops the panel, see `slices`."""
        p = self.p
        vx, vy, vw, vh = view or (0, 0, self.width, self.height)
        area, card = self.box(0, 0, self.cols, self.rows), f'width="{self.width}" height="{num(self.height)}"'
        shape, ring = self.edge()

        def dots(pid, share, fill):  # one LED per pitch, `share` of it lit
            d = p * share
            return (f'<pattern id="{pid}" width="{num(p)}" height="{num(p)}" patternUnits="userSpaceOnUse" x="{num(self.x)}" y="{num(self.y)}">'
                    f'<rect x="{num((p - d) / 2)}" y="{num((p - d) / 2)}" width="{num(d)}" height="{num(d)}" rx="{num(d * .3)}" fill="{fill}"/></pattern>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{num(vx)} {num(vy)} {num(vw)} {num(vh)}" '
                f'width="{num(vw)}" height="{num(vh)}" role="img" aria-label="{title}"><title>{title}</title>'
                f'<defs>{dots("dot", .72, "#fff")}{dots("off", .72, OFF)}{dots("dot-m", .86, "#fff")}'
                f'<mask id="leds" maskUnits="userSpaceOnUse" x="0" y="0" {card}><rect {card} fill="url(#dot)"/></mask>'
                f'<mask id="leds-m" maskUnits="userSpaceOnUse" x="0" y="0" {card}><rect {card} fill="url(#dot-m)"/></mask>'
                f'<clipPath id="screen"><rect {area}/></clipPath>'
                f'<filter id="bloom" x="-3%" y="-3%" width="106%" height="106%"><feGaussianBlur stdDeviation="{num(p * .6)}" result="b"/>'
                f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>{defs}</defs><style>{style}'
                f'@media (max-width:{num(vw * SHARP_BELOW)}px){{.lit{{filter:none}}.dots{{mask:url(#leds-m)}}}}'
                f'@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>'
                f'<path d="{shape}" fill="#0B0907"/><rect {area} fill="{BG}"/><rect {area} fill="url(#off)"/>'
                f'<g class="lit" filter="url(#bloom)"><g class="dots" mask="url(#leds)">{self.draw(ring)}</g>'
                f'<g class="dots" mask="url(#leds)" clip-path="url(#screen)">{body}</g></g></svg>')


def slices(pn, titles, body, style='', defs='', top=None, bottom=None, indices=None):
    """One panel as one image per title, side by side, one link each; `top` and `bottom` (LED rows) keep
    a band of it. README.md sets the images edge to edge with no whitespace (and `align="top"` between
    bands), so they read as one; every cut has to fall between two LEDs."""
    w = pn.width / len(titles)
    assert all((i * w - pn.x) % pn.p == 0 for i in range(1, len(titles))), 'a cut splits an LED'
    y0 = 0 if top is None else pn.y + top * pn.p
    y1 = pn.height if bottom is None else pn.y + bottom * pn.p
    indices = range(len(titles)) if indices is None else indices
    return [pn.svg(titles[i], body, style, defs, view=(i * w, y0, w, y1 - y0)) for i in indices]


def columns(pn, cuts, titles, body, style='', defs='', top=None, bottom=None):
    """A band of a card as images side by side, cut between LED columns (`cuts`; 0 sets the left margin
    apart). A live band puts only its live column on api/ and the rest in the repo: README.md sets the
    pieces on one line, so the static ones arrive with the page, already show the card and hold its height,
    and only the live column fills in, in a slot that is already there."""
    y0 = 0 if top is None else pn.y + top * pn.p
    y1 = pn.height if bottom is None else pn.y + bottom * pn.p
    xs = [0, *(pn.x + c * pn.p for c in cuts), pn.width]
    return [pn.svg(t, body, style, defs, view=(a, y0, b - a, y1 - y0)) for t, a, b in zip(titles, xs, xs[1:])]


HERO_LIVE = (146, 239)  # the counter's columns in the hero's top band: all that depends on the visitor
HERO_BAND = 25  # the top band ends above the photo's light
DEVICE_LIVE = (216,)  # project bands: the device, its live clock and the card's right edge; the copy stays static
# Every piece of a line has to be wide for its height: Chrome rounds widths to 1/64 px and a piece's height is its width
# times its height-to-width ratio, so a tall, narrow strip ends up a pixel row off from its neighbours.


SLOTS = [(6, 86), (99, 184), (197, 280)]  # one link per third of a 284-LED panel, 6 LEDs clear of the cuts


def write(name, out):
    """One SVG, or the slices from `slices` as name-1.svg, name-2.svg..."""
    for i, svg in enumerate([out] if isinstance(out, str) else out):
        (IMG / (f'{name}.svg' if isinstance(out, str) else f'{name}-{i + 1}.svg')).write_text(svg)


# --- motion (CSS only) ----------------------------------------------------------------

def scroll(name, length, cols_per_s, panel):
    return (f'.{name}{{animation:{name} {num(length / cols_per_s)}s steps({length}) infinite}}'
            f'@keyframes {name}{{to{{transform:translateX(-{panel.px(length)}px)}}}}')


def ticker(segments, row, gap=6):
    """Segments (text, colour[, icon key]) end to end, drawn twice so scrolling one length loops without a seam."""
    cells, col = {}, 0
    for s, color, *icon in segments:
        if icon:
            rows, palette = STACK_ICONS[icon[0]]
            cells |= sprite(rows, palette, col, row)
            col += len(rows[0]) + 3
        cells |= text(s, col, row, color, decor=s in '◆·')  # separators are ornament
        col += text_width(s) + gap
    return cells | {(c + col, r): v for (c, r), v in cells.items()}, col


# --- pixel art --------------------------------------------------------------------------

@functools.cache
def art_data():
    """art.json, read once per process: titles, glyphs and pixel art are looked up on every render."""
    return json.loads((OUT / 'art.json').read_text())


def art(name, col, row, radius=.2):
    """Imported pixel art (art.json) with rounded corners."""
    a = art_data()[name]
    w, h = a['w'], a['h']
    return {(col + c, row + r): a['palette'][int(k, 36)]
            for r, line_ in enumerate(a['rows']) for c, k in enumerate(line_)
            if rounded((c + .5) / w, (r + .5) / h, radius)}


def seg_dist(x, y, deg, length):
    a = math.radians(deg)
    ex, ey = length * math.sin(a), -length * math.cos(a)
    t = max(0, min(1, (x * ex + y * ey) / (ex * ex + ey * ey)))
    return math.hypot(x - t * ex, y - t * ey)


def arc_dist(dx, dy, radius, a0, a1):
    """Distance to a round-capped arc, angles clockwise from 12 o'clock."""
    ang = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
    if a0 <= ang <= a1 if a0 < a1 else (ang >= a0 or ang <= a1):
        return abs(math.hypot(dx, dy) - radius)
    return min(math.hypot(dx - radius * math.sin(math.radians(a)), dy + radius * math.cos(math.radians(a))) for a in (a0, a1))


def cadran_face(x, y, ring=(255, 246, 236), smile=(246, 166, 64), stroke=.027):
    """Cadran's mark, measured on the 256 px app icon: a ring open at the bottom, hands at 10:09,
    and a smile about twice the ring's weight sitting in the ring's gap. The icon's gap is 124-236°;
    it is opened a little here so a clear LED stays between the ring and the smile. Returns a colour or None."""
    dx, dy = x - .498, y - .483
    if arc_dist(dx, dy, .316, 134, 226) < stroke * 2.2:
        return smile
    if (arc_dist(dx, dy, .3045, 244, 116) < stroke
            or seg_dist(dx, dy, 301, .112) < stroke or seg_dist(dx, dy, 56.5, .204) < stroke):
        return ring
    return None


def cadran_icon(col, row, size=24):
    magenta, coral = (182, 61, 96), (226, 82, 42)  # the icon's left and right edges

    def paint(x, y):
        if not rounded(x, y, .22):
            return None
        return cadran_face(x, y) or mix(magenta, coral, x + (.5 - y) * .1)
    return raster(size, size, paint, col, row)


def outline(col, row, size, color, radius=.22):
    """One-LED contour hugging a rounded tile (an icon, the photo), lit from above."""
    def inside(c, r):
        return 0 <= c < size and 0 <= r < size and rounded((c + .5) / size, (r + .5) / size, radius)
    top, bottom = mix(rgb(color), (255, 255, 255), .45), mix(rgb(color), rgb(BG), .5)
    return {(col + c, row + r): hexc(mix(top, bottom, (r + 1) / (size + 1)))
            for r in range(-1, size + 1) for c in range(-1, size + 1)
            if not inside(c, r) and any(inside(c + i, r + j) for i in (-1, 0, 1) for j in (-1, 0, 1))}


# --- titles: pre-rendered by `build.py titles` so CI needs neither Pillow nor the font ----

TITLE_CAPS = {'MY PROJECTS': 8}  # section headings sit a size below the names (cap height 14)
TITLES = ['ILYES ABD-LILLAH', 'CADRAN', 'LIFT', 'LED BOARD', 'BYTE', 'PIXEL', 'NIBBLE', 'HEX', 'SUDO', 'PING', 'MY PROJECTS', 'GITHUB']


def big(s, col, row, color, gap=2, size='counter'):
    """Pre-rendered digits at one LED per pixel, like the titles: the counter's by default. `row` is the top."""
    glyphs = art_data()[size]
    INK.add(color)
    cells = {}
    for ch in s:
        g = glyphs[ch]
        cells |= {(col + c, row + r): color for r, line_ in enumerate(g) for c, k in enumerate(line_) if k == '1'}
        col += len(g[0]) + gap
    return cells


def title_width(s):
    return art_data()['titles'][s]['w']


def title(s, col, row, color, decor=False):
    """Title in JetBrains Mono at one LED per pixel. `row` is the cap top."""
    t = art_data()['titles'][s]
    if not decor:
        INK.add(color)
    return {(col + c, row - t['top'] + r): hexc(mix(rgb(BG), rgb(color), int(k) / t['levels']))
            for r, line_ in enumerate(t['rows']) for c, k in enumerate(line_) if k != '0'}


def tile_dist(c, r, w, h, rad):
    """LEDs from cell (c, r)'s centre to the edge of a w x h tile with corner radius `rad`, negative inside."""
    qx, qy = abs(c + .5 - w / 2) - (w / 2 - rad), abs(r + .5 - h / 2) - (h / 2 - rad)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - rad


def halo(col, row, w, h, color, reach=4, rad=None, power=.3, start=1):
    """Light around a tile, as LEDs that dim in steps away from it from `start` LEDs out: no blur,
    every LED one flat colour. Corners default to the icons' rounding."""
    rad = .22 * min(w, h) if rad is None else rad
    return {(col + c, row + r): hexc(mix(rgb(BG), rgb(color), power * (1 - (math.ceil(d) - start - 1) / reach)))
            for r in range(-start - reach, h + start + reach) for c in range(-start - reach, w + start + reach)
            if start < (d := tile_dist(c, r, w, h, rad)) <= start + reach}


@functools.lru_cache(maxsize=16)  # the same few cases on every view: the pet card's screen, the counter's housing
def bezel(col, row, w, h, color):
    """The case around a w x h screen at (col, row): a two-LED rim lit from above with a dim inner lip,
    a faint backlight on the screen and a soft halo outside. Whatever the screen shows is drawn over it."""
    top, bottom = mix(rgb(color), (255, 255, 255), .35), mix(rgb(color), rgb(BG), .55)
    cells = halo(col, row, w, h, color, reach=3, rad=0, power=.14, start=2)
    cells |= {(col + c, row + r): hexc(mix(rgb(BG), rgb(color), .05)) for r in range(h) for c in range(w)}
    for r in range(-2, h + 2):
        for c in range(-2, w + 2):
            d = tile_dist(c, r, w, h, 0)
            if 0 < d <= 1:
                cells[(col + c, row + r)] = hexc(mix(rgb(BG), rgb(color), .22))
            elif 1 < d <= 2:
                cells[(col + c, row + r)] = hexc(mix(top, bottom, (r + 2) / (h + 3)))
    return cells


def board_icon(col, row, size=24):
    """Crypto LED Board's icon: its 9x9 pixel chart, one icon pixel = 2x2 LEDs."""
    pix = [(0, 7), (1, 6), (2, 5), (3, 5), (4, 6), (5, 5), (5, 4), (6, 3), (7, 2), (8, 1), (6, 1), (7, 1), (8, 2), (8, 3)]
    cells = {(col + c, row + r): '#1C120A' for r in range(size) for c in range(size)
             if rounded((c + .5) / size, (r + .5) / size, .22)}
    for px_, py in pix:
        for i in range(2):
            for j in range(2):
                cells[(col + 3 + px_ * 2 + i, row + 3 + py * 2 + j)] = BOARD
    return cells


# The profile pets, drawn on a 26x24 grid (each part as its first row and its rows), doubled with scale2x and lit
# at LED size (see `lit`), so their shading and outline are one LED fine. G fur, S its markings, W cream, D dark
# fur, P inner ear, R collar or scarf, Y bell, tag or feet; K, H, N and C draw the eyes, nose and cheeks of the
# switch's small heads only. A lowercase key is its colour on the face, which moves on its own when the pet
# looks around: those keys, the cheeks, `eyes` (the left eye's corner and size at LED size, the right one
# mirrors it about column 22) and `mouth` (its corner and sprites at LED size). `marks` are fur markings on the
# head at LED size. `ears` sit behind the head unless `front_ears`; `twitch` (row, dx, dy) moves the right ear's
# rows above `row` for a flick. `tail` and `flippers` are chains (see `chain`) swung by `wag`, see `swing`. `cut`
# is the LED row the body bends at to breathe, crouch and stretch; `tile` how many grid rows the switch shows.
PETS = {
    'cat': {'name': 'BYTE', 'noun': 'CAT', 'food': 'fish', 'tile': 15, 'accent': '#F0A04B', 'cut': 36,
        'colors': {'G': '#F0A04B', 'S': '#C8692A', 'W': '#FFF1D6', 'P': '#F58BA0', 'K': '#1A0F0A', 'H': '#FFFFFF', 'N': '#FF8FA8',
                   'C': '#FF9DB4', 'R': '#F23645', 'Y': '#FFD866', 'E': '#5FD068', 'T': '#FF7A9A', 'M': '#6A2E1A'},
        'ears': (1, ['...G..............G',
                     '...GG............GG',
                     '...GPG..........GPG',
                     '..GGPPG........GPPGG',
                     '..GGPPGG......GGPPGG',
                     '..GGGGGG......GGGGGG']),
        'twitch': (4, 1, 0),
        'head': (5, ['.....GGGGGGGGGGGG',
                     '...GGGGGGGGGGGGGGGG',
                     '..GGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGHKGGGGGGGGGGHKGGG',
                     'GGGGKKGGGGGGGGGGKKGGGG',
                     'GGGCCGGGGGNNGGGGGCCGGG',
                     '.GGGGGGGwwwwwwGGGGGGG',
                     '..GGGGGGGwwwwGGGGGGG',
                     '....GGGGGGGGGGGGGG']),
        'body': (13, ['.....GGGGGGGGGGGG',
                      '....GGGGGGGGGGGGGG',
                      '....RRRRRRYYRRRRRR',
                      '...GGGGWWWYYWWWGGGG',
                      '...GGGGWWWWWWWWGGGG',
                      '..GGGGGWWWWWWWWGGGGG',
                      '..GSSGGGWWWWWWGGGSSG',
                      '..SGGSGGGWGGWGGGSGGS',
                      '..SGGSGWWWGGWWWGSGGS',
                      '..GGGGGWWW..WWWGGGGG']),
        'eyes': (7, 16, (6, 7)),
        'marks': (17, 11, ['.S...SS...S', '.S...SS...S', 'S....SS....S', '.....SS.....']),
        'mouth': (18, 22, {'shut': ['..nNNN..', '...NN...', '...MM...', '.MM..MM.'],
                           'open': ['..nNNN..', '...NN...', '..MMMM..', '..MTTM..', '...MM...'],
                           'lick': ['..nNNN..', '...NN...', '...MM...', '.MMTTMM.', '...TT...']}),
        'tail': {'root': (37, 41), 'angle': 80, 'segs': 10, 'length': 2.6, 'widths': (3.4, 2.6), 'curl': -10, 'swing': 16,
                 'lag': .55, 'stripes': 3.5},
        'wag': [(.14, 1, 1)]},
    'dog': {'name': 'PIXEL', 'noun': 'DOG', 'food': 'bone', 'tile': 14, 'accent': '#E3B47A', 'cut': 36,
        'colors': {'G': '#E3B47A', 'S': '#9C5F2E', 'W': '#FFF1D6', 'K': '#1A0F0A', 'H': '#FFFFFF', 'N': '#3A2418', 'C': '#FF9DB4',
                   'R': '#4C8DFF', 'Y': '#FFD866', 'E': '#9A6A3A', 'T': '#FF7A9A', 'M': '#4A2A14'},
        'ears': (3, ['..SSS............SSS',
                     '.SSSSS..........SSSSS',
                     'SSSSSS..........SSSSSS',
                     'SSSSS............SSSSS',
                     'SSSSS............SSSSS',
                     'SSSSS............SSSSS',
                     'SSSS..............SSSS',
                     '.SS................SS']),
        'front_ears': True, 'twitch': (11, 0, -1),
        'head': (2, ['....GGGGGGGGGGGGGG',
                     '..GGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGGHKGGGGGGGGHKGGGG',
                     '.GGGGKKGGGGGGGGKKGGGG',
                     '.GGCCGGGwwwwwwGGGCCGG',
                     '..GGGGGwwwNNwwwGGGGG',
                     '..GGGGGwwwwwwwwGGGGG',
                     '...GGGGGwwwwwwGGGGG',
                     '....GGGGGGGGGGGGGG']),
        'body': (13, ['.....GGGGGGGGGGGG',
                      '....GGGGGGGGGGGGGG',
                      '....RRRRRRYYRRRRRR',
                      '...GGGGWWWYYWWWGGGG',
                      '...GGGGWWWWWWWWGGGG',
                      '..SSSGGWWWWWWWWGGGGG',
                      '..SSSSGGWWWWWWGGGGGG',
                      '..GSSGGGGWGGWGGGGGGG',
                      '..GGGGGWWWGGWWWGGGGG',
                      '..GGGGGWWW..WWWGGGGG']),
        'eyes': (10, 14, (5, 6)),
        'mouth': (18, 20, {'shut': ['.nNNNNN.', '.NNNNNN.', '..NNNN..', '...MM...', '.MM..MM.'],
                           'open': ['.nNNNNN.', '.NNNNNN.', '..NNNN..', '...MM...', '.MMMMMM.', '.MTTTTM.', '..MTTM..'],
                           'lick': ['.nNNNNN.', '.NNNNNN.', '..NNNN..', '...MM...', '.MMTTMM.', '...TT...', '...TT...']}),
        'tail': {'root': (37, 38), 'angle': 45, 'segs': 5, 'length': 2.3, 'widths': (3.8, 2.6), 'curl': -12, 'swing': 34, 'lag': .4},
        'wag': [(.05, .02, 4), (.12, .45, 1), (0, 1.2, 0)]},
    'bunny': {'name': 'NIBBLE', 'noun': 'BUNNY', 'food': 'carrot', 'tile': 15, 'accent': '#FF8FB0', 'cut': 38,
        'colors': {'G': '#ECE8F4', 'S': '#C9C0DA', 'W': '#FFFFFF', 'P': '#FF9DB4', 'K': '#2A1A2E', 'H': '#FFFFFF', 'N': '#FF7A9A',
                   'C': '#FF9DB4', 'E': '#C24A6A', 'T': '#FF7A9A', 'M': '#8A6A8A'},
        'ears': (0, ['...GG............GG',
                     '..GPPG..........GPPG',
                     '..GPPG..........GPPG',
                     '..GPPG..........GPPG',
                     '..GPPG..........GPPG',
                     '..GPPG..........GPPG',
                     '...GPG..........GPG',
                     '...GGG..........GGG']),
        'twitch': (4, 1, 0),
        'head': (6, ['.....GGGGGGGGGGGG',
                     '...GGGGGGGGGGGGGGGG',
                     '..GGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGHKGGGGGGGGGGHKGGG',
                     '.GGGKKGGGGGGGGGGKKGGG',
                     '.GGCCGGGGGNNGGGGGCCGG',
                     '..GGGGGGwwwwwwGGGGGG',
                     '...GGGGGGwwwwGGGGGG',
                     '.....GGGGGGGGGGGG']),
        'body': (15, ['.....GGGGGGGGGGGG',
                      '....GGGGGGGGGGGGGG',
                      '...GGGGWWWWWWWWGGGG',
                      '..GGGGWWWWWWWWWWGGGG',
                      '..GGGGWWWWWWWWWWGGGG',
                      '..GSGGGWWWWWWWWGGGSG',
                      '.GGSGGGWWWGGWWWGGGSGG',
                      '.WWWGGGWWW..WWWGGGWWW']),
        'eyes': (7, 19, (6, 7)),
        'mouth': (19, 24, {'shut': ['.nNNN.', '..NN..', '..MM..', '.M..M.'],
                           'sniff': ['.nNNN.', '.NNNN.', '..MM..', '.M..M.'],
                           'open': ['.nNNN.', '..NN..', '..MM..', '.MWWM.', '..WW..'],
                           'lick': ['.nNNN.', '..NN..', '..MM..', '.MTTM.', '..TT..']}),
        'tail': {'root': (39, 41), 'angle': 90, 'segs': 2, 'length': 1.5, 'widths': (7, 7), 'key': 'W', 'swing': 25},
        'wag': [(.08, 0, 2), (0, 2.5, 0)]},
    'fox': {'name': 'HEX', 'noun': 'FOX', 'food': 'bone', 'tile': 15, 'accent': '#FF7A1F', 'cut': 36,
        'colors': {'G': '#FF7A1F', 'S': '#C2500F', 'W': '#FFF1D6', 'D': '#4A2414', 'P': '#FFC9A0', 'K': '#1A0F0A', 'H': '#FFFFFF',
                   'N': '#2A1A12', 'C': '#FF9DB4', 'E': '#FFC94A', 'T': '#FF7A9A', 'M': '#4A1E0A'},
        'ears': (0, ['.DD................DD',
                     '.DDD..............DDD',
                     '.GDDG............GDDG',
                     '.GGPGG..........GGPGG',
                     '.GGPPGG........GGPPGG',
                     '.GGPPGGG......GGGPPGG',
                     '.GGGGGG........GGGGGG']),
        'twitch': (4, 1, 0),
        'head': (5, ['....GGGGGGGGGGGGGG',
                     '..GGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     '.GGGHKGGGGGGGGGGHKGGG',
                     'WGGGKKGGGGGGGGGGKKGGGW',
                     'WWWGGGGGGwNNwGGGGGGWWW',
                     '.WWWWWWwwwwwwwwWWWWWW',
                     '..WWWWWWwwwwwwWWWWWW',
                     '....WWWWWWWWWWWWWW']),
        'body': (14, ['....GGGGGGGGGGGGGG',
                      '....GGGGWWWWWWGGGG',
                      '...GGGGWWWWWWWWGGGG',
                      '...GGGGWWWWWWWWGGGG',
                      '..GGGGGWWWWWWWWGGGGG',
                      '..GGGGGGWWWWWWGGGGGG',
                      '..GGGGGGGWGGWGGGGGGG',
                      '..GGGGDDGGGGGGDDGGGG',
                      '..GGGGDDD....DDDGGGG']),
        'eyes': (7, 17, (6, 7)),
        'mouth': (19, 22, {'shut': ['.nNNN.', '.NNNN.', '..NN..', '..MM..', 'MM..MM'],
                           'open': ['.nNNN.', '.NNNN.', '..NN..', '.MMMM.', '.MTTM.', '..MM..'],
                           'lick': ['.nNNN.', '.NNNN.', '..NN..', '..MM..', 'MMTTMM', '..TT..']}),
        'tail': {'root': (38, 42), 'angle': 75, 'segs': 7, 'length': 3, 'widths': (5, 9, 5), 'tip': .3, 'curl': -12, 'swing': 12,
                 'lag': .5},
        'wag': [(.16, .8, 1)]},
    'penguin': {'name': 'SUDO', 'noun': 'PENGUIN', 'food': 'fish', 'tile': 14, 'accent': '#8FB2FF', 'cut': 36,
        'colors': {'G': '#4A5578', 'S': '#323A58', 'W': '#F4F6FF', 'Y': '#FFB02E', 'B': '#D98A1E', 'R': '#F23645', 'K': '#141624',
                   'H': '#FFFFFF', 'N': '#FFB02E', 'C': '#FF9DB4', 'E': '#6A80C0', 'T': '#FF7A9A', 'M': '#7A4A10'},
        'head': (1, ['......GGGGGGGGGG',
                     '....GGGGGGGGGGGGGG',
                     '...GGGGGGGGGGGGGGGG',
                     '..GGGGGGGGGGGGGGGGGG',
                     '..GGGWWWGGGGGGWWWGGG',
                     '..GGWWWWWGWWGWWWWWGG',
                     '..GWWHKWWWWWWWWHKWWG',
                     '..GWWKKWWWWWWWWKKWWG',
                     '..GWCCWWWNNNNWWWCCWG',
                     '..GGWWWWWWNNWWWWWWGG',
                     '...GGWWWWWWWWWWWWGG',
                     '....GGGGGGGGGGGGGG']),
        'body': (12, ['....GGGGGGGGGGGGGG',
                      '...GRRRRRRRRRRRRRRG',
                      '..GGRRRRRRRRRRRRRRGG',
                      '.GGGWWWWWWWWWWRRWWGGG',
                      '.GGWWWWWWWWWWWWRRWWGG',
                      '.GGWWWWWWWWWWWWRWWWGG',
                      '.GGWWWWWWWWWWWWWWWWGG',
                      '..GWWWWWWWWWWWWWWWWG',
                      '..GGWWWWWWWWWWWWWWGG',
                      '...GGWWWWWWWWWWWWGG',
                      '....YYY........YYY']),
        'eyes': (10, 14, (5, 6)),
        'mouth': (18, 18, {'shut': ['..nYYY..', '.YYYYYY.', '..BBBB..', '...BB...'],
                           'open': ['..nYYY..', '.YYYYYY.', '.MMMMMM.', '..BBBB..', '...BB...'],
                           'lick': ['..nYYY..', '.YYYYYY.', '..BTTB..', '...TT...']}),
        'flippers': {'root': (6, 31), 'angle': 200, 'segs': 4, 'length': 2.6, 'widths': (4.4, 2.6), 'curl': 8, 'swing': 14, 'lag': .3},
        'wag': [(.07, 0, 2), (0, 3.1, 0)]},
    'frog': {'name': 'PING', 'noun': 'FROG', 'food': 'fly', 'tile': 12, 'accent': '#6FD36B', 'cut': 34,
        'colors': {'G': '#6FD36B', 'S': '#3C9A38', 'W': '#E6F5C4', 'K': '#0E1A0A', 'H': '#FFFFFF', 'C': '#FF9DB4', 'E': '#F5D547',
                   'T': '#FF7A9A', 'M': '#1F4A1A', 'N': '#1F4A1A'},
        'head': (1, ['..GGGG..........GGGG',
                     '.GKHKG..........GKHKG',
                     '.GKKKG..........GKKKG',
                     '.GGGGGGGGGGGGGGGGGGGG',
                     'GGGGGGGGGGGGGGGGGGGGGG',
                     'GGGGGGGGGGGGGGGGGGGGGG',
                     'GGCCGGGGGGGGGGGGGGCCGG',
                     'GGGGGGGGGGGGGGGGGGGGGG',
                     '.GGGGGGGGGGGGGGGGGGGG']),
        'body': (9, ['..GGGGGGGGGGGGGGGGGG',
                     '..GGGGGGGGGGGGGGGGGG',
                     '.GGGGGGWWWWWWWWGGGGGG',
                     '.GGGGGWWWWWWWWWWGGGGG',
                     'GGGGGWWWWWWWWWWWWGGGGG',
                     'GSGGGWWWWWWWWWWWWGGGSG',
                     'GGGSGGWWWWWWWWWWGGSGGG',
                     'GGGGGGGWWWWWWWWGGGGGGG',
                     'GSGGGSGGWWWWWWGGSGGGSG',
                     'GGGGGSGGGWWWWGGGSGGGGG',
                     'GGGGGGSGGGGGGGGSGGGGGG',
                     '.GGGGGS.GGGGGG.SGGGGG',
                     'GGGGGG..GGGGGG..GGGGGG',
                     'G.G.G...G.GG.G...G.G.G']),
        'eyes': (5, 3, (6, 6)), 'look': 1,
        'mouth': (14, 14, {'shut': ['...N........N...'],
                           'open': ['...N........N...', '................', '..MMMMMMMMMMMM..', '.MMTTTTTTTTTTMM.', '..MMMMMMMMMMMM..'],
                           'lick': ['...N........N...', '................', '................', '......TTTT......', '.......TT.......']}),
        'throat': (22, 20)},
}


def grid(first, rows):
    """{(col, row): key} of sprite rows that start at grid row `first`; '.' is empty."""
    return {(c, first + r): k for r, ln in enumerate(rows) for c, k in enumerate(ln) if k != '.'}


def scale2x(rows):
    """Scale2x (AdvMAME2x): doubles pixel art one LED per pixel, rounding its diagonals instead of
    drawing 2x2 blocks."""
    h, w = len(rows), len(rows[0])

    def at(r, c):
        return rows[r][c] if 0 <= r < h and 0 <= c < w else '.'
    out = []
    for r in range(h):
        top, bottom = [], []
        for c in range(w):
            p, a, b, l, d = rows[r][c], at(r - 1, c), at(r, c + 1), at(r, c - 1), at(r + 1, c)
            top += [l if l == a and l != d and a != b else p, b if a == b and a != l and b != d else p]
            bottom += [l if d == l and d != b and l != a else p, b if b == d and b != a and d != l else p]
        out += [''.join(top), ''.join(bottom)]
    return out


def doubled(cells, w=26, h=24):
    """A grid sprite ({(col, row): key}) at LED size, through scale2x."""
    rows = [''.join(cells.get((c, r), '.') for c in range(w)) for r in range(h)]
    return {(c, r): k for r, ln in enumerate(scale2x(rows)) for c, k in enumerate(ln) if k != '.'}


def bent(cells, cut, rise, widen=0, mid=22):
    """A body breathing in, crouching or stretching: the rows above `cut` raised `rise` LEDs (lowered when it is
    negative), the rows they leave repeating the row at the cut or those they cover folded away, then `widen`
    LEDs more width (less when negative) taken at column `mid`. The light and outline move with the fur."""
    out = {}
    for (c, r), v in cells.items():
        if r < cut:
            out[(c, r - rise)] = v
        elif not (rise < 0 and r < cut - rise):
            out[(c, r)] = v
            if r == cut and rise > 0:
                out |= {(c, cut - i): v for i in range(1, rise + 1)}
    k, wide = widen // 2, {}
    for (c, r), v in out.items():
        if k >= 0:
            wide[(c - k if c < mid else c + k, r)] = v
            if c in (mid - 1, mid):  # the middle columns, repeated to fill the gap
                wide |= {(c + (i if c == mid else -i), r): v for i in range(k)}
        elif not mid + k <= c < mid - k:
            wide[(c - k if c < mid else c + k, r)] = v
    return wide


def shaded(hex_, light, colour=1., toward=0., most=0.):
    """hex_ at `light` times its lightness, with `colour` times its chroma (kept, not its saturation, so a pale
    colour stays pale as it darkens) and its hue moved up to `most` toward `toward`."""
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb(hex_)))
    chroma = (1 - abs(2 * l - 1)) * s
    l2 = min(1., l * light) if light <= 1 else l + (1 - l) * (light - 1)
    room = 1 - abs(2 * l2 - 1)
    d = (toward - h + .5) % 1 - .5
    h2 = h + max(-most, min(most, d)) * min(1, chroma * 3)  # greys keep their hue
    return hexc(v * 255 for v in colorsys.hls_to_rgb(h2 % 1, l2, min(1, chroma * colour / room) if room else 0))


@functools.lru_cache(maxsize=128)
def ramp(hex_):
    """A colour's four tones on a pet, from deep shadow to light: shadows lean to blue and lights to yellow, as
    paint does."""
    return shaded(hex_, .62, 1.12, .7, .05), shaded(hex_, .8, 1.06, .7, .025), hex_, shaded(hex_, 1.35, .95, .13, .025)


@functools.lru_cache(maxsize=256)
def rim(hex_, lit_side):
    """The outline LED next to a colour: a dark tone of it, a little lighter on the side the light comes from."""
    return shaded(hex_, .42 if lit_side else .3, 1.2)


LIGHT = (-.55, -.835)  # where the pets' light comes from: above, a little to the left
FLAT = 'KH'  # keys drawn as they are: the small heads' eyes and their light


def lit(keys, colors):
    """A sprite at LED size ({(col, row): key}) lit from LIGHT: one LED of light along the edges that face it, a
    shadow two LEDs deep along those that turn away and a darker line where they face fully away, then a one-LED
    outline in a dark tone of the colour inside it. Each LED gets one flat colour: no anti-aliasing."""
    out, ring = {}, {}
    for (c, r), k in keys.items():
        if k in FLAT:
            out[(c, r)] = colors[k]
            continue
        sx = sy = n = 0
        edge = 3
        for dr in (-2, -1, 0, 1, 2):
            for dc in (-2, -1, 0, 1, 2):
                if (c + dc, r + dr) in keys:
                    sx, sy, n = sx + dc, sy + dr, n + 1
                else:
                    edge = min(edge, max(abs(dc), abs(dr)))
        m = math.hypot(sx, sy)
        facing = -(sx * LIGHT[0] + sy * LIGHT[1]) / m if m > n * .05 else 0  # the edge's normal points away from the inside
        tone = 3 if edge <= 1 and facing > .3 else 0 if edge <= 1 and facing < -.55 else 1 if edge <= 2 and facing < -.2 else 2
        out[(c, r)] = ramp(colors[k])[tone]
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (c + dc, r + dr) not in keys and (c + dc, r + dr) not in ring:
                ring[(c + dc, r + dr)] = rim(colors[k], dr < 0 or dc < 0)
    return ring | out


def chain(spec, phase):
    """A tail or flipper as {(col, row): key} at LED size: `segs` segments of `length` from `root`, each turned
    `curl` degrees from the last (0 is up, 90 right) and swung `swing` degrees by a wave that starts at the root
    and reaches the tip later, so the tip follows through. `phase` (0-1) is where the swing is; `widths` run
    from root to tip, `tip` is the share of the length drawn in W and `stripes` the length of each band of S."""
    (x, y), segs, length, widths = spec['root'], spec['segs'], spec['length'], spec['widths']
    keys, total = {}, segs * length
    for i in range(segs):
        a = math.radians(spec['angle'] + spec.get('curl', 0) * i
                         + spec.get('swing', 0) * (.35 + .65 * i / segs) * math.sin(2 * math.pi * phase - spec.get('lag', .6) * i))
        for j in range(8):
            s = (i * length + j * length / 8) / total
            if len(widths) == 2:
                w = widths[0] + (widths[1] - widths[0]) * s
            else:
                w = widths[0] + (widths[1] - widths[0]) * s * 2 if s < .5 else widths[1] + (widths[2] - widths[1]) * (s - .5) * 2
            px_, py_ = x + math.sin(a) * length * j / 8, y - math.cos(a) * length * j / 8
            k = ('W' if s > 1 - spec.get('tip', 0) else
                 'S' if spec.get('stripes') and int(s * total / spec['stripes']) % 2 else spec.get('key', 'G'))
            for r in range(math.floor(py_ - w / 2), math.ceil(py_ + w / 2) + 1):
                for c in range(math.floor(px_ - w / 2), math.ceil(px_ + w / 2) + 1):
                    if (c + .5 - px_) ** 2 + (r + .5 - py_) ** 2 <= w * w / 4:
                        keys[(c, r)] = k
        x, y = x + math.sin(a) * length, y - math.cos(a) * length
    return keys


EYES = {  # at LED size: K pupil, I and J the iris, deep then lit, H the light it catches, W the frog's cream
    (6, 7): ['.KKKK.', 'KHHKKK', 'KHHKKK', 'KKKKKK', 'KIIIIK', 'KIJJHK', '.JJJJ.'],
    (5, 6): ['.KKK.', 'KHHKK', 'KHKKK', 'KIIIK', 'KIJHK', '.JJJ.'],
    (6, 6): ['.WWWW.', 'WHKKWW', 'WKKKKW', 'WKKKKW', 'WWKKWW', '.WWWW.'],
}

HEART = ['.RR.RR.', 'RHRRRRR', 'RRRRRRR', '.RRRRR.', '..RRR..', '...R...']
SPARKLE = ['..C..', '..C..', 'CCWCC', '..C..', '..C..']
FISH = [['..BBB...B', '.BBBBB.BB', 'B.BBBBBBB', '.BBBBB.BB', '..BBB...B'],
        ['....B...B', '...BB.BB.', '..BBBBBBB', '...BB.BB.', '....B...B'],
        ['.........', '.W.W.W..W', 'WWWWWWWWW', '.W.W.W..W', '.........']]
BONE = [['WW.....WW', 'WWWWWWWWW', '.WWWWWWW.', 'WWWWWWWWW', 'WW.....WW'],
        ['WW.......', 'WWWWW....', '.WWWW....', 'WWWWW....', 'WW.......'],
        ['.........', '.........', '.W...W..W', '...W.....', '.........']]
CARROT = [['......L.L', '..CCCCCL.', 'CCCCCCCLL', '..CCCCCL.', '......L.L'],
          ['......L.L', '.....CCL.', '....CCCLL', '.....CCL.', '......L.L'],
          ['......L.L', '.......L.', '.......LL', '.......L.', '......L.L']]
FLY = [['.WW.WW', '..WKW.', '.KKKKK', '..KKK.'], ['......', '.WWKW.', '.KKKKK', '..KKK.']]  # wings up, wings down
FOOD = {'fish': (FISH, {'B': '#7EC8FF', 'W': CREAM}), 'bone': (BONE, {'W': CREAM}),
        'carrot': (CARROT, {'C': '#FF8A2A', 'L': '#7BD88F'}), 'fly': (FLY, {'K': '#8C96A6', 'W': '#DDF0FF'})}  # three bites each
BALL = ['.YYYY.', 'YYRRYY', 'YRRYYY', 'YYYYRY', 'YYYRRY', '.YYYY.']
ICONS = {  # 9x9 button icons
    'globe': ['..CCCCC..', '.C..C..C.', 'C..C.C..C', 'CCCCCCCCC', 'C..C.C..C', 'CCCCCCCCC', 'C..C.C..C', '.C..C..C.', '..CCCCC..'],
    'in': ['CCCCCCCCC', 'C.CCCCCCC', 'CCCCCCCCC', 'C.CC..CCC', 'C.C.CC.CC', 'C.C.CC.CC', 'C.C.CC.CC', 'C.C.CC.CC', 'CCCCCCCCC'],
    'mail': ['.........', 'CCCCCCCCC', 'CC.....CC', 'C.C...C.C', 'C..C.C..C', 'C...C...C', 'C.......C', 'CCCCCCCCC', '.........'],
    # Button icons: 9x7, the label's height, so they sit on the label's row. L is the shine, in a lighter tint.
    'fish': ['..CCC....', '.CCCCC..C', 'CC.CCCCCC', 'CCCCCCCC.', 'CCCCCCCCC', '.CCCCC..C', '..CCC....'],
    'heart': ['.CC...CC.', 'CLCC.CCCC', 'CCCCCCCCC', '.CCCCCCC.', '..CCCCC..', '...CCC...', '....C....'],
    'ball': ['...CCC...', '..LLCCC..', '.CLCCCCC.', '.CCCCCCC.', '.CCCCCCC.', '..CCCCC..', '...CCC...'],
    'bone': ['.C.....C.', 'CCC...CCC', 'CCCCCCCCC', '.CLLLLLC.', 'CCCCCCCCC', 'CCC...CCC', '.C.....C.'],
    'carrot': ['......L.L', '.....CLL.', '....CCCC.', '...CCCC..', '..CCCC...', '.CCC.....', 'CC.......'],
    'bowl': ['.........', '..L.L.L..', '.LLLLLLL.', '.........', 'CCCCCCCCC', 'CCCCCCCCC', '.CCCCCCC.', '..CCCCC..', '.........'],
    'reload': ['..CCC.C', '.C...CC', 'C...CCC', 'C......', 'C.....C', '.C...C.', '..CCC..'],  # 7x7: the click reloads the page
}


# Stack icons for the hero ticker, 7 LEDs tall like the 5x7 text they precede: (rows, palette).
STACK_ICONS = {
    'react': (['.CC...CC.', '.C.C.C.C.', '.CC.C.CC.', 'C..CWC..C', '.CC.C.CC.', '.C.C.C.C.', '.CC...CC.'],
        {'C': '#61DAFB', 'W': '#C8F4FF'}),
    'typescript': (['.BBBBBBB.', 'BWWWBWWWB', 'BBWBBWBBB', 'BBWBBWWWB', 'BBWBBBBWB', 'BBWBBWWWB', '.BBBBBBB.'],
        {'B': '#3178C6', 'W': '#FFFFFF'}),
    'vue': (['GGDD.DDGG', '.GGDDDGG.', '.GGGDGGG.', '..GGDGG..', '..GGGGG..', '...GGG...', '....G....'],
        {'G': '#42B883', 'D': '#5C7C9C'}),
    'nextjs': (['..RRRRR..', '.RN...NR.', 'R.NN..N.R', 'R.N.N.N.R', 'R.N..NN.R', '.RN...NR.', '..RRRRR..'],
        {'R': '#9A907C', 'N': '#FFF1D6'}),
    'swift': (['.....O...', 'O.....O..', '.O....OO.', '..OO.OOO.', '...OOOOO.', 'OOOOOOOOO', '.OOOO...O'],
        {'O': '#F05138'}),
    'swiftui': (['.BBBBWBB.', 'BWBBBBWBB', 'BBWBBBWWB', 'BBBWWWWWB', 'BWWWWWWWB', 'BBWWWBBBW', '.BBBBBBB.'],
        {'B': '#0071E3', 'W': '#E6F0FF'}),
    'design-systems': (['...P...', '..PPP..', '.T.P.K.', 'TTT.KKK', '.T.P.K.', '..PPP..', '...P...'],
        {'P': '#A259FF', 'T': '#2BD9C4', 'K': '#FF7EB6'}),
    'accessibility': (['..CCCCC..', '.C..C..C.', 'C.CCCCC.C', 'C...C...C', 'C..C.C..C', '.C.C.C.C.', '..CCCCC..'],
        {'C': '#7FA6FF'}),
    'cadran': (['..RRRRR..', '.R.....R.', 'R.R...R.R', 'R..R.R..R', 'R...R...R', '.O.....O.', '..OOOOO..'],
        {'R': '#FFF6EC', 'O': '#F6A640'}),
    'lift': (['.X.....X.', 'XX.....XX', 'XX.....XX', 'XXXXXXXXX', 'XX.....XX', 'XX.....XX', '.X.....X.'],
        {'X': '#7FA6FF'}),
    'led-board': (['........P', '......P.O', '......O.O', '....P.O.O', '....O.O.O', '..P.O.O.O', 'P.O.O.O.O'],
        {'O': '#FF6A00', 'P': '#FFB46A'}),
}

# 24-LED tile for the GitHub card, like the app icons: (rows, palette).
TILE_ICONS = {
    'github': ([
        '...BBBBBBBBBBBBBBBBBB...',
        '..BBBBBBBBBBBBBBBBBBBB..',
        '.BBBBBBBBCCCCCCBBBBBBBB.',
        'BBBBBBBCCCCCCCCCCBBBBBBB',
        'BBBBBCCCCCCCCCCCCCCBBBBB',
        'BBBBCCBCCCCCCCCCCBCCBBBB',
        'BBBBCCBBCCCCCCCCBBCCBBBB',
        'BBBCCCBBBBBBBBBBBBCCCBBB',
        'BBBCCCBBBBBBBBBBBBCCCBBB',
        'BBCCCBBBBBBBBBBBBBBCCCBB',
        'BBCCCBBBBBBBBBBBBBBCCCBB',
        'BBCCCBBBBBBBBBBBBBBCCCBB',
        'BBCCCBBBBBBBBBBBBBBCCCBB',
        'BBCCCCBBBBBBBBBBBBCCCCBB',
        'BBCCCCCBBBBBBBBBBCCCCCBB',
        'BBBCCCCCCBBBBBBCCCCCCBBB',
        'BBBCCCBCCCBBBBCCCCCCCBBB',
        'BBBBCCBBCCBBBBCCCCCCBBBB',
        'BBBBCCCCBBBBBBCCCCCCBBBB',
        'BBBBBCCCCCBBBBCCCCCBBBBB',
        'BBBBBBBCCCBBBBCCCBBBBBBB',
        '.BBBBBBBBCBBBBCBBBBBBBB.',
        '..BBBBBBBBBBBBBBBBBBBB..',
        '...BBBBBBBBBBBBBBBBBB...',
    ], {'B': '#0D1A10', 'C': '#FFF1D6'}),
}


# Pixel emojis that sit on a line of text: (rows, palette).
EMOJI = {
    'fr': (['BBWWRR'] * 5, {'B': '#3D7BFF', 'W': CREAM, 'R': '#EF4135'}),  # 5 tall, on 3x5 text
    'sparkle': (['..C..', '..C..', 'CC.CC', '..C..', '..C..'], {'C': PET}),
    'apple': (['...G.', '.RGR.', 'RRRRR', 'RRRRR', '.R.R.'], {'R': '#F23645', 'G': '#4CD964'}),
}


def emoji(key, col, row):
    rows, palette = EMOJI[key]
    return sprite(rows, palette, col, row)


# --- panels -----------------------------------------------------------------------------

def years():
    start = dt.date(2017, 9, 1)
    return TODAY.year - start.year - ((TODAY.month, TODAY.day) < (start.month, start.day))


def hero(n=None):
    """The header as four images, see columns: the top band in three (greeting, the live counter, "I'M:"),
    then the rest. api/hero.py serves the counter. n is the visitor number (None when the count is out)."""
    pn = Panel(284, 101)  # rows: border 0, counter housing 5-23, photo and text 28-79, rule 84, ticker 89-95, border 100: 4 clear rows between each
    stack = [('REACT', CREAM, 'react'), ('TYPESCRIPT', CREAM, 'typescript'), ('VUE', CREAM, 'vue'), ('NEXT.JS', CREAM, 'nextjs'),
             ('SWIFT', CREAM, 'swift'), ('SWIFTUI', CREAM, 'swiftui'), ('DESIGN SYSTEMS', MUTED, 'design-systems'),
             ('ACCESSIBILITY', MUTED, 'accessibility'), ('CADRAN', CADRAN, 'cadran'), ('LIFT', LIFT, 'lift'),
             ('CRYPTO LED BOARD', BOARD, 'led-board')]
    tick, length = ticker([seg for item in stack for seg in (item, ('·', MUTED))], 89)
    name = title('ILYES ABD-LILLAH', 68, 28, CREAM)
    typed = title_width('ILYES ABD-LILLAH')  # the width the typing uncovers, a letter at a time
    lines = [('AT POSITIVE SOLUTION · TOULOUSE, FRANCE', 'fr'), (f'{years()}+ YEARS OF PRODUCT INTERFACES, DESIGN SYSTEMS', 'sparkle'),
             ('AND NATIVE APPS FOR THE MAC AND IPHONE.', 'apple')]
    intro = {}
    for i, (ln, icon) in enumerate(lines):  # each line ends on its emoji
        intro |= text(ln, 68, 60 + i * 7, MUTED, '3x5') | emoji(icon, 68 + text_width(ln, '3x5') + 4, 60 + i * 7)
    assert max(c for c, _ in {**name, **intro}) < pn.cols - 2
    chase = {(c, pn.rows - 1): RULE for c in range(-3, pn.cols + 3, 3)}  # marching along the bottom only: the top
    border = {(c, 0): RULE for c in range(0, pn.cols, 3)}  # crosses the counter's cut, and pieces can't march in step
    lead = 'HELLO VISITOR NUMBER #'  # then the counter, then "I'M:", which leads into the name below
    x = 11 + text_width(lead) + 6  # 4 clear LEDs each side of the housing
    hello, reels, count_css = drums(pn, n, x, 7)
    hello = bezel(x, 7, 7 * 11 + 6 * 2, 15, MUTED) | hello  # the counter's housing
    live = f'<g class="live">{pn.draw({(c, r): RED for c in (6, 7) for r in (13, 14)})}</g>'  # static, so lit even when the count is out
    glow = halo(6, 28, 52, 52, CREAM, reach=3, rad=.14 * 52, power=.18) | outline(6, 28, 52, CREAM, .14)  # light around the photo
    body = (pn.draw(glow | art('avatar', 6, 28, .14))
            + f'<g clip-path="url(#typed)">{pn.draw(name)}<g clip-path="url(#band)">{pn.draw(title("ILYES ABD-LILLAH", 68, 28, "#FFFFFF", decor=True))}</g></g>'
            + f'<g class="type"><g class="caret">{pn.draw(hline(68 + typed + 2, 68 + typed + 11, 43, CREAM) | hline(68 + typed + 2, 68 + typed + 11, 44, CREAM))}</g></g>'
            + pn.draw(text('SENIOR TECH LEAD · DESIGN ENGINEER', 68, 47, CREAM) | intro | hline(0, pn.cols - 1, 84, RULE) | border)
            + f'<g class="chase">{pn.draw(chase)}</g><g class="tick">{pn.draw(tick)}</g>'
            + pn.draw(hello | text(lead, 11, 11, CREAM) | text("I'M:", x + 7 * 11 + 6 * 2 + 6, 11, CREAM)) + reels + live)
    # The name types itself: a mask that uncovers it a letter at a time, an underscore cursor that follows
    # and then blinks. Reduced motion shows the whole name.
    letters = len('ILYES ABD-LILLAH')
    keys = ''.join(f'{num(k * 100 / letters)}%{{transform:translateX(-{pn.px(typed - round(k * typed / letters))}px)}}' for k in range(letters))
    defs = (f'<clipPath id="band"><rect class="sweep" {pn.box(54, 0, 8, pn.rows)}/></clipPath>'
            f'<clipPath id="typed"><rect class="type" {pn.box(68, 28, typed + 1, 14)}/></clipPath>')
    style = (f'.type{{animation:type 1.6s 1s step-end backwards}}@keyframes type{{{keys}100%{{transform:none}}}}'
             f'.caret{{animation:caret 1s step-end infinite}}@keyframes caret{{50%{{opacity:0}}}}'
             f'.sweep{{transform:translateX(-{pn.px(80)}px);animation:sweep 8s 2.5s infinite}}'
             f'@keyframes sweep{{0%{{transform:none;animation-timing-function:steps(52)}}25%,100%{{transform:translateX({pn.px(208)}px)}}}}'
             f'.chase{{animation:chase .9s steps(3) infinite}}@keyframes chase{{to{{transform:translateX(-{pn.px(3)}px)}}}}'
             + scroll('tick', length, 14, pn) + count_css + '.live{animation:live 1.2s step-end infinite}@keyframes live{50%{opacity:0}}')
    alt = (f'Ilyes Abd-Lillah, Senior Tech Lead and Design Engineer at Positive Solution in Toulouse, France. '
           f'{years()}+ years of product interfaces, design systems and native apps for the Mac and iPhone.'
           + ('' if n is None else f' Hello, visitor number {n}!'))  # the alt keeps the greeting short
    still = alt.split(' Hello,')[0]
    return (columns(pn, HERO_LIVE, ['', alt, ''], body, style, defs, bottom=HERO_BAND)
            + columns(pn, [], [still], body, style, defs, top=HERO_BAND))


def card_text(name, tag, sub, lines, foot, left, accent, screen=223):
    """Title and framed tag, a line in the accent right under it, three lines of copy, then an optional
    footer in the accent. With `screen`, also the bezel of a screen on the right, whose contents (from that
    column, rows 4-51) are the caller's; the project cards draw a device there instead."""
    name_w, tag_w = title_width(name), text_width(tag, '3x5')
    assert left + max([name_w + 12 + tag_w, *(text_width(t, '3x5') for t in [sub, *lines, foot or ''])]) < 220, name
    cells = ({} if screen is None else bezel(screen, 4, 57, 48, accent)) | title(name, left, 6, accent) | text(tag, left + name_w + 8, 10, MUTED, '3x5')
    cells |= frame(left + name_w + 5, 7, left + name_w + 10 + tag_w, 16, RULE) | text(sub, left, 23, accent, '3x5')
    for i, ln in enumerate(lines):
        cells |= text(ln, left, 36 + i * 8, CREAM, '3x5')
    return cells | (text(foot, left, 61, accent, '3x5') if foot else {})


def project(pn, alt, name, tag, lines, tech, cta, accent, icon, demo):
    """One band of the projects card, 76 rows on `pn`: a 24-LED icon level with the title's top, then name,
    link, description and stack from column 40; on the right (columns 220-283) `demo` draws the app running
    on its device. Returns (alt, body, css)."""
    cells = halo(6, 6, 24, 24, accent) | icon | outline(6, 6, 24, accent) | card_text(name, tag, cta, lines, tech, 40, accent, None)
    body, css = demo(pn.at_row(3))  # the device 3 rows down, so its light stays clear of the rule above
    return alt, pn.draw(cells | {(c, 0): RULE for c in range(0, pn.cols, 2)}) + body, css  # a dotted rule over each project


def tile(key, col, row, accent):
    rows, palette = TILE_ICONS[key]
    return halo(col, row, 24, 24, accent) | sprite(rows, palette, col, row) | outline(col, row, 24, accent)


def projects_mark(col, row, size=16):
    """The projects heading's icon, a size below the app icons: three app cards (Cadran, Lift, LED Board)
    stacked down to the right on a dark tile, each lit along its top edge and cut from the one behind."""
    tile_ = '#1C120A'
    cells = {(col + c, row + r): tile_ for r in range(size) for c in range(size) if rounded((c + .5) / size, (r + .5) / size, .22)}
    for i, color in enumerate((CADRAN, LIFT, BOARD)):
        x0, y0 = col + 2 + 3 * i, row + 2 + 3 * i
        if i:  # a one-LED gap from the card behind
            cells |= {(x0 + c, y0 + r): tile_ for r in range(-1, 7) for c in range(-1, 7) if (x0 + c, y0 + r) in cells}
        cells |= {(x0 + c, y0 + r): hexc(mix(rgb(color), (255, 255, 255), .4)) if r == 0 else color
                  for r in range(6) for c in range(6) if not (c in (0, 5) and r in (0, 5))}
    return cells


def projects_card(downloads=None, now=None, only=None):
    """The projects as one card in four bands: the heading, then Cadran, Lift and LED Board. Each band is
    an image of its own so README.md can link it; api/cadran.py and api/lift.py serve theirs live (the
    download count, the clocks), the build writes the other two. The live bands come as (margin, live
    part), see columns. `only` draws just that band."""
    pn = Panel(284, 32 + 3 * 76)
    heading = (halo(6, 8, 16, 16, CREAM) | projects_mark(6, 8) | outline(6, 8, 16, CREAM)  # 16 LEDs, level with the title and its line
               | title('MY PROJECTS', 32, 8, CREAM) | text('3 APPS SHIPPED · MACOS · IOS · WEB', 32, 19, MUTED, '3x5'))
    makers = [lambda b: ('My projects: three apps shipped, on macOS, iOS and the web.', b.draw(heading), ''),
              lambda b: cadran(b, downloads, now), lambda b: lift(b, None, now), lambda b: board(b)]
    tops = [0, 32, 108, 184, 260]
    out = []
    for i, make in enumerate(makers):
        if only is None or i == only:
            alt, body, css = make(pn.at_row(tops[i]))
            band = dict(top=tops[i] or None, bottom=tops[i + 1] if i < 3 else None)
            out += columns(pn, DEVICE_LIVE, [alt, alt], body, css, **band) if i in (1, 2) else slices(pn, [alt], body, css, **band)
    return out


def paris(now):
    """Toulouse time, by the EU rule: summer time from the last Sunday of March to the last Sunday of
    October, both at 01:00 UTC. No time zone database needed on Vercel."""
    def last_sunday(month):
        d = dt.datetime(now.year, month, 31, 1, tzinfo=dt.timezone.utc)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    return now.astimezone(dt.timezone(dt.timedelta(hours=2 if last_sunday(3) <= now < last_sunday(10) else 1)))


def ticking(pn, glyphs, places, now, color, name, minutes=120, gap=3):
    """Clock digits that keep time once the image has loaded. places maps an index into "HHMM" to the
    (col, row) of that digit; each is a reel of the ten glyphs that steps on the minute, starting at the
    current second. With reduced motion it simply shows the time of the request."""
    local = paris(now)
    first = local.replace(second=0, microsecond=0)
    seq = [(first + dt.timedelta(minutes=i)).strftime('%H%M') for i in range(minutes)]
    h, w = len(glyphs['0']), len(glyphs['0'][0])
    pitch = (h + gap) * pn.p
    svg, css = '', ''
    for k, (col, row) in places.items():
        reel = {(col + c, row + int(d) * (h + gap) + r): color for d in '0123456789'
                for r, line_ in enumerate(glyphs[d]) for c, ch in enumerate(line_) if ch == '1'}
        kf = ''.join(f'{num(i * 100 / minutes)}%{{transform:translateY(-{num(int(v[k]) * pitch)}px)}}'
                     for i, v in enumerate(seq) if i == 0 or v[k] != seq[i - 1][k])
        css += (f'.{name}{k}{{animation:{name}{k} {minutes * 60}s step-end infinite;animation-delay:-{local.second}s}}'
                f'@keyframes {name}{k}{{{kf}}}')
        svg += (f'<clipPath id="{name}c{k}"><rect {pn.box(col, row, w, h)}/></clipPath><g clip-path="url(#{name}c{k})">'
                f'<g class="{name}{k}" transform="translate(0 -{num(int(seq[0][k]) * pitch)})">{pn.draw(reel)}</g></g>')
    return svg, css


def slab(col, row, w, h, rad, top, bottom):
    """A rounded w x h block lit from above: RGB `top` fading to `bottom`."""
    return {(col + c, row + r): hexc(mix(top, bottom, r / max(h - 1, 1)))
            for r in range(h) for c in range(w) if tile_dist(c, r, w, h, rad) <= 0}


def imac(color):
    """An iMac in the app's colour, in its light: body 58x42 at (223, 3) with the chin under a 54x33 screen
    at (225, 5), on a stand down to row 52."""
    tint, white, dark = rgb(color), (255, 255, 255), rgb(BG)
    return (halo(223, 3, 58, 42, color, reach=3, rad=3, power=.3)
            | slab(240, 51, 24, 2, 0, mix(tint, dark, .3), mix(tint, dark, .55))       # foot
            | slab(246, 45, 12, 6, 0, mix(tint, dark, .4), mix(tint, dark, .6))        # neck
            | slab(223, 3, 58, 42, 3, mix(tint, white, .55), mix(tint, dark, .25))     # body and chin
            | slab(224, 4, 56, 35, 1, (24, 22, 26), (24, 22, 26))                      # black border round the screen
            | {(250 + c, 40 + r): hexc(mix(tint, dark, .45)) for c, r in ((1, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2))})


def monitor(color):
    """A graphite display in the app's light: bezel 58x37 at (223, 3) round a 54x33 screen at (225, 5), stand to row 48."""
    tint, dark = rgb(color), rgb(BG)
    return (halo(223, 3, 58, 37, color, reach=3, rad=2, power=.3)
            | slab(240, 47, 24, 2, 0, (70, 66, 72), (40, 38, 44)) | slab(248, 40, 8, 7, 0, (60, 56, 62), (36, 34, 40))
            | slab(223, 3, 58, 37, 2, mix((84, 80, 88), tint, .25), mix((34, 32, 38), dark, .3)))


def iphone(color):
    """An iPhone in the app's colour and light: frame 34x62 at (233, 3), screen 30x58 at (235, 5), rounded."""
    tint, white, dark = rgb(color), (255, 255, 255), rgb(BG)
    side = hexc(mix(tint, dark, .35))
    return (halo(233, 3, 34, 62, color, reach=3, rad=6, power=.3)
            | {(232, r): side for r in [*range(15, 19), *range(21, 27)]} | {(267, r): side for r in range(18, 25)}  # buttons
            | slab(233, 3, 34, 62, 6, mix(tint, white, .5), mix(tint, dark, .3)) | slab(234, 4, 32, 60, 6, (14, 14, 18), (14, 14, 18)))


def cadran(pn, downloads=None, now=None):
    """Cadran on an iMac desktop: its Titan face on the wallpaper, with the menu bar, folders and dock.
    `downloads` comes live from the counter cadranapp.com keeps (api/cadran.py)."""
    accent, top, bottom, ink, dock_top, dock_bottom = CADRAN, (236, 124, 38), (196, 92, 18), (64, 30, 8), (246, 172, 112), (224, 146, 88)

    def demo(pn):
        wall = {(225 + c, 5 + r): hexc(mix(top, bottom, r / 32)) for r in range(33) for c in range(54)}
        ink_ = hexc(ink)  # Titan's dark digits, dark like the unlit LEDs between them
        titan = art_data()['titan']
        tw = len(titan['0'][0])  # the cells touch: the glyphs' own margins are the gap, as on the face
        clock, clock_css = ticking(pn, titan, {0: (229, 9), 1: (229 + tw, 9), 2: (229, 21), 3: (229 + tw, 21)},
                                   now or dt.datetime.now(dt.timezone.utc), ink_, 'ti')  # hours over minutes, as Titan sets them
        menu = ({(225 + c, 5 + r): hexc(mix(top, (255, 255, 255), .3)) for r in range(3) for c in range(54)}
                | sprite(['.C.', 'CCC', 'CCC'], {'C': ink_}, 227, 5)  # the Apple menu, menus, status items
                | {(c, 6): ink_ for a, b in ((232, 235), (238, 241), (244, 246), (266, 268), (271, 277)) for c in range(a, b + 1)})
        folders = {(271 + c, top + r): '#6CB8F0' for top in (10, 17) for r in range(5) for c in range(6) if r or c < 3}
        dock = slab(237, 33, 22, 4, 1, dock_top, dock_bottom)
        for i, colors in enumerate([('#4A9BFF',), ('#B63D60', '#E2522A'), ('#4CD964',), ('#FFB340',), ('#C8C8D0',)]):
            dock |= {(239 + i * 4 + c, 34 + r): colors[min(c * len(colors) // 3, len(colors) - 1)] for c in range(3) for r in range(2)}
        count = {}  # under the iMac: live, so in the device's column
        if downloads:
            label = f'{downloads:,} DOWNLOADS'
            w = 7 + text_width(label, '3x5')
            x = min(252 - w // 2, 284 - w)  # centred under the iMac, but inside the card
            count = sprite(STAT_ICONS['download'], {'C': CADRAN}, x, 57) | text(label, x + 7, 57, CADRAN, '3x5')
        return pn.draw(imac(accent) | wall | menu | folders | dock | count) + clock, clock_css
    link = 'CADRANAPP.COM ↗'
    return project(pn, 'Cadran: clock faces rendered on your macOS wallpaper, on every Space and display. Featured on Product Hunt '
                   'and in awesome-mac. Built with SwiftUI, Core Animation and Next.js.'
                   + (f' Downloaded {downloads:,} times.' if downloads else ''),
                   'CADRAN', 'MACOS',
                   ['CLOCK FACES RENDERED ON YOUR WALLPAPER,', 'ON EVERY SPACE AND EVERY DISPLAY.',
                    'FEATURED ON PRODUCT HUNT & AWESOME-MAC.'],
                   'SWIFTUI · CORE ANIMATION · NEXT.JS', link, accent, cadran_icon(6, 6), demo)


# The iPhone's lock-screen digits, drawn by hand at 5x9 so every stroke is one even LED (SF condensed came
# out ragged at this size).
PHONE_DIGITS = {k: [ln.replace('#', '1').replace('.', '0') for ln in v.split()] for k, v in {
    '0': '.###. #...# #...# #...# #...# #...# #...# #...# .###.', '1': '..#.. .##.. #.#.. ..#.. ..#.. ..#.. ..#.. ..#.. #####',
    '2': '.###. #...# ....# ....# ...#. ..#.. .#... #.... #####', '3': '.###. #...# ....# ....# ..##. ....# ....# #...# .###.',
    '4': '...#. ..##. .#.#. #..#. #..#. ##### ...#. ...#. ...#.', '5': '##### #.... #.... ####. ....# ....# ....# #...# .###.',
    '6': '.###. #.... #.... ####. #...# #...# #...# #...# .###.', '7': '##### ....# ...#. ...#. ..#.. ..#.. .#... .#... .#...',
    '8': '.###. #...# #...# #...# .###. #...# #...# #...# .###.', '9': '.###. #...# #...# #...# .#### ....# ....# ....# .###.',
    ':': '.. .. ## ## .. ## ## .. ..'}.items()}


DUMBBELL = ['.CC.....CC.', 'CCC.....CCC', 'CCCCCCCCCCC', 'CCC.....CCC', '.CC.....CC.']


def lift(pn, downloads=None, now=None):
    """Lift on an iPhone lock screen: the time, and the rest timer counting down in a Live Activity."""
    rest, cycle, gap = 30, 31, 5  # timer seconds; loop length; rows between digits on a reel
    left = [rest - t for t in range(cycle)]

    def demo(pn):
        screen = {(235 + c, 5 + r): hexc(mix((22, 30, 64), (8, 10, 24), r / 57))
                  for r in range(58) for c in range(30) if tile_dist(c, r, 30, 58, 5) <= 0}
        island = slab(241, 7, 18, 4, 2, (6, 6, 8), (6, 6, 8)) | {(c, r): LIFT for c in (243, 244) for r in (8, 9)}
        phone = PHONE_DIGITS
        w, cw = len(phone['0'][0]), len(phone[':'][0])
        x = 235 + (30 - (4 * w + cw + 6)) // 2  # "HH:MM": one LED between digits, two round the colon
        local = paris(now or dt.datetime.now(dt.timezone.utc))
        colon = {(x + 2 * w + 3 + c, 23 + r): CREAM for r, line_ in enumerate(phone[':']) for c, ch in enumerate(line_) if ch == '1'}
        clock, clock_css = ticking(pn, phone, {0: (x, 23), 1: (x + w + 1, 23), 2: (x + 2 * w + cw + 5, 23), 3: (x + 3 * w + cw + 6, 23)},
                                   now or dt.datetime.now(dt.timezone.utc), CREAM, 'ph')
        day = f'{local:%a} {local.day}'.upper()  # "WED 14": the full name is wider than the screen
        widget = (slab(237, 38, 26, 21, 3, (44, 50, 72), (32, 36, 54)) | sprite(DUMBBELL, {'C': LIFT}, 239, 41)
                  | {(251 + i * 3 + a, 42 + b): (LIFT if i < 3 else RULE) for i in range(4) for a in range(2) for b in range(2)}
                  | hline(239, 260, 57, RULE) | {(c, 61): '#787882' for c in range(245, 255)})
        x0 = 238  # "0:30", 23 LEDs, centred in the widget
        tens, ones = {}, {}
        for i, d in enumerate('3210'):
            tens |= text(d, x0 + 12, 48 + i * (7 + gap), CREAM)
        for d in range(10):
            ones |= text(str(d), x0 + 18, 48 + d * (7 + gap), CREAM)
        step = (7 + gap) * pn.p

        def reel(name, offsets):
            kf = ''.join(f'{num(i * 100 / cycle)}%{{transform:translateY(-{num(o * step)}px)}}' for i, o in enumerate(offsets))
            return f'.{name}{{animation:{name} {cycle}s step-end infinite}}@keyframes {name}{{{kf}}}'
        css = (reel('tens', [3 - v // 10 for v in left]) + reel('ones', [v % 10 for v in left])
               + f'.bar{{animation:bar {cycle}s infinite}}@keyframes bar{{0%{{transform:none;animation-timing-function:steps(22)}}'
                 f'{num(rest * 100 / cycle)}%,100%{{transform:translateX(-{pn.px(22)}px)}}}}')
        static = (iphone(LIFT) | screen | island | text(day, 235 + (30 - text_width(day, '3x5')) // 2, 15, MUTED, '3x5') | colon | widget
                  | text('0:', x0, 48, CREAM))
        return (pn.draw(static) + clock
                + f'<clipPath id="reel"><rect {pn.box(x0 + 12, 48, 11, 7)}/></clipPath>'
                  f'<clipPath id="barwin"><rect {pn.box(239, 57, 22, 1)}/></clipPath>'
                + f'<g clip-path="url(#reel)"><g class="tens">{pn.draw(tens)}</g><g class="ones">{pn.draw(ones)}</g></g>'
                + f'<g clip-path="url(#barwin)"><g class="bar">{pn.draw(hline(239, 260, 57, LIFT))}</g></g>'), css + clock_css
    link = 'FREE ON THE APP STORE ↗' + (f' · {downloads:,} DOWNLOADS' if downloads else '')
    return project(pn, 'Lift: a research-based hypertrophy program for iPhone and iPad, built backwards from your goal date, '
                   'with the rest timer on the lock screen and in the Dynamic Island. Free on the App Store.'
                   + (f' Downloaded {downloads:,} times.' if downloads else ''),
                   'LIFT', 'IOS · IPADOS',
                   ['HYPERTROPHY PROGRAM BUILT BACKWARDS', 'FROM YOUR GOAL DATE. REST TIMER ON THE',
                    'LOCK SCREEN AND IN THE DYNAMIC ISLAND.'],
                   'REACT · CAPACITOR · ACTIVITYKIT', link, LIFT, art('lift', 6, 6, .22), demo)


def board(pn):
    """Crypto LED Board on a desktop monitor: the ticker over a scrolling chart."""
    period, base = 84, 37  # the chart fills the screen down to its last row

    def demo(pn):
        items = []
        for sym, up in [('BTC', 1), ('ETH', 0), ('SOL', 1), ('BNB', 1), ('XRP', 0), ('ADA', 1), ('DOGE', 0)]:
            items += [(sym, BOARD), ('▲' if up else '▼', GREEN if up else RED)]  # symbols only: a picture, not a feed
        tick, n = ticker(items, 0, gap=5)
        tick = {(c + 225, r + 7): v for (c, r), v in tick.items()}
        chart = {}
        for i in range(period):  # periodic, so the scroll loops without a seam
            t = 2 * math.pi * i / period
            h = max(1, round(9 + 5 * math.sin(2 * t) + 3 * math.sin(5 * t + 1) + 1.5 * math.sin(11 * t + 2)))
            for r in range(base - h + 1, base + 1):
                chart[(225 + i, r)] = chart[(225 + i + period, r)] = BOARD if r == base - h + 1 else '#5A2600'
        screen = {(225 + c, 5 + r): hexc(mix(rgb(BG), rgb(BOARD), .04)) for r in range(33) for c in range(54)}
        return (pn.draw(monitor(BOARD) | screen)
                + f'<clipPath id="win"><rect {pn.box(225, 5, 54, 33)}/></clipPath><g clip-path="url(#win)">'
                f'<g class="tick">{pn.draw(tick)}</g>{pn.draw(hline(225, 278, 16, RULE))}<g class="chart">{pn.draw(chart)}</g></g>',
                scroll('tick', n, 10, pn) + scroll('chart', period, 4, pn))
    return project(pn, 'Crypto LED Board: live Binance Spot prices, charts and order book rendered on a pixel-art LED matrix. '
                   'Built with React, WebSockets and Canvas/WebGL.',
                   'LED BOARD', 'CRYPTO · WEB',
                   ['LIVE BINANCE SPOT PRICES, CHARTS AND', 'ORDER BOOK ON A PIXEL-ART LED MATRIX,',
                    'WITH CRT EFFECTS AND ITS OWN FONTS.'],
                   'REACT · WEBSOCKETS · CANVAS / WEBGL', 'OPEN THE LIVE BOARD ↗', BOARD, board_icon(6, 6), demo)


GH = '#39D353'  # GitHub's contribution green
GITHUB_USER = 'Ilyomix'
STATS_QUERY = ('{ user(login: "%s") { followers { totalCount } '
               'repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) { totalCount nodes { stargazerCount '
               'languages(first: 6, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } } } '
               'contributionsCollection { totalCommitContributions totalPullRequestContributions '
               'contributionCalendar { totalContributions weeks { contributionDays { contributionLevel date } } } } } }' % GITHUB_USER)
LANG_SHORT = {'TypeScript': 'TS', 'JavaScript': 'JS', 'Python': 'PY'}
STAT_ICONS = {  # 5x5, beside each count
    'commit': ['.....', '.CCC.', 'CC.CC', '.CCC.', '.....'],
    'pr': ['C...C', 'C...C', 'C..C.', 'C.C..', 'CC...'],  # a branch merging back
    'repo': ['CCCC.', 'C..C.', 'C..C.', 'CCCC.', 'C.C..'],
    'star': ['..C..', 'CCCCC', '.CCC.', '.C.C.', 'C...C'],
    'follower': ['.CCC.', '.CCC.', '.....', 'CCCCC', 'CCCCC'],
    'download': ['..C..', 'C.C.C', '.CCC.', '..C..', 'CCCCC'],  # an arrow down onto a tray
}


def import_stats():
    """Refreshes github.json through the gh CLI: logged in on a Mac, GH_TOKEN in the workflow."""
    import subprocess
    u = json.loads(subprocess.run(['gh', 'api', 'graphql', '-f', f'query={STATS_QUERY}'],
                                  check=True, capture_output=True, text=True).stdout)['data']['user']
    c, sizes, colors = u['contributionsCollection'], {}, {}
    for repo in u['repositories']['nodes']:
        for e in repo['languages']['edges']:
            name = e['node']['name']
            sizes[name], colors[name] = sizes.get(name, 0) + e['size'], e['node']['color'] or MUTED
    total = sum(sizes.values()) or 1
    levels = ['NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE']
    (OUT / 'github.json').write_text(json.dumps({
        'contributions': c['contributionCalendar']['totalContributions'], 'commits': c['totalCommitContributions'],
        'prs': c['totalPullRequestContributions'], 'repos': u['repositories']['totalCount'],
        'stars': sum(r['stargazerCount'] for r in u['repositories']['nodes']), 'followers': u['followers']['totalCount'],
        'languages': [[n, colors[n], round(sz / total, 3)] for n, sz in sorted(sizes.items(), key=lambda kv: -kv[1])[:4]],
        'weeks': [''.join(str(levels.index(d['contributionLevel'])) for d in w['contributionDays']) for w in c['contributionCalendar']['weeks']],
        'first': c['contributionCalendar']['weeks'][0]['contributionDays'][0]['date'],
    }, indent=1) + '\n')


def github():
    """GitHub activity, refreshed daily by the workflow (`build.py stats`): the year's contributions as an
    LED calendar, the counts beside it, and the languages across the public repos."""
    g = json.loads((OUT / 'github.json').read_text())
    pn = Panel(284, 80)  # rows: title 6, line 23, legend 34, grid 42-61, months 65, years 72
    sub, right = f"{g['contributions']:,} CONTRIBUTIONS IN 12 MONTHS", 186  # the counts' column starts at `right`
    assert 40 + text_width(sub, '3x5') < right - 3, 'the contributions line runs into the counts'
    cells = tile('github', 6, 6, GH) | card_text('GITHUB', f'@{GITHUB_USER.upper()}', sub, [], None, 40, GH, None)
    shade = [RULE] + [hexc(mix(rgb(BG), rgb(GH), t)) for t in (.3, .5, .75, 1)]
    for w, days in enumerate(g['weeks']):  # a week per column, Sunday on top; the first week may start mid-week
        top = 7 - len(days) if w == 0 else 0
        cells |= {(6 + w * 3 + a, 42 + (top + d) * 3 + b): shade[int(lvl)] for d, lvl in enumerate(days) for a in (0, 1) for b in (0, 1)}
    sunday = dt.date.fromisoformat(g['first']) - dt.timedelta(days=7 - len(g['weeks'][0]))  # the grid's first column
    end, first_label = 0, True
    for w in range(1, len(g['weeks'])):  # every other month (Jan, Mar...) under the week its 1st falls in; the year under the first and each January
        day = next((sunday + dt.timedelta(weeks=w, days=d) for d in range(7) if (sunday + dt.timedelta(weeks=w, days=d)).day == 1), None)
        col = 6 + w * 3
        if day and day.month % 2 and col > end and col + text_width(day.strftime('%b'), '3x5') <= 164:
            cells |= text(day.strftime('%b').upper(), col, 65, MUTED, '3x5')
            end = col + text_width(day.strftime('%b'), '3x5')
            if first_label or day.month == 1:
                cells |= text(str(day.year), col, 72, MUTED, '3x5')
            first_label = False
    x = 164 - text_width('MORE', '3x5')  # the legend, over the grid's right end: the months and years below keep their rows
    cells |= text('MORE', x, 34, MUTED, '3x5')
    cells |= {(x - 17 + i * 3 + a, 35 + b): shade[i] for i in range(5) for a in (0, 1) for b in (0, 1)}
    cells |= text('LESS', x - 19 - text_width('LESS', '3x5'), 34, MUTED, '3x5')
    for i, (icon, label, v) in enumerate([('commit', 'COMMITS', g['commits']), ('pr', 'PULL REQUESTS', g['prs']),
                                          ('repo', 'PUBLIC REPOS', g['repos']), ('star', 'STARS', g['stars']), ('follower', 'FOLLOWERS', g['followers'])]):
        cells |= (sprite(STAT_ICONS[icon], {'C': GH}, right, 8 + i * 11) | text(label, right + 8, 8 + i * 11, MUTED, '3x5')
                  | text(f'{v:,}', 282, 7 + i * 11, CREAM, anchor='end'))
    x, legend = right, []
    for name, color, share in [*g['languages'], ['OTHER', MUTED, max(0, 1 - sum(l[2] for l in g['languages']))]]:
        w = round((282 - right) * share) if name != 'OTHER' else 282 - x
        cells |= {(c, r): color for c in range(x, min(x + w, 282)) for r in (67, 68)}
        x += w
        if name != 'OTHER' and len(legend) < 3:
            readable = color if contrast(color, BG) >= 4.5 else hexc(mix(rgb(color), (255, 255, 255), .35))
            legend.append((f'{LANG_SHORT.get(name, name.upper())} {round(100 * share)}%', readable))
    x = right
    for label, color in legend:
        cells |= text(label, x, 72, color, '3x5')
        x += text_width(label, '3x5') + 6
    alt = (f"GitHub activity for @{GITHUB_USER}: {g['contributions']:,} contributions in the last year, {g['commits']:,} commits, "
           f"{g['prs']} pull requests, {g['repos']} public repos, {g['stars']} stars, {g['followers']} followers. Top languages: "
           + ', '.join(f'{n} {round(100 * s)}%' for n, _, s in g['languages'][:3]) + '.')
    return pn.svg(alt, pn.draw(cells))


LINKS = [('PORTFOLIO', 'globe', CREAM, 'Portfolio: ilyomix.github.io'),
         ('LINKEDIN', 'in', LIFT, 'LinkedIn: Ilyes Abd-Lillah'),
         ('EMAIL', 'mail', PET, 'Email Ilyes')]


def links():
    """One strip, one link per third."""
    pn = Panel(284, 13)
    cells = {(c, r): RULE for c in (92, 191) for r in range(2, 11)}
    for (label, icon, color, _), (a, b) in zip(LINKS, SLOTS):
        x = a + (b - a + 1 - (15 + text_width(label + ' ↗'))) // 2  # icon, label and arrow centred in the slot
        cells |= (sprite(ICONS[icon], {'C': color}, x, 2) | text(label, x + 15, 3, CREAM)
                  | text('↗', x + 16 + text_width(label + ' '), 3, color))
    return slices(pn, [t for *_, t in LINKS], pn.draw(cells))


# --- Byte --------------------------------------------------------------------------------

PET_ACTIONS = ('feed', 'pet', 'play', 'choose')


def pet_state(fields=None):
    """The pet's state from the Redis hash api/act.py writes (field -> string), or the opening state."""
    f = fields or {}
    state = {k: int(f.get(k) or 0) for k in ('feed', 'pet', 'play')}
    state['chosen'] = f.get('chosen') if f.get('chosen') in PETS else 'cat'
    state['last'] = None
    if f.get('last_action') in PET_ACTIONS and f.get('last_at'):
        kind = f.get('last_kind') if f['last_action'] == 'choose' else state['chosen']  # a switch is the only way to change pet
        state['last'] = {'action': f['last_action'], 'kind': kind if kind in PETS else 'cat', 'at': f['last_at'],
                         'where': f.get('last_where') or 'SOMEWHERE'}
    return state


def ago(at, now):
    m = int((now - dt.datetime.fromisoformat(at)).total_seconds() // 60)
    if m < 1:
        return 'JUST NOW'
    if m < 60:
        return f'{m} MIN AGO'
    return f'{m // 60} H AGO' if m < 1440 else f'{m // 1440} DAYS AGO' if m < 144000 else 'LONG AGO'


ACTIONS = [('feed', 'FEED', 'FED', None, '#7EC8FF'), ('pet', 'PET', 'PETTED', 'heart', PET),
           ('play', 'PLAY', 'PLAYED', 'ball', '#FFD866')]  # feed shows the pet's own food


def pet_name(kind):
    return PETS.get(kind, PETS['cat'])['name']


def visit_verb(last):
    """'FED BYTE', 'PICKED SUDO'... for the last visit."""
    if not last:
        return ''
    name = pet_name(last.get('kind', 'cat'))
    return {'feed': f'FED {name}', 'pet': f'PETTED {name}', 'play': f'PLAYED WITH {name}', 'choose': f'PICKED {name}'}[last['action']]


PET_CUT = 58  # the LED row where the live scene ends and the controls start


def pet_card():
    """The pet card's frame: 900 px is the width that splits into both thirds and fifths on LED
    boundaries (cuts at x = 300, 600 and every 180)."""
    return Panel(290, 106, width=900)


POSES = {'rest': (0, 0), 'in': (1, 0), 'crouch': (-3, 2), 'stretch': (2, -2), 'land': (-4, 4)}  # (rise, widen), see `bent`


@functools.lru_cache(maxsize=8)
def pet_art(kind):
    """A pet's parts at LED size, relative to its top left, worked out once per pet: what pet_scene moves."""
    p = PETS[kind]
    colors = p['colors'] | {k.lower(): v for k, v in p['colors'].items()}
    colors['n'] = ramp(colors['N'])[3]  # the light on the nose
    head = grid(*p['head'])

    def painted(keep_face):
        """The head with its small face painted over by the commonest colour around each LED of it."""
        out = {}
        for (c, r), k in head.items():
            if k in 'KHNC' or (k.islower() and not keep_face):
                near = [head.get((c + i, r + j), '.') for i in range(-2, 3) for j in range(-2, 3)]
                near = [q for q in near if q not in '.KHNC' and (keep_face or not q.islower())]
                k = max(sorted(set(near)), key=near.count) if near else 'G'
            out[(c, r)] = k
        return out
    bare = doubled(painted(False))
    if 'marks' in p:
        x, y, rows = p['marks']
        bare |= {(x + c, y + r): 'S' for r, ln in enumerate(rows) for c, k in enumerate(ln) if k == 'S' and (x + c, y + r) in bare}
    base = lit(bare, colors)
    with_face = doubled(painted(True))
    whole = lit({q: k.upper() for q, k in with_face.items()}, colors)
    face = {q: whole[q] for q, k in with_face.items() if k.islower()}
    face |= {(2 * c + i, 2 * r + j): hexc(mix(rgb(base[(2 * c + i, 2 * r + j)]), rgb(colors['C']), .75))
             for (c, r), k in head.items() if k == 'C' for i in (0, 1) for j in (0, 1)}  # blush on the cheeks
    x, y, (w, h) = p['eyes']
    shape = [(c, r, k) for r, ln in enumerate(EYES[(w, h)]) for c, k in enumerate(ln) if k != '.']
    iris = ramp(colors['E'])
    paint = {'K': '#140C08', 'H': '#FFFFFF', 'I': iris[0], 'J': colors['E'], 'W': '#F4F1E6'}
    corners = (x, 44 - x - w)  # the right eye mirrors the left one about column 22
    dark = shaded(base[(x + w // 2, y + h // 2)], .35, 1.2)

    def lids(fur_rows, line):
        """Both eyelids in one state: the fur under the eye over its rows in fur_rows, then a dark line."""
        out = {}
        for x0 in corners:
            out |= {(x0 + c, y + r): base[(x0 + c, y + r)] for c, r, _ in shape if r in fur_rows}
            out |= {(x0 + c, y + r): dark for c, r in line}
        return out
    mid = h // 2
    mx, my, mouths = p['mouth']
    ears = []
    if 'ears' in p:
        g = grid(*p['ears'])
        row, dx, dy = p['twitch']
        flick = {((c + dx, r + dy) if c >= 11 and r < row else (c, r)): k for (c, r), k in g.items()}
        ears = [lit(doubled(g), colors), lit(doubled(flick), colors)]
    body = lit(doubled(grid(*p['body'])), colors)
    tail = []
    if 'tail' in p:
        tail = [lit(chain(p['tail'], k / 8), colors) for k in range(8)]
    elif 'flippers' in p:
        tail = [lit((f := chain(p['flippers'], k / 8)) | {(43 - c, r): v for (c, r), v in f.items()}, colors) for k in range(8)]

    def puff(w_, h_):  # the frog's throat, swelling: lit, its outline only a shade of the belly it swells from
        cx, top = p['throat']
        keys = {(c, r): 'W' for r in range(top, top + h_) for c in range(cx - w_ // 2, cx + w_ // 2)
                if ((c + .5 - cx) / (w_ / 2)) ** 2 + ((r + .5 - top - h_ / 2) / (h_ / 2)) ** 2 <= 1}
        return {q: v if q in keys else ramp(colors['W'])[1] for q, v in lit(keys, colors).items()}
    return {'body': {v: bent(body, p['cut'], *POSES[v]) for v in POSES}, 'head': base, 'ears': ears, 'face': face,
            'eyes': {(x0 + c, y + r): paint[k] for x0 in corners for c, r, k in shape},
            'lids': [lids(range(mid), [(c, mid) for c, r, _ in shape if r == mid]),
                     lids(range(h), [(0, h - 3), (w - 1, h - 3)] + [(c, h - 2) for c in range(1, w - 1)])],
            'happy': lids(range(h), [(c, mid - 1) for c in range(1, w - 1)] + [(0, mid), (w - 1, mid)]),
            'mouth': {k: sprite(v, colors, mx, my) for k, v in mouths.items()}, 'tail': tail,
            'sac': [puff(12, 4), puff(16, 6)] if 'throat' in p else [],
            'top': min(r for part in (base, body, *ears[:1]) for _, r in part)}


class Motion:
    """The CSS that moves a scene: tracks of (seconds, value) on a class, each value held until the next one
    (step-end), so every pose lands on the LEDs. A track loops over its period or, `once`, plays one time; while
    it plays, a class's later track wins over its earlier ones."""

    def __init__(self, pn):
        self.pn, self.anims, self.keys = pn, {}, []

    def track(self, cls, period, seq, decl, once=False, fill='none', delay=0):
        seq = sorted(seq, key=lambda kv: kv[0])
        assert seq[0][0] == 0, cls
        name, kf, last = f'{cls}-{len(self.keys)}', '', None
        for t, v in seq:
            if v != last:
                kf += f'{num(100 * t / period)}%{{{decl(v)}}}'
                last = v
        self.keys.append(f'@keyframes {name}{{{kf}100%{{{decl(seq[-1][1] if once else seq[0][1])}}}}}')
        self.anims.setdefault(cls, []).append(f'{name} {num(period)}s step-end' + (f' -{num(delay)}s' if delay else '')
                                              + (f' 1 {fill}' if once else ' infinite'))

    def move(self, cls, period, seq, **kw):
        """seq of (t, (dx, dy)) in LEDs."""
        self.track(cls, period, seq, lambda v: f'transform:translate({self.pn.px(v[0])}px,{self.pn.px(v[1])}px)', **kw)

    def show(self, cls, ks, period, seq, **kw):
        """seq of (t, k): of the variants cls{k} for k in ks, only k shows."""
        for k in ks:
            self.track(f'{cls}{k}', period, [(t, int(v == k)) for t, v in seq], lambda o: f'opacity:{o}', **kw)

    def fade(self, cls, period, seq, **kw):
        self.track(cls, period, seq, lambda o: f'opacity:{num(o)}', **kw)

    def css(self):
        return ''.join(f'.{c}{{animation:{",".join(a)}}}' for c, a in self.anims.items()) + ''.join(self.keys)


def swing(n, beats):
    """A tail's n frames over time, and the time they take: one frame every `beat` seconds through its swing
    and `hold` more at each end of it, `count` times, for each (beat, hold, count); (0, hold, 0) rests `hold`
    seconds at the middle."""
    seq, t = [], 0.
    for beat, hold, count in beats:
        if not count:
            seq.append((t, 0))
            t += hold
        for _ in range(count):
            for k in range(n):
                seq.append((t, k))
                t += beat + (hold if k in (n // 4, 3 * n // 4) else 0)
    return seq, t


def blinks(*at):
    """Eyelids (0 open, 1 half shut, 2 shut) blinking at each time, quick to close and slower to open; (t, 2)
    blinks twice."""
    seq = [(0, 0)]
    for t in at:
        t, times = t if isinstance(t, tuple) else (t, 1)
        for i in range(times):
            s = t + i * .32
            seq += [(s, 1), (s + .04, 2), (s + .14, 1), (s + .21, 0)]
    return seq


def breaths(t0, t1, period=3.6):
    """Poses for calm breathing from t0 to t1: in 0.9 s into each breath, the head riding the chest, out 1.6 s later."""
    seq, t = [], t0
    while t < t1 - .01:
        seq += [(t, 'rest', (0, 0))] + ([(t + .9, 'in', (0, -1)), (t + 2.5, 'rest', (0, 0))] if t + 2.5 <= t1 else [])
        t += period
    return seq


def hop(t0, dur, height, x0=0, x1=0, fps=24):
    """A jump from t0: up and down a parabola `height` LEDs high in `dur` seconds while moving from x0 to x1,
    sampled `fps` times a second: ([(t, x)], [(t, y)])."""
    n = max(2, round(dur * fps))
    return ([(t0 + i / n * dur, round(x0 + (x1 - x0) * i / n)) for i in range(n + 1)],
            [(t0 + i / n * dur, -round(4 * height * i / n * (1 - i / n))) for i in range(n + 1)])


LOOK = (11.3, [(0, (0, 0)), (2.4, (1, 0)), (2.46, (2, 0)), (4.1, (1, 0)), (4.16, (0, 0)), (6.3, (-1, 0)), (6.36, (-2, 0)),
               (7.6, (-2, -1)), (8.2, (-1, 0)), (8.26, (0, 0)), (9.7, (0, -1)), (10.5, (0, 0))])  # a look around, now and then
BLINK = (9.7, blinks(1.4, (3.9, 2), 7.8))  # at uneven gaps, one of them double
TWITCH = (8.9, [(0, 0), (3.1, 1), (3.22, 0), (3.36, 1), (3.48, 0)])
CROAK = (5.3, [(0, 0), (1, 1), (1.1, 2), (1.5, 1), (1.6, 0), (1.9, 1), (2, 2), (2.4, 1), (2.5, 0)])
SNIFF = (2.9, [(0, 'shut'), (.4, 'sniff'), (.5, 'shut'), (.6, 'sniff'), (.7, 'shut'), (.8, 'sniff'), (.9, 'shut')])
SCENE = (6, 6)  # the pet's top left on the pet card; its props play in columns 46-72, the floor is row 53


@functools.lru_cache(maxsize=36)
def pet_scene(kind, action):
    """The pet doing `action` ('feed', 'pet', 'play', 'choose' or 'sleep') with its props: (svg, css). Every part
    keeps its own clock so the scene never visibly loops: blinks (some double), the tail, the ears, breaths and
    looks around; a reaction comes round every few seconds with anticipation before it and follow-through after
    it, and choosing a pet plays its entrance once, then the pet idles."""
    p, a, pn = PETS[kind], pet_art(kind), pet_card()
    m, (cx, cy), hide = Motion(pn), SCENE, []
    jump = min(8, a['top'] + cy)  # how high the pet can go before it leaves the card

    def draw(cells, x=0, y=0):
        return pn.draw({(c + cx + x, r + cy + y): v for (c, r), v in cells.items()})

    def flip(cls, variants, period, seq, at=(0, 0), **kw):
        """The variants as groups cls0, cls1... (an empty one draws nothing): the first shows when nothing
        moves, seq (t, k) says which shows."""
        ks = [k for k, v in enumerate(variants) if v]
        if len({k for _, k in seq}) > 1:
            m.show(cls, ks, period, seq, **kw)
            hide.extend(f'{cls}{k}' for k in ks if k)
        return ''.join(f'<g class="{cls}{k}">{draw(variants[k], *at)}</g>' for k in ks)

    def gaze(period, seq, **kw):  # where the face looks, as far as this pet's face can go
        m.move('fc', period, [(t, (max(-reach, min(reach, dx)), dy)) for t, (dx, dy) in seq], **kw)
    reach = p.get('look', 2)
    period = {'feed': 10, 'pet': 9, 'play': 6.6, 'choose': 2.6, 'sleep': 4.8}[action]
    once = action == 'choose'
    px = py = face = happy = mouth = sac = None
    props = ''
    if action == 'sleep':
        poses = [(0, 'rest', (0, 1)), (1.3, 'in', (0, 0)), (3.3, 'rest', (0, 1))]
        for i in range(3):  # Zs rise from the head, drift and fade
            props += f'<g class="z{i}">{draw(text("Z", 0, 0, MUTED, "5x7" if i == 1 else "3x5", decor=True), 45, 9)}</g>'
            m.move(f'z{i}', 3.6, [(0, (0, 0))] + [(.3 * k, (k // 3, -k)) for k in range(1, 10)], delay=1.2 * i)
            m.fade(f'z{i}', 3.6, [(0, 1), (2.1, .6), (2.4, .3), (2.7, 0)], delay=1.2 * i)
    elif action == 'feed' and p['food'] == 'fly':  # the frog: a fly buzzes in, the tongue gets it, a gulp
        poses = breaths(0, 2.3) + [(2.3, 'in', (0, -1)), (2.84, 'rest', (0, 0)), (3, 'in', (0, -1)), (3.3, 'rest', (0, 0))]
        poses += breaths(4.3, period)
        mouth = [(0, 'shut'), (2.55, 'open'), (2.84, 'shut'), (3.6, 'lick'), (3.75, 'shut')]
        sac = [(0, 0), (2.95, 1), (3.05, 2), (3.35, 1), (3.45, 0)]
        happy = [(0, 0), (3.5, 1), (4.2, 0)]
        path = [(round(i * .08, 2), (round(68 - 20 * s + 3 * math.sin(9 * s)), round(9 + 4 * math.sin(5 * s) + 2 * math.sin(13 * s))))
                for i in range(31) for s in [i / 30]]
        face = (period, [(t, (int(x > 40), -int(y < 8))) for t, (x, y) in path] + [(2.8, (0, 0)), (5.6, (-1, 0)), (6.6, (0, 0)),
                                                                                   (8, (1, -1)), (8.8, (0, 0))])
        fly, colors = FOOD['fly']
        props += f'<g class="fd">{flip("ff", [sprite(f, colors) for f in fly], .1, [(0, 0), (.05, 1)], at=(45, 8))}</g>'
        m.move('fd', period, [(t, (x - 48, y - 10)) for t, (x, y) in path + [(2.66, (48, 10)), (2.74, (35, 14)), (2.8, (22, 18))]]
               + [(2.84, (-99, 0))])  # caught: it rides the tongue back, then it is gone
        tongue = [{(round(22 + (x - 22) * i / 40) + dc, round(18 + (y - 18) * i / 40) + dr): p['colors']['T']
                   for i in range(41) for dc in (0, 1) for dr in (0, 1)} for x, y in ((35, 14), (48, 10))]
        props += flip('tg', [{}, *tongue], period, [(0, 0), (2.62, 1), (2.66, 2), (2.74, 1), (2.8, 0)])
    elif action == 'feed':  # the food drops in front of the pet, which leans down and eats it in three bites
        poses = [(0, 'rest', (0, 0)), (.9, 'in', (0, -1)), (1.2, 'rest', (0, 0)), (1.3, 'crouch', (0, 5)), (1.38, 'crouch', (0, 8)),
                 (1.46, 'crouch', (0, 10))]
        mouth = [(0, 'shut')]
        for b in (1.6, 2.6, 3.6):
            poses += [(b, 'crouch', (0, 11)), (b + .1, 'crouch', (0, 12)), (b + .22, 'crouch', (0, 10))]
            mouth += [(b, 'open'), (b + .22, 'shut')]
            for i in range(4):  # chewing
                poses.append((b + .36 + .14 * i, 'crouch', (0, 11 - i % 2)))
                mouth.append((b + .36 + .14 * i, 'shut' if i % 2 else 'open'))
        poses += [(4.5, 'crouch', (0, 7)), (4.58, 'rest', (0, 3)), (4.66, 'rest', (0, 1)), (4.74, 'rest', (0, 0))] + breaths(5.8, period)
        mouth += [(4.9, 'lick'), (5.05, 'shut'), (5.2, 'lick'), (5.4, 'shut')]
        happy = [(0, 0), (4.95, 1), (5.7, 0)]
        face = (period, [(0, (0, 0)), (.3, (1, 1)), (.9, (0, 0)), (1.3, (0, 1)), (4.6, (0, 0)), (5, (0, -1)), (5.6, (0, 0)),
                         (6.8, (2, 0)), (7.9, (0, 0)), (8.6, (-2, 0)), (9.3, (0, 0))])
        food, colors = FOOD[p['food']]
        bites = [lit(doubled(grid(0, f), 9, 5), colors) for f in food] + [{}]
        props += f'<g class="fd">{flip("ff", bites, period, [(0, 0), (1.82, 1), (2.82, 2), (3.82, 3)], at=(13, 37))}</g>'
        m.move('fd', period, [(0, (0, -56))] + [(t, (0, y)) for t, y in hop(-.6, 1.2, 56)[1] if t > 0]  # falling from above, a bounce
               + [(.62, (0, -3)), (.67, (0, -4)), (.72, (0, -3)), (.8, (0, 0))])
    elif action == 'pet':  # eyes shut with pleasure, leaning into three strokes, purring, hearts
        poses = [(0, 'rest', (0, 0)), (.25, 'in', (0, -1))]
        for s in (.45, 1.35, 2.25):
            poses += [(s, 'rest', (0, 1)), (s + .15, 'rest', (-1, 2)), (s + .45, 'rest', (-1, 1)), (s + .7, 'rest', (0, 0))]
        poses += [(3.3, 'rest', (1, 0)), (3.38, 'rest', (-1, 0)), (3.46, 'rest', (1, 0)), (3.54, 'rest', (0, 0))] + breaths(3.8, period)
        happy = [(0, 0), (.35, 1), (3.2, 0)]
        px = [(0, (0, 0))] + [(t0 + .07 * i, (i % 2, 0)) for t0 in (.6, 1.5, 2.4) for i in range(9)]  # the purr, in bursts
        face = (period, [(0, (0, 0)), (.25, (0, -1)), (.45, (0, 0)), (5.2, (2, 0)), (6.4, (0, 0)), (7.3, (-2, 0)), (8.1, (0, 0))])
        heart = {(c, r): {'R': p['accent'], 'H': shaded(p['accent'], 1.6)}[k] for r, ln in enumerate(HEART) for c, k in enumerate(ln) if k != '.'}
        for i, (t0, x, y) in enumerate(((.6, 44, 16), (1.4, 50, 12), (2.2, 43, 9))):
            props += f'<g class="h{i}">{draw(heart, x, y)}</g>'
            m.move(f'h{i}', period, [(0, (0, 0))] + [(t0 + .13 * k, ((k // 3) % 2 * (1 if i % 2 else -1), -k)) for k in range(14)]
                   + [(t0 + 1.82, (0, 0))])
            m.fade(f'h{i}', period, [(0, 0), (t0, 1), (t0 + 1.1, .6), (t0 + 1.4, .3), (t0 + 1.7, 0)])
    elif action == 'play':  # a ball bouncing beside the pet, which watches it and jumps after it, small then big
        poses = [(0, 'rest', (0, 0)), (.5, 'in', (0, -1)), (1, 'rest', (0, 0)),
                 (1.25, 'crouch', (0, 3)), (1.5, 'stretch', (0, -2)), (1.6, 'rest', (0, 0)), (2, 'land', (0, 4)), (2.1, 'crouch', (0, 3)),
                 (2.18, 'rest', (0, 0)), (2.6, 'in', (0, -1)), (3.1, 'rest', (0, 0)),
                 (3.3, 'crouch', (0, 3)), (3.85, 'stretch', (0, -2)), (3.95, 'rest', (0, 0)), (4.45, 'land', (0, 4)), (4.55, 'crouch', (0, 3)),
                 (4.63, 'rest', (0, 0)), (5.5, 'in', (0, -1)), (6.2, 'rest', (0, 0))]
        py = [(0, (0, 0))] + [(t, (0, y)) for t, y in hop(1.5, .5, min(5, jump))[1] + hop(3.85, .6, jump)[1]]
        px = [(0, (0, 0)), (3.4, (1, 0)), (3.48, (0, 0)), (3.56, (-1, 0)), (3.64, (0, 0)), (3.72, (1, 0)), (3.8, (0, 0))]  # a wiggle first
        happy = [(0, 0), (4.6, 1), (5.2, 0)]
        face = (1.1, [(0, (2, 1)), (.2, (2, 0)), (.38, (2, -1)), (.72, (2, 0)), (.9, (2, 1))])  # following the ball
        ball = lit(doubled(grid(0, BALL), 6, 6), {'Y': '#FFD866', 'R': RED})
        spins = [ball]
        for _ in range(3):  # a quarter turn at a time
            spins.append({(11 - r, c): v for (c, r), v in spins[-1].items()})
        props += (f'<g class="bl"><g class="bs">{flip("bn", spins, .56, [(0, 0), (.14, 1), (.28, 2), (.42, 3)], at=(55, 34))}</g>'
                  f'<g class="bq">{draw(bent(ball, 7, -2, 2, 6), 55, 34)}</g></g>')  # squashed as it hits the floor
        m.move('bl', 1.1, [(t, (0, y)) for t, y in hop(0, 1.1, 16)[1]])
        m.fade('bs', 1.1, [(0, 0), (.06, 1)])
        m.fade('bq', 1.1, [(0, 1), (.06, 0)])
        hide.append('bq')
    else:  # choose: the pet hops in from the left, lands, and shows off
        x0 = -64
        px, py, poses = [(0, (x0, 0))], [(0, (0, 0))], [(0, 'crouch', (0, 3))]
        for t0, xa, xb in ((.12, x0, x0 * 2 // 3), (.66, x0 * 2 // 3, x0 // 3), (1.2, x0 // 3, 0)):
            xs, ys = hop(t0, .4, min(6, jump), xa, xb)
            px += [(t, (x, 0)) for t, x in xs]
            py += [(t, (0, y)) for t, y in ys]
            poses += [(t0 - .1, 'crouch', (0, 3)), (t0, 'stretch', (0, -2)), (t0 + .08, 'rest', (0, 0)), (t0 + .4, 'land', (0, 4)),
                      (t0 + .48, 'crouch', (0, 3)), (t0 + .54, 'rest', (0, 0))]
        poses += [(1.95, 'in', (0, -1)), (2.4, 'rest', (0, 0))]
        happy = [(0, 0), (1.95, 1), (2.5, 0)]
        face = (period, [(0, (2, 0)), (1.7, (0, 0))])
        star = {(c, r): {'C': p['accent'], 'W': '#FFFFFF'}[k] for r, ln in enumerate(SPARKLE) for c, k in enumerate(ln) if k != '.'}
        for i, (t0, x, y) in enumerate(((1.9, -3, 10), (2, 46, 2), (2.1, 48, 24))):
            props += f'<g class="s{i}">{draw(star, x, y)}</g>'
            m.fade(f's{i}', period, [(0, 0), (t0, 1), (t0 + .3, .5), (t0 + .45, 0)], once=True, fill='both')
    entrance = dict(once=True) if once else {}
    used = sorted({v for _, v, _ in poses} | ({'rest', 'in'} if once else set()), key=list(POSES).index)
    if once:  # first the clocks the pet keeps after its entrance: the entrance's own tracks come later and win while it plays
        idle = breaths(0, 3.6)
        m.show('bd', range(len(used)), 3.6, [(t, used.index(v)) for t, v, _ in idle])
        m.move('hd', 3.6, [(t, o) for t, _, o in idle])
        if 'flippers' in p:
            m.move('sd', 3.6, [(t, (0, -POSES[v][0])) for t, v, _ in idle])
        gaze(*LOOK)
    # the pet, back to front
    svg = ''
    if a['tail']:
        wag = p['wag'] if action != 'sleep' else [(b * 2, h * 3, n) for b, h, n in p['wag']]  # lazier asleep
        seq, span = swing(len(a['tail']), wag)
        tail = flip('tl', a['tail'], span, seq)
        svg += f'<g class="sd">{tail}</g>' if 'flippers' in p else tail  # flippers ride the shoulders, a tail stays put
    svg += flip('bd', [a['body'][v] for v in used], period, [(t, used.index(v)) for t, v, _ in poses], **entrance)
    if a['sac']:
        svg += flip('sc', [{}, *a['sac']], *((period, sac) if sac else CROAK))
    head = flip('er', a['ears'], *TWITCH) if a['ears'] and not p.get('front_ears') else ''
    head += draw(a['head'])
    if a['ears'] and p.get('front_ears'):
        head += flip('er', a['ears'], *TWITCH)
    said = {v for _, v in mouth} if mouth else {'shut', 'sniff'}  # sniffing is the bunny's idle
    mouths = [k for k in a['mouth'] if k in said]  # 'shut' first: the mouth when nothing moves
    clock, chew = (period, mouth) if mouth else SNIFF if 'sniff' in mouths else (1, [(0, 'shut')])
    face_svg = draw(a['face']) + draw(a['eyes']) + flip('mo', [a['mouth'][k] for k in mouths], clock,
                                                        [(t, mouths.index(v)) for t, v in chew])
    if action == 'sleep':
        face_svg += draw(a['lids'][1])
    else:
        face_svg += flip('ld', [{}, *a['lids']], *BLINK)
    if happy:
        face_svg += f'<g class="hp">{draw(a["happy"])}</g>'
        m.fade('hp', period, happy, once=once, fill='both')
        if action != 'pet':
            hide.append('hp')
    sleepy = f' transform="translate(0 {pn.px(1)})"' if action == 'sleep' else ''  # asleep, the face droops
    head += f'<g clip-path="url(#pf)"><g class="fc"{sleepy}>{face_svg}</g></g>'
    svg += f'<g class="hd">{head}</g>'
    m.move('hd', period, [(t, o) for t, _, o in poses], **entrance)
    if 'flippers' in p:
        m.move('sd', period, [(t, (0, -POSES[v][0])) for t, v, _ in poses], **entrance)
    if face:
        gaze(*face, **(entrance if face[0] == period else {}))
    elif action != 'sleep':
        gaze(*LOOK)
    # its shadow on the floor shrinks as it rises
    shadow = [{(c, 47): '#1E1813' for c in range(22 - w, 22 + w)} for w in (17, 12, 7)]
    svg = flip('sh', shadow, period, [(t, 0 if y == 0 else 1 if y >= -3 else 2) for t, (_, y) in py or [(0, (0, 0))]], **entrance) + \
        f'<g class="py">{svg}</g>'
    for cls, seq in (('py', py), ('px', px)):
        if seq:
            m.move(cls, period, seq, **entrance)
    clip = f'<clipPath id="pf"><path d="{pn.runs([(c + cx, r + cy) for c, r in a["head"]])}"/></clipPath>'
    style = (','.join(f'.{c}' for c in hide) + '{opacity:0}' if hide else '') + m.css()
    return f'{clip}<g class="px">{svg}</g>{props}', style


def pet_panel(state=None, now=None):
    """The live top of the pet card, laid out like a project card: the pet, its copy and a stats box. One image,
    served by api/pet.py: it loads below the fold, where its arrival moves nothing in view. The buttons below it
    are static, see pet_controls."""
    state, now = state or pet_state(), now or dt.datetime.now(dt.timezone.utc)
    last = state['last']
    awake = last and now - dt.datetime.fromisoformat(last['at']) <= dt.timedelta(days=2)
    kind = state['chosen'] if state['chosen'] in PETS else 'cat'
    pet, name = PETS[kind], PETS[kind]['name']
    pn, left = pet_card(), 76
    scene, css = pet_scene(kind, last['action'] if awake else 'sleep')  # the same for every view of this state: cached
    verb, when = visit_verb(last), last and ago(last['at'], now)
    did = {'feed': 'FED', 'pet': 'PETTED', 'play': 'PLAYED', 'choose': 'PICKED'}[last['action']] if last else ''  # the pet's name is the title
    foot = f'LAST VISITOR: {did} · {when}' if last else 'NO VISITORS YET. BE THE FIRST!'
    info = card_text(name, f"PROFILE {pet['noun']}", foot, ['A PIXEL PET LIVING ON THIS PROFILE.', 'TAP A BUTTON OR SWITCH PET BELOW:',
                                                          f'THE PAGE RELOADS AND {name} REACTS.'], None, left, pet['accent'], screen=229)
    mood, mood_color = ('HAPPY', pet['accent']) if awake else ('ASLEEP', MUTED)
    info |= text('MOOD', 232, 7, MUTED, '3x5') | text(mood, 283, 7, mood_color, '3x5', anchor='end') | hline(229, 285, 14, RULE)
    place = last['where'] if last else 'NO VISITORS'
    if text_width(place, '3x5') > 47 and ', ' in place:  # 47 LEDs after the pin: a long city drops the country first
        place = place.split(', ')[0]
    while text_width(place, '3x5') > 47:
        place = place[:-1].rstrip(' ,')
    info |= hline(229, 285, 44, RULE) | sprite(['CCC', 'C.C', 'CCC', '.C.', '.C.'], {'C': pet['accent']}, 232, 47) | text(place, 283, 47, CREAM, '3x5', anchor='end')
    for i, (key, label, done, icon, color) in enumerate(ACTIONS):
        info |= text(done, 232, 19 + i * 9, color, '3x5') | text(str(min(state[key], 9999)), 283, 17 + i * 9, CREAM, anchor='end')
    Name = name.capitalize()
    visit = (f"Last visit: someone from {last['where'].title()} {verb.lower().replace(name.lower(), Name)}, {when.lower()}."
             if last else 'No visits yet.')
    summary = (f"{Name}, an interactive pixel-art {pet['noun'].lower()}. Fed {state['feed']} times, petted {state['pet']} times, "
               f"played with {state['play']} times. {visit}")
    art_ = pn.draw(hline(6, 72, 53, RULE)) + scene + pn.draw(info)  # the floor first: the pet's shadow falls on it
    return columns(pn, [], [summary], art_, css, bottom=PET_CUT)[0]


def pet_button(i, pressed=False):
    """Feed, Pet or Play (ACTIONS[i]) in its third of the pet card, 6 LEDs clear of the cuts: dim fill,
    brighter edge. Pressed, it sinks a LED and lights up: api/act.py shows that as the click."""
    key, label, done, icon, color = ACTIONS[i]
    a, b = [(6, 88), (101, 188), (201, 286)][i]
    top = 65 if pressed else 64
    fill, edge = (.36, 1) if pressed else (.14, .5)
    cells = {(c, r): hexc(mix(rgb(BG), rgb(color), edge if c in (a, b) or r in (top, top + 14) else fill))
             for c in range(a, b + 1) for r in range(top, top + 15) if not (c in (a, b) and r in (top, top + 14))}
    x = a + (b - a + 1 - (15 + text_width(label))) // 2
    shine = hexc(mix(rgb(color), (255, 255, 255), .6))
    cells |= sprite(ICONS[icon or 'bowl'], {'C': color, 'L': shine}, x, top + 4) | text(label, x + 15, top + 4, CREAM)
    return cells | sprite(ICONS['reload'], {'C': color}, b - 9, top + 4)  # at the button's end, like the links' arrows: this click reloads


def head_tile(i):
    """The switch's tile for the i-th pet, one per slice of the pet card: (centre LED column, half width).
    Six pets make sixths of 150 px, cut between LEDs."""
    pn, n = pet_card(), len(PETS)
    cols = pn.width / n / pn.p
    return round((pn.width / n * (i + .5) - pn.x) / pn.p), int(cols // 3)


def pet_head(i, pressed=False):
    """The switch's tile for the i-th pet in its slice of the pet card: its head at grid size, lit like the
    pet, with its small face, cropped to the head. Pressed, the tile lights up in the pet card's pink."""
    other = PETS[list(PETS)[i]]
    (c, half), h = head_tile(i), other['tile']
    tone, edge, fill = (PET, .7, .16) if pressed else (MUTED, .35, .03)
    cells = {(x, r): hexc(mix(rgb(BG), rgb(tone), edge if x in (c - half, c + half) or r in (84, 102) else fill))
             for x in range(c - half, c + half + 1) for r in range(84, 103) if not (x in (c - half, c + half) and r in (84, 102))}
    ears = grid(*other['ears']) if 'ears' in other else {}
    keys = grid(*other['body']) | ({} if other.get('front_ears') else ears) | grid(*other['head'])
    keys |= ears if other.get('front_ears') else {}
    colors = other['colors'] | {k.lower(): v for k, v in other['colors'].items()}
    return cells | {(c - 11 + x, 101 - h + r): v for (x, r), v in lit({q: k for q, k in keys.items() if q[1] < h}, colors).items()}


def pet_press(do, kind=None):
    """The click on a pet button, played back by api/act.py before it returns to the profile: the button
    as it is on the card, then pressed, with what it did. Reduced motion shows it pressed straight away."""
    if do == 'choose':
        i = list(PETS).index(kind)
        (c, half), up, down = head_tile(i), pet_head(i), pet_head(i, True)
        c0, r0, c1, r1 = c - half, 84, c + half, 102
        name = PETS[kind]['name']
        said, color = f'{name} ON STAGE', PETS[kind]['accent']
    else:
        i = [a[0] for a in ACTIONS].index(do)
        up, down = pet_button(i), pet_button(i, True)
        (c0, c1), (r0, r1) = [(6, 88), (101, 188), (201, 286)][i], (64, 79)
        said, color = {'feed': 'FED!', 'pet': 'PETTED!', 'play': 'PLAYED!'}[do], ACTIONS[i][4]
    pad = 8
    w = max(c1 - c0 + 1, text_width(said)) + 2 * pad
    pn = Panel(w, (r1 - r0 + 1) + 34, width=w * 3 + 30)
    dc, dr = (w - (c1 - c0 + 1)) // 2 - c0, 18 - r0  # the button, centred under the message

    def at(cells):
        return pn.draw({(c + dc, r + dr): v for (c, r), v in cells.items()})
    plus = text('+1', (w + c1 - c0 + 1) // 2 - text_width('+1'), 10, color) if do != 'choose' else {}  # over the button's right end
    body = (pn.draw(text(said, (w - text_width(said)) // 2, 6, color)) + f'<g class="up">{at(up)}</g><g class="down">{at(down)}</g>'
            + f'<g class="plus">{pn.draw(plus)}</g>'
            + pn.draw(text('BACK TO THE PROFILE...', (w - text_width('BACK TO THE PROFILE...', '3x5')) // 2, dr + r1 + 6, MUTED, '3x5')))
    style = (f'.up{{opacity:0;animation:up .8s step-end both}}@keyframes up{{0%{{opacity:1}}18%,100%{{opacity:0}}}}'
             f'.down{{animation:down .8s step-end both}}@keyframes down{{0%{{opacity:0}}18%,100%{{opacity:1}}}}'
             f'.plus{{animation:plus .8s steps(5) both}}@keyframes plus{{0%,18%{{opacity:0;transform:translateY({pn.px(5)}px)}}'
             f'19%{{opacity:1;transform:translateY({pn.px(5)}px)}}100%{{opacity:1;transform:none}}}}')
    return pn.svg(said.replace('!', '').capitalize(), body, style)


def pet_controls():
    """The bottom of the pet card: Feed, Pet and Play, one per third, then the switch with every pet's
    head, one per fifth. They look the same for every visitor, so build_all writes them to the repo
    and they load with the other static panels: only the scene above them waits for api/pet.py.
    README.md links each slice to api/act.py."""
    pn, info = pet_card(), {}
    for i in range(len(ACTIONS)):
        info |= pet_button(i)
    alts = ['Feed the profile pet: the page reloads and it eats.', 'Pet it: the page reloads and it purrs.',
            'Play with it: the page reloads and it plays.']
    picks = []
    for i, (k, other) in enumerate(PETS.items()):  # the switch: each head in its fifth
        info |= pet_head(i)
        n = other['name'].capitalize()
        picks.append(f"Switch to {n} the {other['noun'].lower()}: the page reloads with {n} on stage.")
    body = pn.draw(info)
    return slices(pn, alts, body, top=PET_CUT, bottom=81) + slices(pn, picks, body, top=81)


def drums(pn, n, col, row, count=7, w=11, h=15, gap=2):
    """A mechanical counter showing n: drums that roll up from n - 1 when the image loads, the units drum
    red like an old dashboard's, dashes when n is None. Returns (cells, reels, css)."""
    new = '-' * count if n is None else f'{n % 10 ** count:0{count}d}'
    old = new if n is None else f'{(n - 1) % 10 ** count:0{count}d}'
    cells, reels = {}, ''
    glyph_w = len(art_data()['counter']['0'][0])
    for i, (a, b) in enumerate(zip(old, new)):
        x = col + i * (w + gap)
        tone = RED if i == count - 1 else CREAM
        cells |= {(x + c, row + r): hexc(mix(rgb(BG), rgb(tone), (.1 if tone == RED else .05) + .16 * math.sin(math.pi * (r + .5) / h)))
                  for r in range(h) for c in range(w)}  # brighter across the middle, like a lit cylinder
        dx, dy = x + (w - glyph_w) // 2, row + (h - 9) // 2  # the digit, centred on its drum
        if a == b:
            cells |= big(b, dx, dy, CREAM)
            continue
        # The new digit sits in place, the old one a drum-height above; the reel starts a drum lower and
        # rolls up, so with reduced motion the new digit simply shows.
        reels += (f'<clipPath id="drum{i}"><rect {pn.box(x, row, w, h)}/></clipPath><g clip-path="url(#drum{i})">'
                  f'<g class="roll">{pn.draw(big(b, dx, dy, CREAM) | big(a, dx, dy - h, CREAM))}</g></g>')
    css = f'.roll{{animation:roll .8s 1s steps({h}) backwards}}@keyframes roll{{from{{transform:translateY({pn.px(h)}px)}}}}' if reels else ''
    return cells, reels, css


# --- entry points -----------------------------------------------------------------------

DIGITS = '0123456789abcdefghijklmnopqrstuvwxyz'


def import_art(avatar, lift_icon):
    from PIL import Image, ImageEnhance

    def grid(im, size, colors):
        im = im.convert('RGB').resize((size, size), Image.LANCZOS).quantize(colors).convert('RGB')
        palette = sorted({hexc(im.getpixel((x, y))) for y in range(size) for x in range(size)})
        rows = [''.join(DIGITS[palette.index(hexc(im.getpixel((x, y))))] for x in range(size)) for y in range(size)]
        return {'w': size, 'h': size, 'palette': palette, 'rows': rows}
    face = Image.open(avatar).convert('RGB')
    w = face.size[0]
    face = face.crop((int(.2 * w), 0, int(.9 * w), int(.7 * w)))  # head and shoulders
    face = ImageEnhance.Contrast(ImageEnhance.Brightness(face).enhance(1.25)).enhance(1.1)
    save_art(avatar=grid(face, 52, 36), lift=grid(Image.open(lift_icon), 24, 5))


def import_titles(font, cap=14, ss=8, levels=1, sf='/System/Library/Fonts/SFNS.ttf'):
    """Titles (JetBrains Mono) and digits (SF), each drawn `ss` times larger, box-filtered to one value per
    LED, then lit only where the glyph covers at least half the LED: no anti-aliasing. The digits: the
    visitor counter's and Cadran's Titan face as the app draws it."""
    from PIL import Image, ImageDraw, ImageFont

    def face(size, weight, path=font, axes=None):
        f = ImageFont.truetype(path, 100)
        f.set_variation_by_axes(axes or [weight])
        f = ImageFont.truetype(path, round(size * ss / (-f.getbbox('H', anchor='ls')[1] / 100)))
        f.set_variation_by_axes(axes or [weight])
        return f

    def rows(s, f, size):  # one row per LED: one blank row, `size` rows of caps, two below
        im = Image.new('L', (math.ceil(f.getlength(s)) + 4 * ss, (size + 3) * ss))
        ImageDraw.Draw(im).text((2 * ss, (size + 1) * ss), s, fill=255, font=f, anchor='ls')
        im = im.crop((im.getbbox()[0] // ss * ss, 0, -(-im.getbbox()[2] // ss) * ss, im.size[1]))
        im = im.resize((im.size[0] // ss, im.size[1] // ss), Image.BOX)
        return [''.join(str(int(im.getpixel((x, y)) >= 128)) for x in range(im.size[0])) for y in range(im.size[1])]
    titles = {}
    for s in TITLES:
        size = TITLE_CAPS.get(s, cap)
        r = rows(s, face(size, 800), size)  # ExtraBold
        titles[s] = {'w': len(r[0]), 'top': 1, 'levels': levels, 'rows': r}
    sets = {}
    f = face(9, 600, sf, [100, 28, 400, 600])  # the counter: SF semibold, whose zero is plain (JetBrains Mono's dot reads as a bar here)
    counter = {d: rows(d, f, 9)[1:10] for d in '0123456789-'}
    w = max(len(g[0]) for g in counter.values())  # one width for all, so a reel can swap them in place
    sets['counter'] = {d: ['0' * ((w - len(g[0])) // 2) + ln + '0' * (w - len(g[0]) - (w - len(g[0])) // 2) for ln in g] for d, g in counter.items()}
    f = face(11, 200, sf, [150, 28, 400, 200])  # SF: width 150 (expanded), optical size, grade, weight 200 (thin)
    titan = {d: rows(d, f, 11)[1:12] for d in '0123456789'}
    w = max(len(g[0]) for g in titan.values())  # one width for all, so a reel can swap them in place
    sets['titan'] = {d: ['0' * ((w - len(g[0])) // 2) + ln + '0' * (w - len(g[0]) - (w - len(g[0])) // 2) for ln in g] for d, g in titan.items()}
    save_art(titles=titles, **sets)


def save_art(**parts):
    path = OUT / 'art.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    path.write_text(json.dumps(data | parts, indent=1) + '\n')


STILL = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)  # static pieces never show a clock: drawn at a fixed time, a
# rebuild changes them only when what they show changes


def build_all():
    IMG.mkdir(exist_ok=True)
    panels = {'github': github, 'links': links}  # hero, the Cadran and Lift bands, and pet are live, see api/
    for name, make in panels.items():
        write(name, make())
    heading, cadran_text, _, lift_copy, _, led_board = projects_card(now=STILL)
    (IMG / 'projects-1.svg').write_text(heading)
    for name, svg in (('projects-2-copy', cadran_text), ('projects-3-copy', lift_copy)):
        (IMG / f'{name}.svg').write_text(svg)
    (IMG / 'projects-4.svg').write_text(led_board)
    greeting, _, im, header = hero()
    for name, svg in (('hero-greeting', greeting), ('hero-im', im), ('hero-body', header)):
        (IMG / f'{name}.svg').write_text(svg)
    controls = pet_controls()
    write('pet-actions', controls[:3])
    write('pet-switch', controls[3:])
    for make in (lambda: hero(1), pet_panel):  # served live by api/, drawn here for the contrast check
        make()
    for kind in PETS:  # api/pet.py draws every scene: each one builds, and bending a body never lifts its feet
        bodies = pet_art(kind)['body'].values()
        assert len({max(r for _, r in b) for b in bodies}) == 1, kind
        for action in (*PET_ACTIONS, 'sleep'):
            pet_scene(kind, action)
    low = {c: round(contrast(c, BG), 2) for c in INK if contrast(c, BG) < 4.5}
    assert not low, f'text below WCAG AA 4.5:1 on {BG}: {low}'
    print(f'{len(panels)} panels; text contrast >= 4.5:1 ({", ".join(f"{c} {contrast(c, BG):.1f}" for c in sorted(INK))})')


if __name__ == '__main__':
    cmd = sys.argv[1:2]
    if cmd == ['art']:
        import_art(sys.argv[2], sys.argv[3])
    elif cmd == ['stats']:
        import_stats()
    elif cmd == ['titles']:
        import_titles(sys.argv[2] if len(sys.argv) > 2 else str(Path.home() / 'Library/Fonts/JetBrainsMono[wght].ttf'))
    else:
        build_all()
