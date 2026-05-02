"""Render stats to a colourful terminal report using `rich`."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .git_stats import Stats
from .personality import Personality

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
BLOCKS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: list[int]) -> str:
    hi = max(values) or 1
    return "".join(BLOCKS[min(8, round(v / hi * 8))] for v in values)


def _hour_chart(by_hour: list[int]) -> Text:
    spark = _sparkline(by_hour)
    text = Text()
    text.append(spark + "\n", style="bold cyan")
    text.append("0   3   6   9   12  15  18  21  ", style="dim")
    return text


def _weekday_table(by_weekday: list[int]) -> Table:
    table = Table.grid(padding=(0, 1))
    hi = max(by_weekday) or 1
    for name, val in zip(WEEKDAYS, by_weekday):
        bar = "█" * round(val / hi * 18)
        style = "green" if name in ("Sat", "Sun") else "cyan"
        table.add_row(
            Text(name, style="bold"),
            Text(bar or "·", style=style),
            Text(str(val), style="dim"),
        )
    return table


def _key_table(stats: Stats) -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style="bold magenta")
    table.add_column()

    span = ""
    if stats.first and stats.last:
        span = f"{stats.first:%b %Y} → {stats.last:%b %Y}"

    rows = [
        ("Commits", str(stats.total_commits)),
        ("Active days", str(stats.active_days)),
        ("Longest streak", f"{stats.longest_streak} days"),
        ("Current streak", f"{stats.current_streak} days"),
        ("Lines added", f"+{stats.insertions:,}"),
        ("Lines removed", f"-{stats.deletions:,}"),
        ("Span", span),
    ]
    if stats.busiest_day:
        day, count = stats.busiest_day
        rows.append(("Busiest day", f"{day:%d %b %Y} ({count} commits)"))
    for label, value in rows:
        table.add_row(label, value)
    return table


def _top_extensions(stats: Stats) -> Text:
    text = Text()
    for ext, count in stats.top_extensions[:6]:
        text.append(f"  {ext:<10}", style="yellow")
        text.append(f"{count}\n", style="dim")
    return text or Text("  (no file data)\n", style="dim")


def render(stats: Stats, personality: Personality, console: Console | None = None) -> None:
    console = console or Console()

    if stats.total_commits == 0:
        console.print(
            Panel(
                "No commits found for this filter. Try a different --author or --since.",
                title="gitvibe",
                border_style="red",
            )
        )
        return

    header = Text()
    header.append(f"{personality.emoji}  ", style="bold")
    header.append(personality.title, style="bold white")
    header.append(f"\n{personality.tagline}", style="italic dim")

    body = Group(
        Panel(header, border_style="magenta", title=f"gitvibe · {stats.repo_name}"),
        Panel(_key_table(stats), title="Stats", border_style="cyan"),
        Panel(_hour_chart(stats.by_hour), title="Commits by hour", border_style="cyan"),
        Panel(_weekday_table(stats.by_weekday), title="Commits by weekday", border_style="cyan"),
        Panel(_top_extensions(stats), title="Top file types", border_style="cyan"),
    )
    console.print(body)
    console.print(
        "[dim]Generated with gitvibe · share your card with --card vibe.png[/dim]"
    )
