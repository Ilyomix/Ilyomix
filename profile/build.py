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
import copy
import datetime as dt
import functools
import json
import math
import re
import sys
from pathlib import Path

OUT = Path(__file__).parent
IMG = OUT / 'img'  # what README.md shows; the SVGs beside build.py belong to the README before ?v=2, until it goes
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


# The LEDs' glow: (filter id suffix, blur radius in LED pitches, the image's display scale at or below which it applies).
# A fixed radius blurs the panels on a phone, where an LED is barely a pixel; media queries inside an <img>'s SVG
# see the size it is shown at, so each image switches by its own scale: slices and full bands stay alike.
BLOOM = (('', .6, None), ('-m', .4, .75), ('-s', .22, .5))


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
        p, dot = self.p, self.p * .72
        vx, vy, vw, vh = view or (0, 0, self.width, self.height)
        inset = (p - dot) / 2
        area, card = self.box(0, 0, self.cols, self.rows), f'width="{self.width}" height="{num(self.height)}"'
        shape, ring = self.edge()
        dots = (f'width="{num(p)}" height="{num(p)}" patternUnits="userSpaceOnUse" x="{num(self.x)}" y="{num(self.y)}"'
                f'><rect x="{num(inset)}" y="{num(inset)}" width="{num(dot)}" height="{num(dot)}" rx="{num(dot * .3)}"')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{num(vx)} {num(vy)} {num(vw)} {num(vh)}" '
                f'width="{num(vw)}" height="{num(vh)}" role="img" aria-label="{title}"><title>{title}</title>'
                f'<defs><pattern id="dot" {dots} fill="#fff"/></pattern><pattern id="off" {dots} fill="{OFF}"/></pattern>'
                f'<mask id="leds" maskUnits="userSpaceOnUse" x="0" y="0" {card}><rect {card} fill="url(#dot)"/></mask>'
                f'<clipPath id="screen"><rect {area}/></clipPath>'
                + ''.join(f'<filter id="bloom{k}" x="-3%" y="-3%" width="106%" height="106%"><feGaussianBlur stdDeviation="{num(p * r)}" result="b"/>'
                          f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' for k, r, _ in BLOOM)
                + f'{defs}</defs><style>{style}'
                + ''.join(f'@media (max-width:{num(vw * at)}px){{.lit{{filter:url(#bloom{k})}}}}' for k, _, at in BLOOM[1:])
                + f'@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>'
                f'<path d="{shape}" fill="#0B0907"/><rect {area} fill="{BG}"/><rect {area} fill="url(#off)"/>'
                f'<g class="lit" filter="url(#bloom)"><g mask="url(#leds)">{self.draw(ring)}</g>'
                f'<g mask="url(#leds)" clip-path="url(#screen)">{body}</g></g></svg>')


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
LEGACY = dict(device=(216, 284), legacy=True)  # what api/ serves without ?v=2: the README before it, pink Cadran, edge strips


SLOTS = [(6, 86), (99, 184), (197, 280)]  # one link per third of a 284-LED panel, 6 LEDs clear of the cuts


def write(name, out):
    """One SVG, or the slices from `slices` as name-1.svg, name-2.svg..."""
    for i, svg in enumerate([out] if isinstance(out, str) else out):
        (IMG / (f'{name}.svg' if isinstance(out, str) else f'{name}-{i + 1}.svg')).write_text(svg)


# --- motion (CSS only) ----------------------------------------------------------------

def frames(name, items, dur):
    """One item visible at a time; reduced motion holds the first one."""
    n = len(items)
    css = (f'.{name}{{opacity:0;animation:{name} {num(dur)}s step-end infinite}}.{name}.k0{{opacity:1}}'
           f'@keyframes {name}{{0%{{opacity:1}}{num(100 / n)}%,100%{{opacity:0}}}}')
    body = ''.join(f'<g class="{name}{" k0" if i == 0 else ""}" style="animation-delay:{num(i * dur / n)}s">{it}</g>'
                   for i, it in enumerate(items))
    return body, css


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


# The profile pets, 26x24 sprites drawn at scale 2. O outline, G fur, S shade or stripes, W cream, P pink,
# K eyes, H eye light, E iris, R collar or scarf, Y bell, tag or beak. `frames` are the two idle poses drawn
# over the body, `shut` the closed eyes; both are {row: (column, run)}, see `layer`. `head` is how many rows
# the switch under the pet card shows.
PETS = {
    'cat': {'name': 'BYTE', 'noun': 'CAT', 'food': 'fish', 'head': 14, 'accent': '#F0A04B',
        'colors': {'O': '#5C2E14', 'G': '#F0A04B', 'S': '#C8692A', 'W': '#FFF1D6', 'P': '#FF9DB4', 'K': '#1A0F0A', 'H': '#FFFFFF', 'R': '#F23645', 'Y': '#FFD866', 'E': '#8BE38F'},
        'body': [
                 '..O............O..',
                 '.OPO..........OPO.',
                 '.OPPO........OPPO.',
                 '.OGPPGOOOOOOGPPGO.',
                 'OGGGGGGSGGSGGGGGGO',
                 'OGGGGGGGSSGGGGGGGO',
                 'OGGGGGGGGGGGGGGGGO',
                 'OGGGGKKGGGGKKGGGGO',
                 'OGGGKHHKGGKHHKGGGO',
                 'OGGGKHKKGGKHKKGGGO',
                 'OGPPGKEGGGGKEGPPGO',
                 '.OGGGGGGPPGGGGGGO.',
                 '..OGGGGWOOWGGGGO..',
                 '...OGGGGGGGGGGO...',
                 '...ORRRRYYRRRRO...',
                 '..OGGGWWYYWWGGGO..',
                 '.OSSGGWWWWWWGGSSO.',
                 '.OGGGGWWWWWWGGGGO.',
                 '.OSSGGGWWWWGGGSSO.',
                 '.OGGGGGGGGGGGGGGO.',
                 '.OGGWWWWGGWWWWGGO.',
                 '..OGWWWWOOWWWWGO..',
                 '...OOOOOOOOOOOO...',
                 ''],
        'frames': [{12: (19, 'OO'), 13: (18, 'OSSO'), 14: (19, 'OGO'), 15: (19, 'OGO'), 16: (19, 'OGO'), 17: (19, 'OGO'), 18: (18, 'OGO'), 19: (17, 'OGO'), 20: (17, 'GO'), 21: (16, 'OO')},
                   {12: (20, 'OO'), 13: (19, 'OSSO'), 14: (20, 'OGO'), 15: (20, 'OGO'), 16: (19, 'OGO'), 17: (19, 'OGO'), 18: (18, 'OGO'), 19: (17, 'OGO'), 20: (17, 'GO'), 21: (16, 'OO')}],
        'shut': {7: (4, 'GGGG..GGGG'), 8: (4, 'KGGK..KGGK'), 9: (4, 'GKKG..GKKG'), 10: (4, 'GGGG..GGGG')}},
    'dog': {'name': 'PIXEL', 'noun': 'DOG', 'food': 'bone', 'head': 12, 'accent': '#E3B47A',
        'colors': {'O': '#4A2A14', 'G': '#E3B47A', 'S': '#9C5F2E', 'W': '#FFF1D6', 'P': '#FF7A9A', 'K': '#1A0F0A', 'H': '#FFFFFF', 'R': '#4C8DFF', 'Y': '#FFD866'},
        'body': [
                 '...OOOOOOOOOOOO...',
                 '..OGGGGGGGGGGGGO..',
                 '.OSOGGGGGGGGGGOSO.',
                 'OSSSOGGGGGGGGOSSSO',
                 'OSSSOGGGGGGGGOSSSO',
                 'OSSSOGHKGGHKGOSSSO',
                 'OSSSOGKKGGKKGOSSSO',
                 'OSSSOGGGWWGGGOSSSO',
                 '.OSSOGGWKKWGGOSSO.',
                 '..OO.OGWWWWGO.OO..',
                 '....OGGWPPWGGO....',
                 '....OGGGPPGGGO....',
                 '...ORRRRYYRRRRO...',
                 '...OGGWWYYWWGGO...',
                 '..OGGGWWWWWWGGGO..',
                 '..OGGGWWWWWWGGGO..',
                 '.OGGGGWWWWWWGGGGO.',
                 '.OGSGGGWWWWGGGSGO.',
                 '.OGSSGGGWWGGGSSGO.',
                 '.OGGGGGGGGGGGGGGO.',
                 '.OGGWWWWGGWWWWGGO.',
                 '..OGWWWWOOWWWWGO..',
                 '...OOOOOOOOOOOO...',
                 ''],
        'frames': [{12: (18, 'OO'), 13: (17, 'OGGO'), 14: (16, 'OGGO'), 15: (16, 'OGO')},
                   {13: (17, 'OOO'), 14: (16, 'OGGGO'), 15: (16, 'OOO')}],
        'shut': {5: (6, 'GG..GG'), 6: (6, 'KK..KK')}},
    'bunny': {'name': 'NIBBLE', 'noun': 'BUNNY', 'food': 'carrot', 'head': 15, 'accent': '#FF8FB0',
        'colors': {'O': '#4E4858', 'G': '#ECE8F4', 'S': '#B8B0C8', 'W': '#FFFFFF', 'P': '#FF9DB4', 'K': '#2A1A2E', 'H': '#FFFFFF', 'R': '#FF8FB0', 'Y': '#FFD866', 'E': '#FF5C8A'},
        'body': [
                 '',
                 '',
                 '',
                 '...OGPO....OPGO...',
                 '...OGPO....OPGO...',
                 '..OOGPOOOOOOPGOO..',
                 '.OGGGGGGGGGGGGGGO.',
                 'OGGGGGGGGGGGGGGGGO',
                 'OGGGGKKGGGGKKGGGGO',
                 'OGGGKHHKGGKHHKGGGO',
                 'OGGGKHKKGGKHKKGGGO',
                 'OGPPGKEGGGGKEGPPGO',
                 '.OGGGGGGPPGGGGGGO.',
                 '..OGGGGWOOWGGGGO..',
                 '...OOGGGGGGGGOO...',
                 '...OGSGWWWWGSGO...',
                 '..OGGSGWWWWGSGGO..',
                 '.OGGGGGWWWWGGGGGO.',
                 '.OGSGGGWWWWGGGSGO.',
                 '.OGGGGGGGGGGGGGGO.',
                 '.OGGWWWWGGWWWWGGO.',
                 '..OGWWWWOOWWWWGO..',
                 '...OOOOOOOOOOOO...',
                 ''],
        'frames': [{0: (3, 'OO........OO'), 1: (3, 'OGO......OGO'), 2: (3, 'OGPO....OPGO'), 17: (16, 'OWWO'), 18: (16, 'OWWWO'), 19: (16, 'OWWO')},
                   {0: (3, 'OO'), 1: (3, 'OGO.......OOOO'), 2: (3, 'OGPO....OPGGGO'), 17: (16, 'OWWO'), 18: (16, 'OWWWO'), 19: (16, 'OWWO')}],
        'shut': {8: (4, 'GGGG..GGGG'), 9: (4, 'KGGK..KGGK'), 10: (4, 'GKKG..GKKG'), 11: (4, 'GGGG..GGGG')}},
    'fox': {'name': 'HEX', 'noun': 'FOX', 'food': 'bone', 'head': 14, 'accent': '#FF7A1F',
        'colors': {'O': '#4A1E0A', 'G': '#FF7A1F', 'S': '#C2500F', 'W': '#FFF1D6', 'P': '#FF9DB4', 'K': '#1A0F0A', 'H': '#FFFFFF', 'R': '#F23645', 'Y': '#FFD866', 'E': '#FFD866'},
        'body': [
                 '.OO............OO.',
                 '.OKO..........OKO.',
                 '.OGKO........OKGO.',
                 '.OGGSOOOOOOOOSGGO.',
                 'OGGGGGGGGGGGGGGGGO',
                 'OGGGGGGGGGGGGGGGGO',
                 'OGGGGGGGGGGGGGGGGO',
                 'OGGGGKKGGGGKKGGGGO',
                 'OGGGKHHKGGKHHKGGGO',
                 'OGGGKHKKGGKHKKGGGO',
                 'OGWWGKEGGGGKEGWWGO',
                 '.OWWWWWWKKWWWWWWO.',
                 '..OWWWWWOOWWWWWO..',
                 '...OOWWWWWWWWOO...',
                 '....OGGWWWWGGO....',
                 '...OGGWWWWWWGGO...',
                 '..OGGGWWWWWWGGGO..',
                 '.OGGGGWWWWWWGGGGO.',
                 '.OGGGGGWWWWGGGGGO.',
                 '.OGGGGGGGGGGGGGGO.',
                 '.OGGSSSSGGSSSSGGO.',
                 '..OGSSSSOOSSSSGO..',
                 '...OOOOOOOOOOOO...',
                 ''],
        'frames': [{11: (19, 'OO'), 12: (18, 'OWWO'), 13: (17, 'OWWWO'), 14: (17, 'OGGGO'), 15: (17, 'OGGGGO'), 16: (17, 'OGGGGO'), 17: (17, 'OGGGGO'), 18: (16, 'OGGGGO'), 19: (16, 'OGGGO'), 20: (16, 'OGGO'), 21: (16, 'OGO')},
                   {12: (20, 'OO'), 13: (19, 'OWWO'), 14: (18, 'OWWWO'), 15: (17, 'OGGGGO'), 16: (17, 'OGGGGO'), 17: (17, 'OGGGGO'), 18: (16, 'OGGGGO'), 19: (16, 'OGGGO'), 20: (16, 'OGGO'), 21: (16, 'OGO')}],
        'shut': {7: (4, 'GGGG..GGGG'), 8: (4, 'KGGK..KGGK'), 9: (4, 'GKKG..GKKG'), 10: (4, 'GGGG..GGGG')}},
    'penguin': {'name': 'SUDO', 'noun': 'PENGUIN', 'food': 'fish', 'head': 11, 'accent': '#8FB2FF',
        'colors': {'O': '#1C2033', 'G': '#4A5578', 'S': '#323A58', 'W': '#F4F6FF', 'P': '#FF9DB4', 'K': '#141624', 'H': '#FFFFFF', 'R': '#F23645', 'Y': '#FFB02E'},
        'body': [
                 '',
                 '......OOOOOO......',
                 '....OOGGGGGGOO....',
                 '...OGGGGGGGGGGO...',
                 '..OGGGGGGGGGGGGO..',
                 '..OGGWWWGGWWWGGO..',
                 '..OGWWHKWWHKWWGO..',
                 '..OGWWKKWWKKWWGO..',
                 '..OGWWWWYYWWWWGO..',
                 '..OGGWWYYYYWWGGO..',
                 '...OGGWWWWWWGGO...',
                 '...ORRRRRRRRRRO...',
                 '..OGRRWWWWWWWGGO..',
                 '.OSGRRWWWWWWWWGGO.',
                 'OSSGGWWWWWWWWWGGO.',
                 'OSSGGWWWWWWWWWGGO.',
                 'OSSGGWWWWWWWWWGGO.',
                 '.OSGGWWWWWWWWWGGO.',
                 '..OGGWWWWWWWWWGGO.',
                 '..OGGGWWWWWWWGGGO.',
                 '...OGGGWWWWWGGGO..',
                 '....OOOOOOOOOOO...',
                 '...OYYYO...OYYYO..',
                 ''],
        'frames': [{13: (16, 'O'), 14: (16, 'SO'), 15: (16, 'SSO'), 16: (16, 'SSO'), 17: (16, 'SO')},
                   {11: (17, 'OO'), 12: (16, 'OSSO'), 13: (16, 'SSO'), 14: (16, 'SO')}],
        'shut': {6: (6, 'WW..WW'), 7: (6, 'KK..KK')}},
    'frog': {'name': 'PING', 'noun': 'FROG', 'food': 'fly', 'head': 10, 'accent': '#6FD36B',
        'colors': {'O': '#173A12', 'G': '#6FD36B', 'S': '#3C9A38', 'W': '#E6F5C4', 'P': '#FF9DB4', 'K': '#0E1A0A', 'H': '#FFFFFF', 'R': '#F23645', 'Y': '#FFD866', 'E': '#F5D547'},
        'body': [
                 '..OOOO......OOOO..',
                 '.OWHWWO....OWHWWO.',
                 '.OWKKWO....OWKKWO.',
                 '.OWKKWOOOOOOWKKWO.',
                 'OGOWWOGGGGGGOWWOGO',
                 'OGGOOGGGGGGGGOOGGO',
                 'OGGGGGGGGGGGGGGGGO',
                 'OGPPGGGGGGGGGGPPGO',
                 'OGGGOOOOOOOOOOGGGO',
                 '.OGGGGGGGGGGGGGGO.',
                 '..OOGGGGGGGGGGOO..',
                 '...OGGWWWWWWGGO...',
                 '..OGGWWWWWWWWGGO..',
                 '.OGSGWWWWWWWWGSGO.',
                 '.OGSGWWWWWWWWGSGO.',
                 'OGGSGGWWWWWWGGSGGO',
                 'OGGGSGGWWWWGGSGGGO',
                 'OGGGGSGGGGGGSGGGGO',
                 '.OGGGGGGGGGGGGGGO.',
                 'OGSGOGGGOOGGGOGSGO',
                 'OGGGGOOO..OOOGGGGO',
                 '.OOOO........OOOO.',
                 ''],
        'frames': [{9: (5, 'GGGGGGGG')}, {9: (5, 'OWWWWWWO'), 10: (4, 'OWWWWWWWWO')}],  # the throat puffs to croak
        'shut': {1: (2, 'GGGG......GGGG'), 2: (2, 'OOOO......OOOO'), 3: (2, 'GGGG......GGGG')}},
}


def layer(spec):
    """Sprite rows from {row: (column, run)}: a pose or a face drawn over a pet's body."""
    return ['.' * spec[r][0] + spec[r][1] if r in spec else '' for r in range(max(spec) + 1)]


def compose(*layers, w=26, h=24):
    """Sprite layers flattened, later ones on top."""
    grid = [['.'] * w for _ in range(h)]
    for rows in layers:
        for r, line_ in enumerate(rows[:h]):
            for c, k in enumerate(line_[:w]):
                if k != '.':
                    grid[r][c] = k
    return [''.join(row) for row in grid]


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
HEART = ['.R.R.', 'RRRRR', 'RRRRR', '.RRR.', '..R..']
FISH = [['..BBB...B', '.BBBBB.BB', 'B.BBBBBBB', '.BBBBB.BB', '..BBB...B'],
        ['....B...B', '...BB.BB.', '..BBBBBBB', '...BB.BB.', '....B...B'],
        ['.........', '.W.W.W..W', 'WWWWWWWWW', '.W.W.W..W', '.........']]
BONE = [['WW.....WW', 'WWWWWWWWW', '.WWWWWWW.', 'WWWWWWWWW', 'WW.....WW'],
        ['WW.......', 'WWWWW....', '.WWWW....', 'WWWWW....', 'WW.......'],
        ['.........', '.........', '.W...W..W', '...W.....', '.........']]
CARROT = [['......L.L', '..CCCCCL.', 'CCCCCCCLL', '..CCCCCL.', '......L.L'],
          ['......L.L', '.....CCL.', '....CCCLL', '.....CCL.', '......L.L'],
          ['......L.L', '.......L.', '.......LL', '.......L.', '......L.L']]
FLY = [['.WW.WW...', '..WKW....', '.KKKKK...', '..KKK....', '...K.....'],
       ['.W..W....', '..KKW....', '.KKKK....', '..KK.....', '.........'],
       ['.........', '..K......', '.K.K.....', '.........', '.........']]
FOOD = {'fish': (FISH, {'B': '#7EC8FF', 'W': CREAM}), 'bone': (BONE, {'W': CREAM}),
        'carrot': (CARROT, {'C': '#FF8A2A', 'L': '#7BD88F'}), 'fly': (FLY, {'K': '#2A2E33', 'W': '#CFE8FF'})}  # three bites each
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


def projects_card(downloads=None, now=None, only=None, device=DEVICE_LIVE, legacy=False):
    """The projects as one card in four bands: the heading, then Cadran, Lift and LED Board. Each band is
    an image of its own so README.md can link it; api/cadran.py and api/lift.py serve theirs live (the
    download count, the clocks), the build writes the other two. The live bands come as (margin, live
    part), see columns. `only` draws just that band."""
    pn = Panel(284, 32 + 3 * 76)
    heading = (halo(6, 8, 16, 16, CREAM) | projects_mark(6, 8) | outline(6, 8, 16, CREAM)  # 16 LEDs, level with the title and its line
               | title('MY PROJECTS', 32, 8, CREAM) | text('3 APPS SHIPPED · MACOS · IOS · WEB', 32, 19, MUTED, '3x5'))
    makers = [lambda b: ('My projects: three apps shipped, on macOS, iOS and the web.', b.draw(heading), ''),
              lambda b: cadran(b, downloads, now, legacy), lambda b: lift(b, None, now), lambda b: board(b)]
    tops = [0, 32, 108, 184, 260]
    out = []
    for i, make in enumerate(makers):
        if only is None or i == only:
            alt, body, css = make(pn.at_row(tops[i]))
            band = dict(top=tops[i] or None, bottom=tops[i + 1] if i < 3 else None)
            out += columns(pn, device, [alt, alt] + [''] * (len(device) - 1), body, css, **band) if i in (1, 2) else slices(pn, [alt], body, css, **band)
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


def cadran(pn, downloads=None, now=None, legacy=False):
    """Cadran on an iMac desktop: its Titan face on the wallpaper, with the menu bar, folders and dock.
    `downloads` comes live from the counter cadranapp.com keeps (api/cadran.py). `legacy`: the pink look of
    the README before ?v=2, until that README is gone."""
    accent, top, bottom, ink, dock_top, dock_bottom = (
        ('#FF7A9A', (205, 98, 124), (176, 82, 106), (70, 30, 42), (226, 150, 170), (204, 128, 150)) if legacy else
        (CADRAN, (236, 124, 38), (196, 92, 18), (64, 30, 8), (246, 172, 112), (224, 146, 88)))

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
        if downloads and legacy:
            label = f'{downloads:,} DOWNLOADS'
            count = text(label, 252 - text_width(label, '3x5') // 2, 57, accent, '3x5')
        elif downloads:
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


def pet_panel(state=None, now=None, strut=None):
    """The live top of the pet card as (margin, live part), see columns, laid out like a project card: the
    pet, its copy and a stats box. api/pet.py serves the live part; the buttons below it are static, see pet_controls."""
    state, now = state or pet_state(), now or dt.datetime.now(dt.timezone.utc)
    last = state['last']
    awake = last and now - dt.datetime.fromisoformat(last['at']) <= dt.timedelta(days=2)
    kind = state['chosen'] if state['chosen'] in PETS else 'cat'
    pet, name = PETS[kind], PETS[kind]['name']
    pn = pet_card()
    cx, cy, left = 6, 6, 76  # the pet, 52x48 LEDs, level with the title like the icons; its props play in columns 46-72
    poses = [scale2x(compose(pet['body'], layer(f))) for f in pet['frames']]  # whole poses: only one shows at a time
    closed = scale2x(compose(pet['body'], layer(pet['frames'][0]), layer(pet['shut'])))
    lids = {(cx + c, cy + r): pet['colors'][k] for r, line_ in enumerate(closed) for c, k in enumerate(line_)
            if k != poses[0][r][c] and k != '.'}  # the closed eyes, drawn over either pose
    pose, css = frames('pose', [pn.draw(sprite(p_, pet['colors'], cx, cy)) for p_ in poses], 1.2)
    floor = pn.draw(hline(6, 72, 53, RULE))
    action = last['action'] if awake else 'sleep'
    if action in ('pet', 'choose', 'sleep'):  # eyes shut, with pleasure or asleep
        eyes = pn.draw(lids)
    else:
        eyes = f'<g class="blink">{pn.draw(lids)}</g>'
        css += '.blink{opacity:0;animation:blink 4s step-end infinite}@keyframes blink{0%{opacity:0}92%{opacity:1}96%,100%{opacity:0}}'
    up, step = pn.px, 'animation-timing-function:steps(4)'
    css += {  # the pet itself reacts: head down to the food, a happy wiggle, a jump with the ball, slow breaths
        'feed': f'.petbody{{animation:eat .5s step-end infinite}}@keyframes eat{{50%{{transform:translateY({up(2)}px)}}}}',
        'pet': f'.petbody{{animation:wiggle .4s step-end infinite}}@keyframes wiggle{{50%{{transform:translateX({up(1)}px)}}}}',
        'choose': f'.petbody{{animation:wiggle .4s step-end infinite}}@keyframes wiggle{{50%{{transform:translateX({up(1)}px)}}}}',
        'play': (f'.petbody{{animation:jump 1s infinite}}@keyframes jump{{0%,100%{{transform:none;{step}}}'
                 f'50%{{transform:translateY(-{up(8)}px);{step}}}}}'),
        'sleep': f'.petbody{{animation:breathe 3s step-end infinite}}@keyframes breathe{{50%{{transform:translateY({up(1)}px)}}}}',
    }[action]
    if action == 'feed':
        food, colors = FOOD[pet['food']]
        prop, prop_css = frames('food', [pn.draw(sprite(f, colors, 52, 43, 2)) for f in food], 3)
    elif action in ('pet', 'choose'):
        prop = ''.join(f'<g class="heart" style="animation-delay:{i * .8}s">'
                       f'{pn.draw(sprite(HEART, {"R": pet["accent"]}, 46 + i * 8, 12 + (i % 2) * 6, 1))}</g>' for i in range(3))
        prop_css = (f'.heart{{animation:heart 2.4s steps(8) infinite}}'
                    f'@keyframes heart{{from{{transform:translateY({pn.px(8)}px);opacity:1}}to{{transform:none;opacity:0}}}}')
    elif action == 'play':
        prop = f'<g class="ball">{pn.draw(sprite(BALL, {"Y": "#FFD866", "R": RED}, 56, 40, 2))}</g>'
        prop_css = (f'.ball{{animation:ball 1s infinite}}@keyframes ball{{0%,100%{{transform:none;animation-timing-function:steps(6)}}'
                    f'50%{{transform:translateY(-{pn.px(24)}px);animation-timing-function:steps(6)}}}}')
    else:
        prop = ''.join(f'<g class="z" style="animation-delay:{i}s">{pn.draw(text("Z", 46 + i * 6, 14 - i * 5, MUTED, "3x5", 1 + i % 2))}</g>'
                       for i in range(3))
        prop_css = '.z{animation:z 3s step-end infinite}@keyframes z{0%,66%{opacity:1}67%,100%{opacity:0}}'
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
    art_ = floor + f'<g class="petbody">{pose}{eyes}</g>' + prop + pn.draw(info)
    cuts = [] if strut is None else [strut]  # whole: it loads below the fold, where its arrival moves nothing in view
    return columns(pn, cuts, [''] * len(cuts) + [summary], art_, css + prop_css, bottom=PET_CUT)


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
    """The switch's tile for the i-th pet in its slice of the pet card: the head and its first pose, cropped
    to the head. Pressed, the tile lights up in the pet card's pink."""
    other = PETS[list(PETS)[i]]
    c, half, h = head_tile(i) + (other['head'],)
    tone, edge, fill = (PET, .7, .16) if pressed else (MUTED, .35, .03)
    cells = {(x, r): hexc(mix(rgb(BG), rgb(tone), edge if x in (c - half, c + half) or r in (84, 102) else fill))
             for x in range(c - half, c + half + 1) for r in range(84, 103) if not (x in (c - half, c + half) and r in (84, 102))}
    for rows in (other['body'], layer(other['frames'][0])):
        cells |= sprite([ln[:18] for ln in rows[:h]], other['colors'], c - 9, 101 - h)
    return cells


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
