"""Small SVG helpers shared by every plate."""
from __future__ import annotations

import re
from xml.sax.saxutils import escape

M = 7  # side margin, so every plate shares the same left and right edge


def num(v: float, nd: int = 2) -> str:
    s = f"{v:.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def minify(svg: str) -> str:
    svg = re.sub(r">\s+<", "><", svg)
    return re.sub(r"\s{2,}", " ", svg).strip()


def document(w: float, h: float, title: str, desc: str, body: str, defs: str = "", style: str = "") -> str:
    reduce = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    css = f"<style>{style}{reduce}</style>" if style else ""
    return minify(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" '
        f'viewBox="0 0 {num(w)} {num(h)}" fill="none" role="img" aria-labelledby="t d">'
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
        f"<defs>{defs}</defs>{css}{body}</svg>")


def keyframes(name: str, frames: list[tuple[float, str]]) -> str:
    return f"@keyframes {name}{{" + "".join(f"{num(pc, 3)}%{{{rule}}}" for pc, rule in frames) + "}"
