"""Text as outlines.

GitHub serves README images under a CSP that blocks web fonts, so every glyph
is written as an SVG path. Each document carries a small glyph dictionary in
<defs>; a line of text is a group of <use> references, laid out with the
advances and kerning stored in fonts/*.json (see tools/build_glyphs.py).
"""
from __future__ import annotations

import json
import os

from svg import num

HERE = os.path.dirname(os.path.abspath(__file__))

DISPLAY = "display-400"       # Bodoni Moda Italic at display size
DISPLAY_BOLD = "display-800"  # the same, heavy: the name morphs between the two
TEXT = "text"                 # Bodoni Moda at text size
TEXT_I = "text-italic"
CAPS = "caps"                 # Archivo Expanded, set in small capitals


class Face:
    def __init__(self, key: str):
        with open(os.path.join(HERE, "fonts", f"{key}.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        self.key = key
        self.upem = meta["upem"]
        self.glyphs = meta["glyphs"]
        self.kern = meta["kern"]

    def layout(self, text: str, tracking: float = 0.0):
        """[(char, x)] in font units, plus the advance of the whole run."""
        track = tracking * self.upem
        run, x, prev = [], 0.0, None
        for ch in text:
            if ch not in self.glyphs:
                ch = "?"
            if prev is not None:
                x += self.kern.get(prev + ch, 0)
            run.append((ch, x))
            x += self.glyphs[ch]["a"] + track
            prev = ch
        return run, (x - track if run else 0.0)

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        return self.layout(text, tracking)[1] * size / self.upem


_FACES: dict[str, Face] = {}


def face(key: str) -> Face:
    if key not in _FACES:
        _FACES[key] = Face(key)
    return _FACES[key]


def width(text: str, key: str, size: float, tracking: float = 0.0) -> float:
    return face(key).width(text, size, tracking)


class Glyphs:
    """The glyph dictionary of one SVG document."""

    def __init__(self):
        self._ids: dict[tuple[str, str], str] = {}
        self._defs: list[str] = []

    def _ref(self, fc: Face, ch: str) -> str:
        key = (fc.key, ch)
        if key not in self._ids:
            d = fc.glyphs[ch]["d"]
            gid = f"g{len(self._defs)}" if d else ""
            if d:
                self._defs.append(f'<path id="{gid}" d="{d}"/>')
            self._ids[key] = gid
        return self._ids[key]

    def text(self, s: str, x: float, y: float, key: str, size: float, fill: str | None = None,
             tracking: float = 0.0, anchor: str = "start", attrs: str = "") -> str:
        fc = face(key)
        run, adv = fc.layout(s, tracking)
        k = size / fc.upem
        if anchor == "middle":
            x -= adv * k / 2
        elif anchor == "end":
            x -= adv * k
        uses = "".join(f'<use href="#{gid}" x="{num(gx, 0)}"/>'
                       for ch, gx in run if (gid := self._ref(fc, ch)))
        paint = f' fill="{fill}"' if fill else ""
        extra = f" {attrs}" if attrs else ""
        return (f'<g transform="translate({num(x)} {num(y)}) scale({k:.5f} {-k:.5f})"{paint}{extra}>'
                f"{uses}</g>")

    def defs(self) -> str:
        return "".join(self._defs)
