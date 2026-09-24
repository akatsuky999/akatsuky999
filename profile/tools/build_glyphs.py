"""Extract glyph outlines, advances and kerning into small JSON files.

The generator stays dependency-free: it lays text out from these files and
writes every glyph as an SVG path (GitHub serves README images under a CSP
that blocks web fonts). Instances of one variable font share their point
structure, and the pen below never shortens commands, so two weights of the
same glyph can be morphed into each other with SMIL.

Only needed when the fonts change:
    pip install fonttools brotli uharfbuzz
    python profile/tools/build_glyphs.py <dir with the variable woff2/ttf files>
"""
import io
import json
import os
import sys

import uharfbuzz as hb
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

# key: (file, axis location)
FONTS = {
    "display-400": ("bodoni-moda-latin-opsz-italic.woff2", {"wght": 400, "opsz": 40}),
    "display-800": ("bodoni-moda-latin-opsz-italic.woff2", {"wght": 800, "opsz": 40}),
    "text": ("bodoni-moda-latin-opsz-normal.woff2", {"wght": 440, "opsz": 16}),
    "text-italic": ("bodoni-moda-latin-opsz-italic.woff2", {"wght": 440, "opsz": 16}),
    "caps": ("archivo-latin-wdth-normal.woff2", {"wght": 520, "wdth": 125}),
}
CHARS = "".join(chr(c) for c in range(32, 127)) + "·×—–’‘“”…"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")


def num(v):
    return str(int(round(v)))


def mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def path_data(rec):
    """SVG path data with a fixed command vocabulary (M, L, Q, C, Z)."""
    out = []
    for op, args in rec.value:
        if op == "moveTo":
            out.append("M{} {}".format(*map(num, args[0])))
        elif op == "lineTo":
            out.append("L{} {}".format(*map(num, args[0])))
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:  # a contour made only of off-curve points
                offs = pts[:-1]
                start = mid(offs[-1], offs[0])
                out.append("M{} {}".format(*map(num, start)))
                for i, off in enumerate(offs):
                    end = mid(off, offs[i + 1]) if i < len(offs) - 1 else start
                    out.append("Q{} {} {} {}".format(*map(num, off + end)))
                continue
            offs, on = pts[:-1], pts[-1]
            for i, off in enumerate(offs):
                end = mid(off, offs[i + 1]) if i < len(offs) - 1 else on
                out.append("Q{} {} {} {}".format(*map(num, off + end)))
        elif op == "curveTo":
            out.append("C" + " ".join(num(v) for p in args for v in p))
        elif op in ("closePath", "endPath"):
            out.append("Z")
    return "".join(out)


def static(path, loc):
    inst = instancer.instantiateVariableFont(TTFont(path), loc)
    inst.flavor = None
    buf = io.BytesIO()
    inst.save(buf)
    return buf.getvalue()


def build(key, path, loc):
    data = static(path, loc)
    tt = TTFont(io.BytesIO(data))
    cmap, gs, hmtx = tt.getBestCmap(), tt.getGlyphSet(), tt["hmtx"]
    font = hb.Font(hb.Face(data))
    glyphs, kern = {}, {}
    chars = [c for c in CHARS if ord(c) in cmap]
    for ch in chars:
        rec = RecordingPen()
        gs[cmap[ord(ch)]].draw(rec)
        glyphs[ch] = {"a": hmtx[cmap[ord(ch)]][0], "d": path_data(rec)}
    for a in chars:
        for b in chars:
            buf = hb.Buffer()
            buf.add_str(a + b)
            buf.guess_segment_properties()
            hb.shape(font, buf, {"kern": True, "liga": False, "calt": False})
            k = buf.glyph_positions[0].x_advance - glyphs[a]["a"]
            if k:
                kern[a + b] = k
    meta = {"upem": tt["head"].unitsPerEm, "glyphs": glyphs, "kern": kern}
    with open(os.path.join(OUT, f"{key}.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, separators=(",", ":"), ensure_ascii=False)
    print(f"{key}: {len(glyphs)} glyphs, {len(kern)} kerning pairs")


if __name__ == "__main__":
    src = sys.argv[1]
    for key, (fn, loc) in FONTS.items():
        build(key, os.path.join(src, fn), loc)
