"""Turn raw stats into a fun, shareable coding personality.

A personality has two parts:
  * a *chronotype* (when you commit)  e.g. "Night Owl"
  * a *style*      (how you commit)   e.g. "Fix-it Felix"

The combination is what makes the result feel personal and tweet-worthy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .git_stats import Stats


@dataclass
class Personality:
    chronotype: str
    style: str
    emoji: str
    tagline: str

    @property
    def title(self) -> str:
        return f"{self.chronotype} {self.style}"


# (label, emoji, predicate over hour-buckets fractions)
def _chronotype(by_hour: list[int]) -> tuple[str, str]:
    total = sum(by_hour) or 1
    night = sum(by_hour[22:24] + by_hour[0:5]) / total      # 22:00–04:59
    morning = sum(by_hour[5:9]) / total                     # 05:00–08:59
    work = sum(by_hour[9:18]) / total                       # 09:00–17:59
    evening = sum(by_hour[18:22]) / total                   # 18:00–21:59

    buckets = {
        ("Night Owl", "\U0001F989"): night,
        ("Early Bird", "\U0001F426"): morning,
        ("Nine-to-Fiver", "☕"): work,
        ("Evening Hacker", "\U0001F319"): evening,
    }
    (label, emoji), _ = max(buckets.items(), key=lambda kv: kv[1])
    return label, emoji


_PATTERNS = {
    "Fix-it Felix": r"\b(fix|bug|hotfix|patch|resolve|repair)\b",
    "Refactor Addict": r"\b(refactor|cleanup|clean up|rename|reorg|tidy|simplif)\w*",
    "The Documenter": r"\b(doc|docs|readme|comment|typo)\w*",
    "WIP Wizard": r"\b(wip|temp|tmp|stash|checkpoint)\b",
    "Test Pilot": r"\b(test|spec|coverage|ci)\w*",
    "Ship It Captain": r"\b(add|feature|feat|implement|new|ship)\w*",
}


def _style(stats: Stats) -> str:
    counts = {name: 0 for name in _PATTERNS}
    for c in stats.commits:
        subject = c.subject.lower()
        for name, pattern in _PATTERNS.items():
            if re.search(pattern, subject):
                counts[name] += 1
    if not any(counts.values()):
        return "Mystery Coder"
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _weekend_ratio(by_weekday: list[int]) -> float:
    total = sum(by_weekday) or 1
    return (by_weekday[5] + by_weekday[6]) / total


def _tagline(stats: Stats, chrono: str, style: str) -> str:
    if _weekend_ratio(stats.by_weekday) > 0.4:
        return "Weekends are just untracked work hours."
    if stats.longest_streak >= 7:
        return f"Survived a {stats.longest_streak}-day commit streak. Respect."
    bits = {
        "Night Owl": "The best code compiles after midnight.",
        "Early Bird": "Commits before coffee. Iconic.",
        "Nine-to-Fiver": "Professional, punctual, productive.",
        "Evening Hacker": "Golden-hour pushes hit different.",
    }
    return bits.get(chrono, "Built one commit at a time.")


def analyze(stats: Stats) -> Personality:
    chrono, emoji = _chronotype(stats.by_hour)
    style = _style(stats)
    tagline = _tagline(stats, chrono, style)
    return Personality(chronotype=chrono, style=style, emoji=emoji, tagline=tagline)
