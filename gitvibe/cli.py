"""Command-line entry point for gitvibe."""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console

from . import __version__
from .git_stats import NotAGitRepo, collect_stats
from .personality import analyze
from .render import render, render_roast
from .roast import roast as roast_repo


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gitvibe",
        description="Spotify Wrapped, but for your git history. Runs fully offline.",
    )
    p.add_argument("path", nargs="?", default=".", help="path to the git repo (default: .)")
    p.add_argument("--me", action="store_true", help="only count commits by your git user.email")
    p.add_argument("--author", help="filter commits by author name or email")
    p.add_argument("--since", help="only commits after this date, e.g. '2025-01-01' or '1 year ago'")
    p.add_argument("--card", metavar="FILE", help="export a shareable PNG card to FILE")
    p.add_argument("--roast", action="store_true", help="roast your commit history (offline, savage, screenshot-worthy)")
    p.add_argument("--json", action="store_true", help="print raw stats as JSON instead of a report")
    p.add_argument("--version", action="version", version=f"gitvibe {__version__}")
    return p


def _resolve_author(args, path: str) -> str | None:
    if args.author:
        return args.author
    if args.me:
        import subprocess

        out = subprocess.run(
            ["git", "config", "user.email"],
            cwd=path, capture_output=True, text=True,
        )
        email = out.stdout.strip()
        if not email:
            print("Could not read git user.email; use --author instead.", file=sys.stderr)
            sys.exit(2)
        return email
    return None


def _make_utf8_safe() -> None:
    """Best-effort: never crash on terminals with a non-Unicode codepage."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _make_utf8_safe()
    console = Console()

    try:
        author = _resolve_author(args, args.path)
        stats = collect_stats(args.path, author=author, since=args.since)
    except NotAGitRepo as exc:
        console.print(f"[red]Not a git repository:[/red] {exc}")
        return 1

    personality = analyze(stats)

    if args.json:
        payload = {
            "repo": stats.repo_name,
            "personality": personality.title,
            "tagline": personality.tagline,
            "total_commits": stats.total_commits,
            "active_days": stats.active_days,
            "longest_streak": stats.longest_streak,
            "current_streak": stats.current_streak,
            "insertions": stats.insertions,
            "deletions": stats.deletions,
            "by_hour": stats.by_hour,
            "by_weekday": stats.by_weekday,
            "top_extensions": stats.top_extensions,
        }
        if args.roast:
            r = roast_repo(stats)
            payload["roast"] = {
                "score": r.score,
                "level": r.level,
                "burns": r.burns,
                "verdict": r.verdict,
            }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.roast:
        r = roast_repo(stats)
        render_roast(stats, r, console)
        if args.card:
            from .card import render_roast_card

            out = render_roast_card(stats, r, args.card)
            console.print(f"[green]Saved roast card →[/green] {out}")
        return 0

    render(stats, personality, console)

    if args.card:
        from .card import render_card

        out = render_card(stats, personality, args.card)
        console.print(f"[green]Saved card →[/green] {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
