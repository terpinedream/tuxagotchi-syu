import toml
import os
from pathlib import Path


def load_config():
    """Load config from user's config directory or fallback to local config.toml"""

    # Check for user config first (specific to tuxagotchi-syu)
    user_config_path = Path.home() / ".config" / "tuxagotchi-syu" / "config.toml"

    # Check for environment variable (set by launcher script)
    env_config_path = os.getenv("TUXAGOTCHI_SYU_CONFIG_PATH")
    if env_config_path:
        config_path = Path(env_config_path)
    elif user_config_path.exists():
        config_path = user_config_path
    else:
        # Fallback to local config.toml for development
        config_path = Path("config.toml")

    try:
        config = toml.load(str(config_path))
        print(f"Loaded config from: {config_path}")
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        print("Please run 'tuxagotchi-syu' to set up your configuration.")
        # Return minimal config to prevent crashes
        config = {
            "github": {
                "username": "GITHUBUSERNAME",
                "repo": "REPONAME",
                "token": "TOKENHERE",
            },
            "colors": {},
        }

    # Provide fallback defaults for colors
    colors = config.get("colors", {})
    config["colors"] = {
        "accent": colors.get("accent", "red"),
        "background": colors.get("background", "transparent"),
        "foreground": colors.get("foreground", "red"),
        "highlight": colors.get("highlight", "red"),
        "todo_border": colors.get("todo_border", "red"),
    }

    return config
