"""The contribution snake.

A greedy agent runs breadth-first search to the nearest uneaten day, steering
around its own body, until the year is cleared. The snake is a single rounded
stroke sliding along that route; the route stays behind as a hairline, so every
day's run leaves a different drawing. At the end the grid refills, week by week.
"""
from __future__ import annotations

from collections import deque

from contrib import Day
from svg import M, document, keyframes, num
from typeset import CAPS, Glyphs

LENGTH = 5          # cells of body
STEP = 0.1          # seconds per cell
PAUSE = 2.6         # quiet time at the end of a loop while the grid refills
MOVES = ((0, -1), (0, 1), (1, 0), (-1, 0))  # finish a week before moving on


def plan(days: list[Day]):
    cols = max(d.col for d in days) + 1
    todo = {(d.col, d.row) for d in days if d.level > 0}
    lo_c, hi_c, lo_r, hi_r = -1, cols, -1, 7

    def inside(c):
        return lo_c <= c[0] <= hi_c and lo_r <= c[1] <= hi_r

    def route(src, goal, blocked):
        prev, q = {src: None}, deque([src])
        while q:
            cur = q.popleft()
            if cur != src and goal(cur):
                out = []
                while cur != src:
                    out.append(cur)
                    cur = prev[cur]
                return out[::-1]
            for dc, dr in MOVES:
                nb = (cur[0] + dc, cur[1] + dr)
                if inside(nb) and nb not in prev and nb not in blocked:
                    prev[nb] = cur
                    q.append(nb)
        return None

    body = deque((-1 - k, 3) for k in range(LENGTH))
    path, eaten = [body[0]], {}

    def advance(cells):
        for cell in cells:
            body.appendleft(cell)
            body.pop()
            path.append(cell)
            if cell in todo:
                todo.discard(cell)
                eaten[cell] = len(path) - 1

    while todo:
        blocked = set(list(body)[1:-1])
        advance(route(body[0], lambda c: c in todo, blocked) or route(body[0], lambda c: c in todo, set()))
    advance(route(body[0], lambda c: c == (hi_c, 3), set(list(body)[1:-1])) or [])
    advance([(hi_c + k, 3) for k in range(1, LENGTH + 3)])
    return path, eaten, cols


def render(days: list[Day], p: dict, total: int) -> str:
    W, H = 824, 146
    g = Glyphs()
    path, eaten, cols = plan(days)
    n = len(path) - 1
    T = n * STEP + PAUSE
    moving = n * STEP / T * 100

    left, right, top = M + 1, W - M - 1, 30.0
    gap = 3.2
    pitch = (right - left + gap) / cols
    cell = pitch - gap

    def corner(c):
        return left + c[0] * pitch, top + c[1] * pitch

    def centre(c):
        x, y = corner(c)
        return x + cell / 2, y + cell / 2

    body, css = [], []
    span = f"{days[0].date:%b %Y} — {days[-1].date:%b %Y}".upper()
    body.append(g.text("CONTRIBUTIONS", left, 17, CAPS, 7.4, p["faint"], tracking=.22))
    body.append(g.text(span, right, 17, CAPS, 7.4, p["faint"], tracking=.22, anchor="end"))

    # the calendar, empty
    empty = "".join(f'<rect x="{num(corner((d.col, d.row))[0])}" y="{num(corner((d.col, d.row))[1])}" '
                    f'width="{num(cell)}" height="{num(cell)}" rx="1.6"/>' for d in days)
    body.append(f'<g fill="{p["lv"][0]}">{empty}</g>')

    # days with work: eaten as the head passes, refilled week by week at the end
    food = []
    for i, d in enumerate(sorted((d for d in days if d.level > 0), key=lambda d: (d.col, d.row))):
        t = eaten[(d.col, d.row)] * STEP / T * 100
        back = moving + (100 - moving) * (.2 + .55 * d.col / max(cols - 1, 1))
        lv = p["lv"][d.level]
        css.append(keyframes(f"e{i}", [(0, f"transform:scale(1);fill:{lv}"), (t, f"transform:scale(1);fill:{lv}"),
                                       (t + .35, f"transform:scale(1.18);fill:{p['accent']}"),
                                       (t + 1.1, f"transform:scale(0);fill:{p['accent']}"),
                                       (back, f"transform:scale(0);fill:{lv}"),
                                       (min(back + 3, 100), f"transform:scale(1);fill:{lv}"),
                                       (100, f"transform:scale(1);fill:{lv}")]))
        x, y = corner((d.col, d.row))
        food.append(f'<rect class="f" style="animation-name:e{i}" x="{num(x)}" y="{num(y)}" width="{num(cell)}" '
                    f'height="{num(cell)}" rx="1.6" fill="{p["lv"][d.level]}"/>')
    css.append(f".f{{transform-box:fill-box;transform-origin:center;animation-duration:{num(T)}s;"
               f"animation-timing-function:ease-in-out;animation-iteration-count:infinite}}")
    body.append("".join(food))

    # the route, revealed behind the head, and the snake: one stroke sliding along it
    d = "M" + "L".join("{} {}".format(*(num(v, 1) for v in centre(c))) for c in path)
    fade = moving + (100 - moving) * .5
    css.append(keyframes("trace", [(0, f"stroke-dashoffset:{n};opacity:1"), (moving, "stroke-dashoffset:0;opacity:1"),
                                   (fade, "stroke-dashoffset:0;opacity:0"), (100, f"stroke-dashoffset:{n};opacity:0")]))
    css.append(keyframes("slide", [(0, f"stroke-dashoffset:{LENGTH}"), (moving, f"stroke-dashoffset:{LENGTH - n}"),
                                   (100, f"stroke-dashoffset:{LENGTH - n}")]))
    css.append(f".trace{{stroke-dasharray:{n} {n};animation:trace {num(T)}s linear infinite}}")
    css.append(f".snake{{stroke-dasharray:{LENGTH} {n + 2 * LENGTH};animation:slide {num(T)}s linear infinite}}")
    clip = (f'<clipPath id="field"><rect x="{num(left - 1)}" y="{num(top - 1)}" width="{num(right - left + 2)}" '
            f'height="{num(7 * pitch)}"/></clipPath>')
    body.append(f'<g clip-path="url(#field)" stroke="{p["accent"]}" stroke-linecap="round" stroke-linejoin="round">'
                f'<path class="trace" d="{d}" pathLength="{n}" stroke-opacity=".38" stroke-width=".9"/>'
                f'<path class="snake" d="{d}" pathLength="{n}" stroke-width="{num(cell * .5)}"/></g>')

    return document(W, H, "Contributions",
                    f"{total} contributions, {span.title()}. A snake-like agent plans its way through every day "
                    f"with work on it; its route stays behind as a thin line.",
                    "".join(body), defs=g.defs() + clip, style="".join(css))
