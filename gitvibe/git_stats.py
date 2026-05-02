"""Collect statistics from a local git repository.

Everything here runs against the *local* git history via subprocess, so it works
offline on any repo without API tokens or network access.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

US = "\x1f"  # unit separator between fields
RS = "\x1e"  # record separator between commits


class NotAGitRepo(Exception):
    """Raised when the given path is not inside a git repository."""


@dataclass
class Commit:
    hash: str
    author: str
    email: str
    timestamp: int
    subject: str

    @property
    def dt(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)


@dataclass
class Stats:
    repo_name: str
    total_commits: int
    first: datetime | None
    last: datetime | None
    by_hour: list[int]            # length 24, index = hour of day
    by_weekday: list[int]         # length 7, Monday = 0
    longest_streak: int
    current_streak: int
    busiest_day: tuple | None     # (date, count)
    active_days: int
    insertions: int
    deletions: int
    top_extensions: list          # [(ext, commits_touching), ...]
    top_files: list               # [(path, changes), ...]
    authors: list                 # [(name, count), ...]
    commits: list = field(default_factory=list)


def _run_git(args: list[str], cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:  # git not installed
        raise NotAGitRepo("git executable not found on PATH") from exc
    if out.returncode != 0:
        raise NotAGitRepo(out.stderr.strip() or "not a git repository")
    return out.stdout


def _repo_name(cwd: str) -> str:
    try:
        top = _run_git(["rev-parse", "--show-toplevel"], cwd).strip()
        if top:
            return os.path.basename(top)
    except NotAGitRepo:
        pass
    return os.path.basename(os.path.abspath(cwd))


def _collect_commits(cwd: str, author: str | None, since: str | None) -> list[Commit]:
    fmt = US.join(["%H", "%an", "%ae", "%at", "%s"]) + RS
    args = ["log", "--no-merges", f"--pretty=format:{fmt}"]
    if author:
        args.append(f"--author={author}")
    if since:
        args.append(f"--since={since}")
    raw = _run_git(args, cwd)

    commits: list[Commit] = []
    for record in raw.split(RS):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(US)
        if len(parts) != 5:
            continue
        h, an, ae, at, subject = parts
        try:
            ts = int(at)
        except ValueError:
            continue
        commits.append(Commit(h, an, ae, ts, subject))
    return commits


_NUMSTAT_RE = re.compile(r"^(\d+)\t(\d+)\t(.+)$")


def _collect_file_stats(cwd: str, author: str | None, since: str | None):
    args = ["log", "--no-merges", "--numstat", "--pretty=format:"]
    if author:
        args.append(f"--author={author}")
    if since:
        args.append(f"--since={since}")
    raw = _run_git(args, cwd)

    insertions = deletions = 0
    ext_counter: Counter = Counter()
    file_counter: Counter = Counter()

    for line in raw.splitlines():
        m = _NUMSTAT_RE.match(line)
        if not m:
            continue
        added, removed, path = m.groups()
        insertions += int(added)
        deletions += int(removed)
        changes = int(added) + int(removed)
        file_counter[path] += changes
        _, ext = os.path.splitext(path)
        if ext:
            ext_counter[ext.lower()] += 1
        else:
            ext_counter["(no ext)"] += 1

    return insertions, deletions, ext_counter, file_counter


def _streaks(dates: set) -> tuple[int, int]:
    """Return (longest_streak, current_streak) in days from a set of dates."""
    if not dates:
        return 0, 0
    ordered = sorted(dates)
    longest = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        if (cur - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)

    # current streak: consecutive days ending today or yesterday
    today = datetime.now().date()
    current = 0
    day = today if today in dates else today - timedelta(days=1)
    while day in dates:
        current += 1
        day -= timedelta(days=1)
    return longest, current


def collect_stats(
    path: str = ".",
    author: str | None = None,
    since: str | None = None,
) -> Stats:
    """Gather all statistics for a repository at ``path``."""
    cwd = os.path.abspath(path)
    commits = _collect_commits(cwd, author, since)
    repo_name = _repo_name(cwd)

    if not commits:
        return Stats(
            repo_name=repo_name, total_commits=0, first=None, last=None,
            by_hour=[0] * 24, by_weekday=[0] * 7, longest_streak=0,
            current_streak=0, busiest_day=None, active_days=0,
            insertions=0, deletions=0, top_extensions=[], top_files=[],
            authors=[], commits=[],
        )

    by_hour = [0] * 24
    by_weekday = [0] * 7
    day_counter: Counter = Counter()
    author_counter: Counter = Counter()

    for c in commits:
        dt = c.dt
        by_hour[dt.hour] += 1
        by_weekday[dt.weekday()] += 1
        day_counter[dt.date()] += 1
        author_counter[c.author] += 1

    longest, current = _streaks(set(day_counter))
    busiest_day = max(day_counter.items(), key=lambda kv: kv[1])
    timestamps = [c.timestamp for c in commits]
    insertions, deletions, ext_counter, file_counter = _collect_file_stats(
        cwd, author, since
    )

    return Stats(
        repo_name=repo_name,
        total_commits=len(commits),
        first=datetime.fromtimestamp(min(timestamps)),
        last=datetime.fromtimestamp(max(timestamps)),
        by_hour=by_hour,
        by_weekday=by_weekday,
        longest_streak=longest,
        current_streak=current,
        busiest_day=busiest_day,
        active_days=len(day_counter),
        insertions=insertions,
        deletions=deletions,
        top_extensions=ext_counter.most_common(8),
        top_files=file_counter.most_common(10),
        authors=author_counter.most_common(10),
        commits=commits,
    )
