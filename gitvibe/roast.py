"""Roast a repo based on its commit history — fully offline, no AI required.

This reads the same `Stats` gitvibe already collects and turns the embarrassing
parts of your git history into savage-but-affectionate one-liners. Every burn is
backed by a real number, so it feels personal (and very screenshot-able).

Nothing here calls the network. It's all rule-based pattern matching over your
local commit subjects and timing.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from .git_stats import Stats

# Low-effort commit subjects we all know we've written at 2am.
_LAZY = {
    "update", "updates", "updated", "wip", "stuff", "things", "change",
    "changes", "misc", "minor", "tweak", "tweaks", "edit", "edits", "asdf",
    "oops", "nvm", "temp", "tmp", "test", "x", "y", "z", "more", "again",
    ".", "..", "...", "!", "ok", "okay", "done", "final", "save", "commit",
}

_FIX = re.compile(r"\b(fix|fixes|fixed|bug|hotfix|patch|broken|revert)\w*", re.I)
_REVERT = re.compile(r"\brevert\w*", re.I)
_TYPO = re.compile(r"\btypo\w*", re.I)
_DESPERATE = re.compile(
    r"\b(please|plz|pls|work|finally|why|seriously|i swear|come on|ugh|argh|"
    r"omg|wtf|kill me|help|hate|stupid)\b",
    re.I,
)
_FINAL = re.compile(r"\b(final|really final|last one|for real|actually final|done now)\b", re.I)
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]"
)


@dataclass
class Roast:
    """A finished roast: a list of burns, a verdict, and a 0–100 char level."""

    burns: list[str]
    verdict: str
    score: int
    level: str


def _pct(part: int, whole: int) -> int:
    return round(100 * part / whole) if whole else 0


def _words(subject: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", subject)


def _gather(stats: Stats):
    """Return a bag of measurements used by the roast rules."""
    subjects = [c.subject.strip() for c in stats.commits]
    total = len(subjects) or 1

    fix = sum(1 for s in subjects if _FIX.search(s))
    revert = sum(1 for s in subjects if _REVERT.search(s))
    typo = sum(1 for s in subjects if _TYPO.search(s))
    desperate = sum(1 for s in subjects if _DESPERATE.search(s))
    final = sum(1 for s in subjects if _FINAL.search(s))
    emoji = sum(1 for s in subjects if _EMOJI.search(s))
    lazy = sum(1 for s in subjects if s.lower().strip(" .!") in _LAZY)
    one_word = sum(1 for s in subjects if len(_words(s)) <= 1)
    shouting = sum(1 for s in subjects if len(s) > 4 and s.upper() == s and s.lower() != s)
    short = sum(1 for s in subjects if len(s) <= 8)
    ellipsis = sum(1 for s in subjects if s.endswith("..."))

    by_hour = stats.by_hour
    htotal = sum(by_hour) or 1
    night = sum(by_hour[0:5] + by_hour[22:24])
    by_wd = stats.by_weekday
    wtotal = sum(by_wd) or 1
    weekend = by_wd[5] + by_wd[6]

    avg_len = round(sum(len(s) for s in subjects) / total)

    return {
        "total": len(subjects),
        "fix_pct": _pct(fix, total),
        "revert": revert,
        "typo": typo,
        "desperate": desperate,
        "final": final,
        "emoji_pct": _pct(emoji, total),
        "lazy_pct": _pct(lazy, total),
        "one_word_pct": _pct(one_word, total),
        "shouting": shouting,
        "short_pct": _pct(short, total),
        "ellipsis": ellipsis,
        "night_pct": _pct(night, htotal),
        "weekend_pct": _pct(weekend, wtotal),
        "avg_len": avg_len,
        "streak": stats.longest_streak,
        "insertions": stats.insertions,
        "deletions": stats.deletions,
    }


# Each rule: (severity, predicate(m) -> bool, line(m) -> str)
_RULES = [
    (9, lambda m: m["fix_pct"] >= 30,
     lambda m: f"{m['fix_pct']}% of your commits are fixes. Maybe ship it right the first time? Just a thought."),
    (8, lambda m: m["revert"] >= 3,
     lambda m: f"{m['revert']} reverts. Git is the only thing standing between you and total chaos."),
    (8, lambda m: m["lazy_pct"] >= 20,
     lambda m: f'{m["lazy_pct"]}% of your messages are basically "update". Future-you sends their regards. They are not happy.'),
    (7, lambda m: m["one_word_pct"] >= 40,
     lambda m: f"{m['one_word_pct']}% of your commits are one word. `git log` reads like a ransom note."),
    (8, lambda m: m["final"] >= 2,
     lambda m: f'You have {m["final"]} commits claiming to be the "final" one. We both know that\'s a lie.'),
    (7, lambda m: m["night_pct"] >= 25,
     lambda m: f"{m['night_pct']}% of your commits land between 10pm and 5am. Sleep is for people with passing tests, apparently."),
    (6, lambda m: m["desperate"] >= 2,
     lambda m: f'{m["desperate"]} commit messages openly beg the code to work. Bargaining is the 4th stage of debugging.'),
    (6, lambda m: m["typo"] >= 2,
     lambda m: f'{m["typo"]} "fix typo" commits. Your spellchecker is unemployed and it\'s your fault.'),
    (5, lambda m: m["shouting"] >= 1,
     lambda m: f"{m['shouting']} commit(s) IN ALL CAPS. We can hear you screaming through the git history."),
    (6, lambda m: m["avg_len"] <= 12 and m["total"] >= 10,
     lambda m: f"Average commit message length: {m['avg_len']} characters. Twitter gives you 280. Use a few."),
    (5, lambda m: m["emoji_pct"] >= 25,
     lambda m: f"{m['emoji_pct']}% of your commits have emoji. The vibes are immaculate; the changelog is unreadable."),
    (5, lambda m: m["weekend_pct"] >= 35,
     lambda m: f"{m['weekend_pct']}% of your commits are on weekends. 'Work-life balance' was never installed."),
    (6, lambda m: m["streak"] >= 14,
     lambda m: f"A {m['streak']}-day commit streak. Impressive. Also, please, the grass misses you."),
    (5, lambda m: m["deletions"] > m["insertions"] and m["insertions"] > 0,
     lambda m: f"You deleted more lines ({m['deletions']:,}) than you wrote ({m['insertions']:,}). Negative-LOC engineering. Bold."),
    (4, lambda m: m["ellipsis"] >= 3,
     lambda m: f'{m["ellipsis"]} commits trailing off into "..." like you weren\'t sure it was done either.'),
    (4, lambda m: m["short_pct"] >= 50,
     lambda m: f"{m['short_pct']}% of your messages are 8 chars or fewer. Minimalism, or just tired? (It's tired.)"),
]

# When the history is suspiciously clean, roast *that*.
_CLEAN = [
    "Suspiciously clean history. You force-pushed over the evidence, didn't you?",
    "Tidy commits, sensible messages... who are you and what did you do with the real dev?",
    "No fixes, no reverts, no 2am panic. Either you're a robot or this repo is one commit old.",
]

_LEVELS = [
    (0, "Lightly toasted", "\U0001F35E"),     # 🍞
    (25, "Medium rare", "\U0001F969"),         # 🥩
    (45, "Well done", "\U0001F525"),           # 🔥
    (65, "Burnt to a crisp", "\U0001F525\U0001F525"),
    (85, "Cremated — call a priest", "⚰️"),  # ⚰️
]


def _verdict(m: dict, score: int) -> str:
    if m["total"] < 5:
        return "Too few commits to fully judge you. Lucky escape. For now."
    if score >= 70:
        return "Verdict: your git history is a cry for help with great test coverage."
    if score >= 45:
        return "Verdict: chaotic, caffeinated, and somehow it ships. Respect."
    if score >= 25:
        return "Verdict: messy in all the normal ways. You're going to be fine."
    return "Verdict: annoyingly responsible. Live a little — break main once."


def roast(stats: Stats, seed: int | None = None) -> Roast:
    """Build a Roast from a repo's stats."""
    if stats.total_commits == 0:
        return Roast(
            burns=["There are no commits here. We can't roast a blank page. That IS the roast."],
            verdict="Verdict: 0 commits. The cleanest history is the one that never happened.",
            score=0,
            level="Untouched",
        )

    m = _gather(stats)
    rng = random.Random(seed if seed is not None else stats.total_commits)

    triggered = [(sev, make(m)) for sev, pred, make in _RULES if pred(m)]
    triggered.sort(key=lambda t: t[0], reverse=True)

    if triggered:
        # Keep the sharpest burns, but shuffle the chosen few for variety.
        top = triggered[:6]
        rng.shuffle(top)
        burns = [line for _, line in top]
        score = min(100, sum(sev for sev, _ in triggered) * 6)
    else:
        burns = [rng.choice(_CLEAN)]
        score = 8

    level = _LEVELS[0][1]
    emoji = _LEVELS[0][2]
    for threshold, label, ico in _LEVELS:
        if score >= threshold:
            level, emoji = label, ico
    level = f"{emoji}  {level}"

    return Roast(burns=burns, verdict=_verdict(m, score), score=score, level=level)
