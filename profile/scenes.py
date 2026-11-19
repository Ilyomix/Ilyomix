#!/usr/bin/env python3
"""Draws the nature scenes Glowback's monitor plays on the projects card into art.json (needs Pillow):

    python3 profile/scenes.py [PREVIEW_DIR]

Each scene is drawn ten times larger in a few flat colours of its own palette, then every LED of the 46x26
screen takes the colour most of its 10x10 block has: crisp shapes, no in-between colours, and every colour is
one path in the SVG. build.py lights the wall around the monitor from each scene's edges, see `glowback`.
PREVIEW_DIR gets each scene as LEDs, 8x.
"""
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = Path(__file__).parent
W, H, K = 46, 26, 10  # the screen in LEDs, and how much larger the scenes are drawn
BW, BH = W * K, H * K
DIGITS = '0123456789abcdefghijklmnopqrstuvwxyz'


def lerp(a, b, t):
    t = max(0., min(1., t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(draw, y0, y1, stops):
    """Rows y0 to y1 shaded through `stops`, [(t, rgb)] with t from 0 at y0 to 1 at y1."""
    for y in range(int(y0), int(y1)):
        t = (y - y0) / max(1, y1 - y0 - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t <= t1:
                draw.line([(0, y), (BW, y)], fill=lerp(c0, c1, (t - t0) / ((t1 - t0) or 1)))
                break


def bands(draw, y0, y1, colors):
    """Rows y0 to y1 in flat bands, one per colour, top to bottom: a sky the way pixel art shades it."""
    for i, c in enumerate(colors):
        draw.rectangle([0, y0 + (y1 - y0) * i / len(colors), BW, y0 + (y1 - y0) * (i + 1) / len(colors)], fill=c)


def ridge(seed, base, amp, freq):
    """A skyline: the height of a range of hills at each column, around `base`."""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
    return [base - amp * (.55 * math.sin(x / BW * freq * 2 * math.pi + ph[0]) + .3 * math.sin(x / BW * freq * 4.2 * math.pi + ph[1])
                          + .15 * math.sin(x / BW * freq * 9.5 * math.pi + ph[2])) for x in range(BW + 1)]


def peaks(points):
    """A jagged skyline through (x, y) points in fractions of the scene, as a height per column."""
    pts = [(x * BW, y * BH) for x, y in points]
    out = []
    for x in range(BW + 1):
        (x0, y0), (x1, y1) = next((a, b) for a, b in zip(pts, pts[1:]) if a[0] <= x <= b[0])
        out.append(y0 + (y1 - y0) * (x - x0) / ((x1 - x0) or 1))
    return out


def below(draw, ys, color):
    draw.polygon([(0, BH)] + [(x, ys[x]) for x in range(0, BW + 1, 2)] + [(BW, BH)], fill=color)


def stroke(draw, pts, width, color):
    """A thick line with round ends and joints: the palm's trunk and fronds."""
    draw.line(pts, fill=color, width=round(width), joint='curve')
    for x, y in (pts[0], pts[-1]):
        draw.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=color)


def mountains():
    """An alpine valley in the morning: snowy peaks against the sky, green slopes, pines in front."""
    im = Image.new('RGB', (BW, BH))
    d = ImageDraw.Draw(im)
    bands(d, 0, BH * .62, [(36, 104, 222), (60, 136, 240), (98, 170, 250), (146, 202, 255)])
    d.ellipse([BW * .78, -BH * .26, BW * 1.06, BH * .30], fill=(206, 230, 255))  # the sun and its halo
    d.ellipse([BW * .84, -BH * .14, BW * 1.0, BH * .17], fill=(255, 246, 214))
    sky = peaks([(0, .56), (.07, .42), (.13, .5), (.25, .2), (.33, .36), (.4, .3), (.48, .46), (.6, .24), (.69, .4),
                 (.78, .33), (.88, .5), (1, .42)])
    below(d, sky, (70, 92, 160))
    for x in range(0, BW + 1, 2):
        if sky[x] < BH * .36:  # snow down from each summit, with a ragged edge
            d.line([(x, sky[x]), (x, BH * (.36 + .025 * math.sin(x / 6)))], fill=(240, 246, 255), width=2)
    for px, py, valley in ((.25, .2, .33), (.6, .24, .69)):  # the snow in shade on the tallest peaks' right sides
        d.polygon([(px * BW, py * BH), (valley * BW, sky[int(valley * BW)]), ((px + .04) * BW, BH * .37)], fill=(186, 204, 238))
    below(d, ridge(11, BH * .64, BH * .05, 1.6), (78, 156, 96))  # a meadow
    below(d, ridge(13, BH * .86, BH * .04, 2.4), (40, 112, 70))
    for x, h in ((.03, .5), (.13, .36), (.36, .44), (.47, .3), (.71, .52), (.83, .38), (.97, .46)):  # pines in front, apart
        d.polygon([(x * BW, BH * (1 - h)), (x * BW - h * BH * .3, BH + 4), (x * BW + h * BH * .3, BH + 4)], fill=(16, 64, 40))
    return im


def lagoon():
    """A tropical lagoon: clouds over turquoise water, white surf, sand and a palm leaning in from the right."""
    im = Image.new('RGB', (BW, BH))
    d = ImageDraw.Draw(im)
    hz, shore = int(BH * .42), int(BH * .76)
    bands(d, 0, hz, [(22, 112, 232), (58, 150, 246), (110, 192, 255)])
    for cx, cy, s in ((.10, .14, 1.), (.46, .08, .8), (.66, .26, .6)):  # puffy clouds
        for dx, dy, rr in ((0, 4, 13), (15, -5, 17), (32, 2, 14), (18, 7, 13)):
            x, y, r = cx * BW + dx * s * 1.4, cy * BH + dy * s * 1.4, rr * s * 1.4
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 252, 255))
    bands(d, hz, shore, [(0, 86, 166), (0, 130, 186), (0, 172, 198), (44, 214, 204)])
    d.polygon([(0, shore - 4), (BW, shore - 12), (BW, shore + 4), (0, shore + 12)], fill=(236, 250, 255))  # surf
    d.polygon([(0, shore + 12), (BW, shore + 4), (BW, BH), (0, BH)], fill=(246, 216, 150))
    d.polygon([(0, BH * .93), (BW, BH * .88), (BW, BH), (0, BH)], fill=(226, 188, 120))
    base, crown = (BW * .90, BH + 10), (BW * .76, BH * .30)
    trunk = [(base[0] + (crown[0] - base[0]) * t + 26 * math.sin(t * math.pi), base[1] + (crown[1] - base[1]) * t)
             for t in (i / 12 for i in range(13))]
    stroke(d, trunk, 22, (104, 66, 36))
    for a, length, droop in ((-178, 120, 70), (-150, 110, 40), (-118, 80, 30), (-70, 84, 30), (-34, 110, 50), (-4, 100, 70),
                             (160, 70, 40)):
        r = math.radians(a)
        pts = [(crown[0] + length * t * math.cos(r), crown[1] + length * t * math.sin(r) + droop * t * t) for t in (i / 10 for i in range(11))]
        stroke(d, pts, 20, (16, 104, 56))
    for dx, dy in ((-8, 10), (8, 12)):
        d.ellipse([crown[0] + dx - 8, crown[1] + dy - 8, crown[0] + dx + 8, crown[1] + dy + 8], fill=(84, 52, 26))
    return im


def dunes():
    """Sand dunes under a deep blue sky, each lit on its windward face, its slip face in shadow behind a sharp crest."""
    im = Image.new('RGB', (BW, BH))
    d = ImageDraw.Draw(im)
    bands(d, 0, BH * .56, [(14, 64, 180), (34, 100, 214), (70, 142, 236), (124, 184, 246)])
    below(d, ridge(31, BH * .54, BH * .03, 1.3), (214, 140, 88))  # far dunes in the haze

    def dune(peak, left, right, base, lit, shade, crest_end):
        px, py = peak
        n = 24
        windward = [(left + (px - left) * t, base - (base - py) * math.sin(t * math.pi / 2) ** 1.6) for t in (i / n for i in range(n + 1))]
        lee = [(px + (right - px) * t, py + (base - py) * t ** .7) for t in (i / n for i in range(1, n + 1))]
        d.polygon(windward + lee + [(right, BH), (left, BH)], fill=lit)
        ex, ey = crest_end  # the crest runs from the peak down towards the viewer, an S-curve
        crest = [(px + (ex - px) * t + 40 * math.sin(t * math.pi) * (1 - t), py + (ey - py) * t ** 1.2) for t in (i / n for i in range(n + 1))]
        d.polygon([peak] + lee + [(right, BH), (ex, BH)] + list(reversed(crest)), fill=shade)
    dune((BW * .60, BH * .36), -BW * .2, BW * 1.3, BH * .64, (246, 172, 92), (164, 82, 40), (BW * .74, BH))
    dune((BW * .22, BH * .62), -BW * .5, BW * .80, BH * 1.08, (255, 202, 120), (180, 94, 44), (BW * .34, BH))
    return im


def aurora():
    """The northern lights over dark mountains, mirrored in a still lake."""
    im = Image.new('RGB', (BW, BH))
    d = ImageDraw.Draw(im)
    bands(d, 0, BH * .72, [(4, 8, 24), (8, 16, 40), (12, 30, 60), (22, 70, 92)])  # a teal haze low in the sky
    rnd = random.Random(4)
    for _ in range(16):  # stars, one LED each
        x, y = rnd.randrange(W), rnd.randrange(int(H * .45))
        d.rectangle([x * K, y * K, x * K + K - 1, y * K + K - 1], fill=(206, 218, 255) if rnd.random() > .4 else (118, 136, 200))
    curtain = []
    for x in range(BW + 1):
        yc = BH * (.36 + .1 * math.sin(x / BW * 2 * math.pi * 1.05 + .5) + .03 * math.sin(x / BW * 2 * math.pi * 3.2))
        h = BH * (.17 + .05 * math.sin(x / BW * 2 * math.pi * 2.1 + 1.1))
        curtain.append((yc, h))
    for x in range(0, BW + 1, 2):  # violet above, a bright green core, teal at its foot
        yc, h = curtain[x]
        for (a, b), c in (((-1, -.55), (120, 70, 220)), ((-.55, -.15), (44, 214, 150)), ((-.15, .12), (150, 255, 196)),
                          ((.12, .3), (24, 160, 150))):
            d.line([(x, yc + a * h), (x, yc + b * h)], fill=c, width=2)
    lake = BH * .76
    below(d, peaks([(0, .66), (.1, .56), (.2, .64), (.34, .5), (.46, .62), (.58, .54), (.7, .64), (.84, .52), (1, .62)]), (6, 8, 20))
    d.rectangle([0, lake, BW, BH], fill=(8, 22, 46))
    for x in range(0, BW + 1, 2):  # the curtain mirrored in the lake, on every other LED row: ripples
        yc, h = curtain[x]
        top, bottom = lake + (lake - (yc + .12 * h)) * .3, lake + (lake - (yc - .55 * h)) * .3
        for y in range(int(top), int(bottom) + 1):
            if (y // K) % 2 == 0:
                d.line([(x, y), (x + 1, y)], fill=(30, 150, 110))
    return im


# The scenes in the order they play, each with its palette: every colour the drawing uses, in that order or any.
SCENES = {
    'mountains': (mountains, [(36, 104, 222), (60, 136, 240), (98, 170, 250), (146, 202, 255), (206, 230, 255), (255, 246, 214),
                              (70, 92, 160), (240, 246, 255), (186, 204, 238), (78, 156, 96), (40, 112, 70), (16, 64, 40)]),
    'lagoon': (lagoon, [(22, 112, 232), (58, 150, 246), (110, 192, 255), (250, 252, 255), (0, 86, 166), (0, 130, 186), (0, 172, 198),
                        (44, 214, 204), (236, 250, 255), (246, 216, 150), (226, 188, 120), (104, 66, 36), (16, 104, 56), (84, 52, 26)]),
    'dunes': (dunes, [(14, 64, 180), (34, 100, 214), (70, 142, 236), (124, 184, 246), (214, 140, 88), (246, 172, 92), (164, 82, 40),
                      (255, 202, 120), (180, 94, 44)]),
    'aurora': (aurora, [(4, 8, 24), (8, 16, 40), (12, 30, 60), (22, 70, 92), (206, 218, 255), (118, 136, 200), (120, 70, 220),
                        (44, 214, 150), (150, 255, 196), (24, 160, 150), (6, 8, 20), (8, 22, 46), (30, 150, 110)]),
}


def shrink(im, colors):
    """Every LED takes the colour most of its K x K block has, each pixel first snapped to the palette."""
    pal = Image.new('P', (1, 1))
    flat = [v for c in colors for v in c]
    pal.putpalette(flat + flat[:3] * (256 - len(colors)))
    idx = im.quantize(palette=pal, dither=Image.Dither.NONE)
    px = idx.load()
    out = Image.new('RGB', (W, H))
    for y in range(H):
        for x in range(W):
            votes = Counter(px[x * K + i, y * K + j] for j in range(1, K - 1) for i in range(1, K - 1))
            out.putpixel((x, y), colors[votes.most_common(1)[0][0]])
    return out


def leds(im, k=8):
    """A preview: each pixel as a lit dot, 72 % of the pitch, on the panel's background."""
    out = Image.new('RGB', (im.size[0] * k, im.size[1] * k), (3, 2, 1))
    d, pad = ImageDraw.Draw(out), round(k * .14)
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            d.rounded_rectangle([x * k + pad, y * k + pad, x * k + k - pad - 1, y * k + k - pad - 1], radius=2, fill=im.getpixel((x, y)))
    return out


def main(preview=None):
    path = OUT / 'art.json'
    art = {k: v for k, v in json.loads(path.read_text()).items() if not k.startswith('scene-')}
    for name, (draw, colors) in SCENES.items():
        q = shrink(draw(), colors)
        palette = sorted({'#%02X%02X%02X' % q.getpixel((x, y)) for y in range(H) for x in range(W)})
        rows = [''.join(DIGITS[palette.index('#%02X%02X%02X' % q.getpixel((x, y)))] for x in range(W)) for y in range(H)]
        art[f'scene-{name}'] = {'w': W, 'h': H, 'palette': palette, 'rows': rows}
        if preview:
            leds(q).save(Path(preview) / f'scene-{name}.png')
        print(name, len(palette), 'colours')
    path.write_text(json.dumps(art, indent=1) + '\n')


if __name__ == '__main__':
    main(*sys.argv[1:2])
