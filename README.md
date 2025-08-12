# tuxagotchi-syu

A virtual pet that tracks your Arch Linux system updates.

---

## Description

**tuxagotchi-syu** is a fun terminal-based virtual pet inspired by Tamagotchi, which grows and thrives as you keep your Arch Linux system updated. It integrates with Pacman and tracks your system updates, encouraging good maintenance habits!

---

## Features

- Tracks Pacman updates and reflects system health.
- Configurable via a TOML config file.
- Supports GitHub integration for advanced stats.
- Customizable color themes.
- Simple and lightweight, built with Python and Textual.

---

## Installation

Install from the Arch User Repository (AUR) with your preferred AUR helper:

```bash
paru -S tuxagotchi-syu
# or
yay -S tuxagotchi-syu
```

---

## Usage

Run the app with:

```bash
tuxagotchi-syu
```

On first run, a config file will be created at:

```
~/.config/tuxagotchi-syu/config.toml
```

Edit this file to customize the app and add GitHub integration.

---

## Configuration

The config file uses [TOML](https://toml.io/en/) format. You can adjust:

- GitHub credentials for commit tracking.
- Color themes.
- Other preferences.

---

## Thanks

A special thanks to ISimpForCartoonGirls (yes, really) for this brilliant idea.
![Tuxagotchi Screenshot](screenshots/gooner.jpg)


## Development

Source code and issues available on [GitHub](https://github.com/terpinedream/tuxagotchi-syu).

---

## License

This project is licensed under the GPL.

---

## Maintainer

[terpinedream](https://github.com/terpinedream)

---

*Enjoy keeping your Arch Linux system healthy with tuxagotchi-syu!* 🐧

