import os
from pathlib import Path

ASCII_FRAMES = {}


def preload_ascii_frames(asset_dir=None):
    """Preload ASCII frames with dynamic asset directory resolution"""
    if asset_dir is None:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent.parent  # Go up one level from textual_app/
        asset_dir = script_dir / "assets"
    else:
        asset_dir = Path(asset_dir)

    moods = ["happy", "neutral", "sad"]
    for mood in moods:
        ASCII_FRAMES[mood] = []
        for i in range(2):
            path = asset_dir / f"{mood}_{i + 1}.txt"
            if path.exists():
                ASCII_FRAMES[mood].append(path.read_text())
            else:
                ASCII_FRAMES[mood].append(f"[Missing {mood}_{i + 1}]")
