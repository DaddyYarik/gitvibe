"""Render a shareable PNG card. Requires Pillow (`pip install gitvibe[card]`).

The card is sized 1200x630 — the standard social-share aspect ratio — so it
looks good when posted to Twitter/X, LinkedIn, or a README.

There's also :func:`render_roast_card`, which renders a `--roast` as a real
terminal-window screenshot (dark chrome, monospace text, colour emoji).
"""

from __future__ import annotations

import os

from .git_stats import Stats
from .personality import Personality
from .roast import Roast

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


# --------------------------------------------------------------------------- #
# Roast card: a terminal-window screenshot of `gitvibe --roast`.
# --------------------------------------------------------------------------- #

_MONO_CANDIDATES = [
    r"C:\Windows\Fonts\consola.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]
_MONO_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\consolab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]
_EMOJI_CANDIDATES = [
    r"C:\Windows\Fonts\seguiemj.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
]

# Terminal palette (GitHub-dark-ish).
T_BG = (13, 17, 23)
T_BAR = (28, 33, 40)
T_FG = (230, 237, 243)
T_DIM = (139, 148, 158)
T_RED = (248, 81, 73)
T_YELLOW = (231, 179, 88)
T_GREEN = (63, 185, 80)
T_PROMPT = (86, 211, 100)
DOTS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]


def _first_existing(paths: list[str]):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _mono(size: int, bold: bool = False):
    from PIL import ImageFont

    path = _first_existing(_MONO_BOLD_CANDIDATES if bold else _MONO_CANDIDATES)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def _emoji_font(size: int):
    from PIL import ImageFont

    path = _first_existing(_EMOJI_CANDIDATES)
    if not path:
        return None
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return None


def _roast_lines(stats: Stats, roast: Roast) -> list[list[tuple]]:
    """Turn a Roast into renderable lines of (kind, text, fill) tokens.

    kind is one of: "emoji", "mono", "bold". `fill` is ignored for emoji.
    """
    emoji, _, label = roast.level.partition("  ")
    filled = round(roast.score / 100 * 20)
    meter = "█" * filled + "░" * (20 - filled)
    lines: list[list[tuple]] = [
        [("dim", "$ ", None), ("mono", "gitvibe --roast", T_FG)],
        [],
        [("emoji", emoji.strip(), None), ("bold", "  " + label, T_RED)],
        [("bold", meter, T_RED), ("bold", f"  {roast.score}/100", T_YELLOW)],
        [],
    ]
    for burn in roast.burns:
        # split a leading emoji off the burn if present, else add a flame
        lines.append([("emoji", "\U0001F525", None),
                      ("mono", "  " + burn, T_FG)])
    lines.append([])
    lines.append([("bold", roast.verdict, T_YELLOW)])
    return lines


def render_roast_card(stats: Stats, roast: Roast, out_path: str) -> str:
    """Render a roast as a terminal-window PNG screenshot."""
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Card export needs Pillow. Install it with:  pip install gitvibe[card]"
        ) from exc

    size = 30
    line_h = 46
    pad_x, pad_top, pad_bottom = 44, 30, 36
    bar_h = 56
    radius = 16
    margin = 46  # room for the drop shadow

    f_mono = _mono(size)
    f_bold = _mono(size, bold=True)
    f_emoji = _emoji_font(size)
    f_title = _mono(24, bold=True)

    lines = _roast_lines(stats, roast)

    def tok_font(kind):
        return {"mono": f_mono, "dim": f_mono, "bold": f_bold}.get(kind, f_mono)

    def line_width(tokens) -> int:
        w = 0
        for kind, text, _ in tokens:
            f = f_emoji if (kind == "emoji" and f_emoji) else tok_font(kind)
            w += f.getlength(text)
        return int(w)

    inner_w = max((line_width(t) for t in lines), default=400)
    inner_w = max(inner_w, int(f_title.getlength(f"gitvibe · roast — {stats.repo_name}")) + 120)
    win_w = inner_w + 2 * pad_x
    win_h = bar_h + pad_top + len(lines) * line_h + pad_bottom
    W, H = win_w + 2 * margin, win_h + 2 * margin

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # soft drop shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [margin, margin + 8, margin + win_w, margin + win_h + 8],
        radius=radius, fill=(0, 0, 0, 150),
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))

    draw = ImageDraw.Draw(img)
    x0, y0 = margin, margin
    x1, y1 = margin + win_w, margin + win_h

    # window body + title bar
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=T_BG)
    draw.rounded_rectangle([x0, y0, x1, y0 + bar_h + radius], radius=radius, fill=T_BAR)
    draw.rectangle([x0, y0 + bar_h, x1, y0 + bar_h + 2], fill=(0, 0, 0, 60))

    # traffic-light dots
    cy = y0 + bar_h // 2
    for i, color in enumerate(DOTS):
        cx = x0 + 26 + i * 26
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=color)

    title = f"gitvibe · roast — {stats.repo_name}"
    tw = f_title.getlength(title)
    draw.text((x0 + (win_w - tw) / 2, cy - 13), title, font=f_title, fill=T_DIM)

    # body
    y = y0 + bar_h + pad_top
    for tokens in lines:
        x = x0 + pad_x
        for kind, text, fill in tokens:
            if kind == "emoji" and f_emoji:
                draw.text((x, y - 2), text, font=f_emoji, embedded_color=True)
                x += f_emoji.getlength(text)
            else:
                color = T_DIM if kind == "dim" else (fill or T_FG)
                f = tok_font(kind)
                draw.text((x, y), text, font=f, fill=color)
                x += f.getlength(text)
        y += line_h

    img.save(out_path)
    return out_path
