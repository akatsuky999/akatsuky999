"""The name card.

The name is set in Bodoni Moda Italic and breathes: each letter swings between
the regular and the heavy weight of the variable font, one after another, so a
slow wave runs through the word. Both weights share their point structure, so
the outlines morph with SMIL; the letters are re-spaced every frame as their
advances change.
"""
from __future__ import annotations

import math

from svg import M, document, num
from typeset import CAPS, DISPLAY, DISPLAY_BOLD, TEXT, TEXT_I, Glyphs, face, width

W, H = 824, 172
NAME = "Akatsuky"
PERIOD = 8.0     # seconds for the wave to pass through a letter and back
STAGGER = .07    # delay between neighbouring letters, as a share of the period
SAMPLES = 80

RESEARCH = "spatio-temporal data, time series analysis, agents and LLMs for science"
TABLE = [("STUDY", ["SEU", "HKUST"]), ("RESEARCH", ["PolyU", "CAIR(HK)"]), ("PLAY", ["shuttle", "dumbbell"])]

# 15 x 15 line icons, drawn at the weight of the text next to them
ICONS = {
    # a shuttlecock in flight: cork, skirt, and the rim seen in perspective
    "shuttle": ("M5.4 11.6H10.6A2.6 2.6 0 0 1 5.4 11.6M5.9 11.6 3.3 3.2M10.1 11.6 12.7 3.2"
                "M3.3 3.2A4.7 1.3 0 1 0 12.7 3.2A4.7 1.3 0 1 0 3.3 3.2M7.3 11.6 6.9 1.9M8.7 11.6 9.1 4.5"
                "M4.4 6.9Q8 8 11.6 6.9"),
    "dumbbell": "M4.8 7.9h6.4M3 4.4h1.8v7H3zM11.2 4.4H13v7h-1.8zM1.5 5.7H3v4.4H1.5zM13 5.7h1.5v4.4H13z",
}
TILT = {"shuttle": 40}


def ease(s: float) -> float:
    """Weight share over one period: 0 -> 1 -> 0, sine-shaped."""
    return .5 - .5 * math.cos(2 * math.pi * s)


def breathing_name(x: float, y: float, size: float, ink: str, accent: str) -> str:
    lo, hi = face(DISPLAY), face(DISPLAY_BOLD)
    k = size / lo.upem
    chars = list(NAME)
    n = len(chars)
    phase = [i * STAGGER for i in range(n + 1)]  # the full stop rides the wave too

    def advance(i, u):
        a0, a1 = lo.glyphs[chars[i]]["a"], hi.glyphs[chars[i]]["a"]
        a = a0 + u * (a1 - a0)
        if i + 1 < n:
            pair = chars[i] + chars[i + 1]
            a += lo.kern.get(pair, 0) + u * (hi.kern.get(pair, 0) - lo.kern.get(pair, 0))
        return a

    xs = [[0.0] * (SAMPLES + 1) for _ in range(n + 1)]
    for s in range(SAMPLES + 1):
        t, acc = s / SAMPLES, 0.0
        for i in range(n):
            xs[i][s] = acc
            acc += advance(i, ease((t - phase[i]) % 1))
        xs[n][s] = acc

    times = ";".join(num(s / SAMPLES, 4) for s in range(SAMPLES + 1))
    spline = ' calcMode="spline" keyTimes="0;.5;1" keySplines=".37 0 .63 1;.37 0 .63 1"'
    letters = []
    for i, ch in enumerate(chars):
        d0, d1 = lo.glyphs[ch]["d"], hi.glyphs[ch]["d"]
        begin = -((1 - phase[i]) % 1) * PERIOD
        slide = ";".join(num(v, 1) for v in xs[i])
        letters.append(
            f'<g><animateTransform attributeName="transform" type="translate" values="{slide}" '
            f'keyTimes="{times}" dur="{num(PERIOD)}s" repeatCount="indefinite"/>'
            f'<path d="{d0}"><animate attributeName="d" values="{d0};{d1};{d0}"{spline} '
            f'dur="{num(PERIOD)}s" begin="{num(begin, 3)}s" repeatCount="indefinite"/></path></g>')
    word = (f'<g transform="translate({num(x)} {num(y)}) scale({k:.5f} {-k:.5f})" fill="{ink}">'
            f'{"".join(letters)}</g>')

    # the full stop: a dot in the accent colour that swells when the wave reaches it
    gap = .07 * size
    cx = ";".join(num(x + k * v + gap, 2) for v in xs[n])
    rs = [size * (.058 + .022 * ease((s / SAMPLES - phase[n]) % 1)) for s in range(SAMPLES + 1)]
    r = ";".join(num(v, 2) for v in rs)
    cy = ";".join(num(y - v, 2) for v in rs)
    dot = (f'<circle cx="{num(x + k * xs[n][0] + gap)}" cy="{num(y - rs[0])}" r="{num(rs[0])}" fill="{accent}">'
           f'<animate attributeName="cx" values="{cx}" keyTimes="{times}" dur="{num(PERIOD)}s" repeatCount="indefinite"/>'
           f'<animate attributeName="cy" values="{cy}" keyTimes="{times}" dur="{num(PERIOD)}s" repeatCount="indefinite"/>'
           f'<animate attributeName="r" values="{r}" keyTimes="{times}" dur="{num(PERIOD)}s" repeatCount="indefinite"/>'
           f"</circle>")
    return word + dot


def icon(name: str, x: float, y: float, color: str) -> str:
    tilt = f" rotate({TILT[name]} 8 8)" if name in TILT else ""
    return (f'<path transform="translate({num(x)} {num(y)}){tilt}" d="{ICONS[name]}" stroke="{color}" '
            f'stroke-width="1.05" stroke-linecap="round" stroke-linejoin="round"/>')


def render(p: dict) -> str:
    g = Glyphs()
    left, right = M + 1, W - M - 1
    body = []

    # masthead
    body.append(g.text("HELLO FROM", left, 21, CAPS, 8.2, p["muted"], tracking=.24))
    body.append(g.text("RESEARCH · CODE · TOOLS", right, 21, CAPS, 8.2, p["faint"], tracking=.24, anchor="end"))
    body.append(f'<path d="M{left} 31.5H{right}" stroke="{p["rule"]}"/>')

    base = 118.0
    body.append(breathing_name(left - 2, base, 58, p["ink"], p["accent"]))

    # a small table, its last row sitting on the name's baseline
    cols = [548.0, 658.0, right - 15]
    for (label, items), cx in zip(TABLE, cols):
        anchor = "end" if label == "PLAY" else "start"
        lx = right if label == "PLAY" else cx
        body.append(g.text(label, lx, 74, CAPS, 7.4, p["faint"], tracking=.22, anchor=anchor))
        for row, item in enumerate(items):
            y = 97 + 21 * row
            if item in ICONS:
                body.append(icon(item, cx - 1, y - 13, p["ink2"]))
            else:
                body.append(g.text(item, cx, y, TEXT, 15, p["ink"]))

    body.append(g.text(RESEARCH, left, 152, TEXT_I, 16, p["ink2"]))
    return document(W, H, "Akatsuky",
                    "Hello from Akatsuky — research, code, tools. Study: SEU, HKUST. Research: PolyU, CAIR(HK). "
                    "Play: badminton, the gym. Working on spatio-temporal data, time series analysis, agents "
                    "and LLMs for science.",
                    "".join(body), defs=g.defs())
