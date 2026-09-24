"""The contribution calendar: fetched from GitHub, or rebuilt from a CSV for previews."""
from __future__ import annotations

import datetime as dt
import json
import urllib.request
from dataclasses import dataclass

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      }
    }
  }
}"""


@dataclass
class Day:
    date: dt.date
    count: int
    level: int
    col: int
    row: int  # 0 = Sunday, as on GitHub


def fetch(login: str, token: str) -> list[Day]:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": f"{login}-profile"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for col, week in enumerate(weeks):
        for d in week["contributionDays"]:
            days.append(Day(dt.date.fromisoformat(d["date"]), d["contributionCount"],
                            LEVELS[d["contributionLevel"]], col, d["weekday"]))
    return days


def from_counts(counts: dict[dt.date, int], end: dt.date) -> list[Day]:
    """GitHub's layout (53 Sunday-first weeks ending at `end`) with quartile levels."""
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    nonzero = sorted(v for d, v in counts.items() if start <= d <= end and v > 0)

    def level(v):
        if v <= 0 or not nonzero:
            return 0
        q = [nonzero[int(len(nonzero) * f)] for f in (.25, .5, .75)]
        return 1 + sum(v > t for t in q)

    days, d = [], start
    while d <= end:
        off = (d - start).days
        days.append(Day(d, counts.get(d, 0), level(counts.get(d, 0)), off // 7, off % 7))
        d += dt.timedelta(days=1)
    return days


def read_csv(path: str) -> dict[dt.date, int]:
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                day, n = line.strip().split(",")
                out[dt.date.fromisoformat(day)] = int(n)
    return out
