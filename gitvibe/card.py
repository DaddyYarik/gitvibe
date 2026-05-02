"""Render a shareable PNG card. Requires Pillow (`pip install gitvibe[card]`).

The card is sized 1200x630 — the standard social-share aspect ratio — so it
looks good when posted to Twitter/X, LinkedIn, or a README.
"""

from __future__ import annotations

import os

from .git_stats import Stats
from .personality import Personality

WIDTH, HEIGHT = 1200, 630
BG = (13, 17, 23)          # GitHub dark
FG = (230, 237, 243)
ACCENT = (188, 140, 255)   # purple
SUB = (139, 148, 158)
BAR = (88, 166, 255)       # blue

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    for path in (_FONT_BOLD_CANDIDATES if bold else _FONT_CANDIDATES):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_card(stats: Stats, personality: Personality, out_path: str) -> str:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Card export needs Pillow. Install it with:  pip install gitvibe[card]"
        ) from exc

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WIDTH, 8], fill=ACCENT)

    f_small = _load_font(26)
    f_label = _load_font(24)
    f_stat = _load_font(46, bold=True)
    f_title = _load_font(58, bold=True)
    f_repo = _load_font(30, bold=True)

    draw.text((60, 50), "gitvibe", font=f_repo, fill=ACCENT)
    draw.text((60, 92), stats.repo_name, font=f_small, fill=SUB)

    draw.text((60, 160), personality.title, font=f_title, fill=FG)
    draw.text((60, 232), personality.tagline, font=f_small, fill=SUB)

    # stat blocks
    stats_grid = [
        ("commits", f"{stats.total_commits:,}"),
        ("active days", f"{stats.active_days:,}"),
        ("longest streak", f"{stats.longest_streak}d"),
        ("lines added", f"+{stats.insertions:,}"),
    ]
    x = 60
    for label, value in stats_grid:
        draw.text((x, 320), value, font=f_stat, fill=FG)
        draw.text((x, 380), label, font=f_label, fill=SUB)
        x += 280

    # hour histogram
    draw.text((60, 460), "commits by hour", font=f_label, fill=SUB)
    hi = max(stats.by_hour) or 1
    bar_w = 40
    gap = 7
    base_y = 590
    for i, v in enumerate(stats.by_hour):
        h = int(v / hi * 90)
        bx = 60 + i * (bar_w + gap)
        draw.rectangle([bx, base_y - h, bx + bar_w, base_y], fill=BAR)

    img.save(out_path)
    return out_path
