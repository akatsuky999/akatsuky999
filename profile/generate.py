"""Render the profile plates.

    python profile/generate.py --out dist                 # live data (needs GITHUB_TOKEN)
    python profile/generate.py --out dist --csv days.csv  # offline preview from date,count rows
    python profile/generate.py --out assets --only header # the static name card
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent  # noqa: E402
import contrib  # noqa: E402
import header  # noqa: E402
from theme import PALETTES  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="akatsuky999")
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", help="offline preview: date,count per line")
    ap.add_argument("--today", help="offline preview: last day of the calendar (YYYY-MM-DD)")
    ap.add_argument("--only", choices=["header", "live"], help="render just one group")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    plates = {}
    if args.only != "live":
        for theme, p in PALETTES.items():
            plates[f"header-{theme}.svg"] = header.render(p)
    if args.only != "header":
        if args.csv:
            end = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
            days = contrib.from_counts(contrib.read_csv(args.csv), end)
        else:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                sys.exit("GITHUB_TOKEN is not set (or pass --csv for an offline preview)")
            days = contrib.fetch(args.user, token)
        total = sum(d.count for d in days[-365:])
        for theme, p in PALETTES.items():
            plates[f"snake-{theme}.svg"] = agent.render(days, p, total)

    for name, svg in plates.items():
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"{name:22s} {len(svg.encode()) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
