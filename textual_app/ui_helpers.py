from typing import Optional
from datetime import timedelta
import os


def load_ascii(mood: str, tick: int) -> str:
    """Load ASCII art from two alternating files per mood for animation"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, "..", "assets", f"{mood}.txt")
    alt_path = os.path.join(script_dir, "..", "assets", f"{mood}2.txt")

    try:
        with open(base_path) as f:
            base_lines = f.readlines()
    except FileNotFoundError:
        base_lines = ["(?)\n"]

    try:
        with open(alt_path) as f:
            alt_lines = f.readlines()
    except FileNotFoundError:
        alt_lines = base_lines

    max_height = max(len(base_lines), len(alt_lines))
    base_lines += ["\n"] * (max_height - len(base_lines))
    alt_lines += ["\n"] * (max_height - len(alt_lines))

    return "".join(base_lines if tick % 2 == 0 else alt_lines)


def format_timedelta(td: timedelta) -> str:
    """Format timedelta into concise string (seconds, minutes, hours, days)"""
    seconds = int(td.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"


def generate_block_bar(tux: object, tick: int, length: int = 10) -> str:
    """Generate block progress bar for mood countdowns"""
    if not hasattr(tux, "mood") or not hasattr(tux, "time_until_next_mood"):
        return "[Invalid Tux object]"

    countdown = tux.time_until_next_mood()
    if not countdown:
        return ""  # No countdown for sad/dead moods

    if tux.mood == "happy":
        total = 4 * 3600  # 4 hours in seconds
    elif tux.mood == "neutral":
        total = 24 * 3600  # 1 day in seconds
    else:
        return ""

    remaining = countdown.total_seconds()
    progress = 1 - (remaining / total)
    blocks_filled = int(progress * length)
    blocks_empty = length - blocks_filled

    animation = ["░", "▒", "▓", "█", "▓", "▒"]
    frame = animation[tick % len(animation)]

    if blocks_filled > 0:
        return "█" * (blocks_filled - 1) + frame + "░" * blocks_empty
    else:
        return frame + "░" * (length - 1)


def center_ascii(art: str, width: int = 32) -> str:
    """Center ASCII art horizontally given a target width"""
    lines = art.splitlines()
    return "\n".join(line.center(width) for line in lines)


def generate_css(colors: dict) -> str:
    """Generate CSS string with colors from config"""
    return f"""
Screen {{
  background: black;
  border: none;
  padding: 0;
  margin: 0;
}}

#main-container {{
    height: 100%;
    width: 100%;
    padding: 0 0 0 0;
}}

#tux-widget {{
    width: 60;
    padding: 1 2;
    margin: 1 0 0 0;
    border: round {colors["accent"]};
    background: {colors["background"]};
    color: {colors["foreground"]};
}}

#pacman-widget {{
    min-width: 20;
    max-width: 20;
    padding: 1 2;
    margin: 1 0 0 0;
    border: none;
    background: transparent;
    color: {colors["foreground"]};
    overflow-y: auto;
}}

#pacman-output {{
    border: round white;
    background: transparent;
    color: {colors["foreground"]};
}}

#pacman-button {{
    border: round white;
    background: transparent;
    color: {colors["foreground"]};
    margin: 1 0;
}}
"""
