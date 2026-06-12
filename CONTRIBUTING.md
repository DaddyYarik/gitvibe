# Contributing to gitvibe

Thanks for being here! gitvibe is designed to grow with the community, and small
PRs are genuinely welcome.

## Quick start

```bash
git clone https://github.com/DaddyYarik/gitvibe
cd gitvibe
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e ".[card]"
gitvibe .                     # run it against this very repo
```

## Project layout

```
gitvibe/
├── git_stats.py    # read + aggregate local git history (subprocess)
├── personality.py  # map stats -> chronotype + style
├── render.py       # rich terminal report
├── card.py         # Pillow PNG card
└── cli.py          # argparse entry point
```

## Good first issues

- **New personality archetypes** — add a pattern to `_PATTERNS` in `personality.py`.
- **Card themes** — parametrise the colour constants in `card.py`.
- **More charts** — e.g. a monthly streak calendar in `render.py`.

## Guidelines

- Keep the core dependency-light (`rich` only; `Pillow` stays optional).
- The tool must keep working **offline** — no network calls in the core path.
- Run `gitvibe .` before opening a PR to make sure the report still renders.

By contributing you agree your work is licensed under the MIT License.
