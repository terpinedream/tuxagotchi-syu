from datetime import datetime, timezone, timedelta
import asyncio
import os
import subprocess
from typing import Optional
from pacman import get_last_pacman_update_time
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static, Input, Button
from textual.app import ComposeResult
from textual.events import Key
from textual import log
from textual_app.tux import Tux
from textual_app.tux_widget import TuxWidget
from config import load_config
from textual_app.ascii_loader import preload_ascii_frames
from rich.panel import Panel
from rich.text import Text
from rich import box


# UI Helper Functions (formerly in ui.py and ui_helpers.py)
def load_ascii(mood: str, tick: int) -> str:
    """Load ASCII art from two alternating files per mood for animation"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, "assets", f"{mood}.txt")
    alt_path = os.path.join(script_dir, "assets", f"{mood}2.txt")

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


class PacmanWidget(Widget):
    """Widget that displays live terminal output from 'sudo pacman -Syu'"""

    can_focus = True

    def __init__(self, id: str = "pacman-widget"):
        super().__init__(id=id)
        self._is_running = False
        self.process = None
        self.waiting_for_password = False
        self._stored_password = None

    def compose(self) -> ComposeResult:
        self.output_display = Static(
            "Ready to update packages...'",
            id="pacman-output",
        )
        self.update_button = Button("Update System", id="pacman-button")

        # Create a password display instead of input widget
        self.password_display = Static(">", id="password-display")
        self.password_display.can_focus = True

        self.password_display.visible = False
        self.current_password = ""

        # Create a simple test container
        test_container = Vertical(
            self.output_display,
            self.password_display,
            self.update_button,
            id="pacman-container",
        )

        yield test_container

    async def on_mount(self):
        # Set consistent sizing to match the old TODO widget
        self.output_display.styles.width = 35
        self.output_display.styles.min_width = 35
        self.output_display.styles.max_width = 35
        self.output_display.styles.height = (
            "24"  # Slightly smaller to make room for password input
        )
        self.output_display.styles.overflow = "auto"
        self.output_display.styles.scrollbar_size_vertical = 1
        self.output_display.styles.border = ("round", "white")
        self.output_display.styles.padding = (1, 2)

        # Style password display
        self.password_display.styles.width = 35
        self.password_display.styles.height = 3
        self.password_display.styles.border = ("round", "white")
        self.password_display.styles.margin = (1, 0)

        self.styles.width = 35
        self.styles.min_width = 35
        self.styles.max_width = 35

        container = self.query_one("#pacman-container")
        container.styles.width = 35
        container.styles.min_width = 35
        container.styles.max_width = 35

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Debug input changes to see if text is being captured"""
        if event.input.id == "password-input":
            log(
                f"Input changed: value='{event.value}', length={len(event.value) if event.value else 0}"
            )
        else:
            log(f"Input changed on different widget: {event.input.id}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Debug input submission events"""
        log(
            f"Input submitted event: input_id={event.input.id}, value='{event.value}', length={len(event.value) if event.value else 0}"
        )
        if event.input.id == "password-input" and self.waiting_for_password:
            password = event.value
            log(f"Password input submitted: {len(password)} chars")
            self.password_input.value = ""
            self.password_input.visible = False
            self.password_input.disabled = True
            self.password_input.refresh()
            self.waiting_for_password = False
            self._stored_password = password
            log(
                f"Password stored: {len(self._stored_password)} chars, waiting_for_password: {self.waiting_for_password}"
            )
            self.output_display.update(
                self.output_display.renderable
                + "\n[Password entered - starting update...]"
            )
            # Start the actual pacman update
            await self.start_pacman_update()
        else:
            log(
                f"Input submitted but conditions not met: input_id={event.input.id}, waiting_for_password={self.waiting_for_password}"
            )

    async def show_password_input(self):
        self.waiting_for_password = True
        self.current_password = ""
        self.password_display.visible = True
        self.password_display.update(">")

        # Force refresh
        self.password_display.refresh()
        container = self.query_one("#pacman-container")
        container.refresh()

        self.output_display.update(
            self.output_display.renderable + "\nType your password and press ENTER:"
        )

        # Focus the password display
        self.password_display.focus()

        log(f"Password input ready: waiting_for_password={self.waiting_for_password}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        log(f"Button pressed: {event.button.id}")

        self.output_display.update(
            self.output_display.renderable + f"\n[Button pressed: {event.button.id}]"
        )

        if event.button.id == "pacman-button" and not self._is_running:
            log("Pacman button pressed, starting update")
            await self.run_pacman_update()

    async def run_pacman_update(self):
        """Run sudo pacman -Syu and display output in real-time"""
        if self._is_running:
            return

        self._is_running = True
        self.update_button.disabled = True
        self.update_button.label = "Updating..."
        self.output_display.update("Starting system update...\nChecking sudo access...")

        await self.show_password_input()

        log("Password input requested - waiting for user input...")

        # The actual pacman update will be started by the button press handler
        pass

    async def start_pacman_update(self):
        """Actually start the pacman update process"""
        log(
            f"Starting pacman update with password length: {len(self._stored_password) if self._stored_password else 0}"
        )

        if not self._stored_password:
            self.output_display.update("[x] No password available for update.")
            self._is_running = False
            self.update_button.disabled = False
            self.update_button.label = "Update System"
            return

        try:
            log("Creating pacman subprocess...")
            # First test sudo access with a simple command
            test_process = await asyncio.create_subprocess_exec(
                "sudo",
                "-S",
                "echo",
                "test",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            log("Testing sudo access...")
            log(
                f"Password before encoding: '{self._stored_password}' (length: {len(self._stored_password)})"
            )
            password_input = f"{self._stored_password}\n".encode("utf-8")
            log(
                f"Password after encoding: {password_input} (length: {len(password_input)})"
            )
            test_process.stdin.write(password_input)
            await test_process.stdin.drain()
            test_process.stdin.close()

            await test_process.wait()
            log(f"Sudo test result: {test_process.returncode}")

            if test_process.returncode != 0:
                self.output_display.update(
                    "[x] Sudo access test failed - password may be incorrect"
                )
                return

            # Now run the actual pacman command
            self.process = await asyncio.create_subprocess_exec(
                "sudo",
                "-S",
                "pacman",
                "-Syu",
                "--noconfirm",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                stdin=asyncio.subprocess.PIPE,
            )

            log("Sending password to pacman sudo...")
            # Send the password to stdin with proper newline
            password_input = f"{self._stored_password}\n".encode("utf-8")
            log(
                f"Password being sent: '{self._stored_password}' (length: {len(self._stored_password)})"
            )
            self.process.stdin.write(password_input)
            await self.process.stdin.drain()
            self.process.stdin.close()
            log("Password sent to pacman, stdin closed")

            output_lines = ["Starting pacman update..."]
            log("Starting to read pacman output...")

            # Read output line by line
            while True:
                try:
                    line = await asyncio.wait_for(
                        self.process.stdout.readline(), timeout=2.0
                    )
                    if not line:
                        break

                    decoded_line = line.decode("utf-8", errors="replace").rstrip()

                    if decoded_line.strip():  # Only add non-empty lines
                        output_lines.append(decoded_line)

                        # Update display with last 25 lines
                        display_lines = output_lines[-25:]
                        self.output_display.update("\n".join(display_lines))

                        # Auto-scroll to bottom
                        self.output_display.scroll_end()

                except asyncio.TimeoutError:
                    # Check if process is still running
                    if self.process.returncode is not None:
                        break
                    continue

            # Wait for process to complete
            await self.process.wait()

            if self.process.returncode == 0:
                output_lines.append(
                    "\n[✓] System update completed successfully!\n\nThank you for feeding Tux!"
                )
            else:
                output_lines.append(
                    f"\n[x] Update failed with exit code {self.process.returncode}"
                )

            # Final display update
            display_lines = output_lines[-25:]
            self.output_display.update("\n".join(display_lines))
            self.output_display.scroll_end()

        except Exception as e:
            error_msg = f"[x] Error running pacman update: {str(e)}"
            self.output_display.update(error_msg)
            log(f"Pacman update error: {e}")

        finally:
            # Clean up stored password
            self._stored_password = None
            self._is_running = False
            self.waiting_for_password = False
            self.password_display.visible = False
            self.update_button.disabled = False
            self.update_button.label = "Update System"
            self.process = None

    async def on_key(self, event: Key) -> None:
        log(
            f"Key pressed: '{event.key}', waiting_for_password={self.waiting_for_password}"
        )

        # Handle 'u' key to start update
        if event.key == "u" and not self._is_running and not self.waiting_for_password:
            log("'u' key pressed, starting update")
            await self.run_pacman_update()
            event.stop()
            return

        # Handle password input via key events
        if self.waiting_for_password:
            if event.key == "enter":
                log(
                    f"Enter key pressed. Final password: {len(self.current_password)} chars"
                )
                if self.current_password:
                    self.waiting_for_password = False
                    self._stored_password = self.current_password
                    self.current_password = ""
                    self.password_display.visible = False
                    self.password_display.refresh()
                    log(f"Password entered: {len(self._stored_password)} chars")
                    self.output_display.update(
                        self.output_display.renderable
                        + "\n[Password entered - starting update...]"
                    )
                    # Start the actual pacman update
                    await self.start_pacman_update()
                event.stop()
                return
            elif event.key == "backspace":
                if self.current_password:
                    self.current_password = self.current_password[:-1]
                    self.password_display.update(f">{'*' * len(self.current_password)}")
                event.stop()
                return
            elif len(event.key) == 1 and event.key.isprintable():
                # Add character to password
                self.current_password += event.key
                self.password_display.update(f">{'*' * len(self.current_password)}")
                event.stop()
                return

        # Allow ESC to cancel running update
        if event.key == "escape" and self._is_running and self.process:
            try:
                self.process.terminate()
                self.output_display.update(
                    self.output_display.renderable + "\n\n[x] Update cancelled by user"
                )
            except Exception as e:
                log(f"Error cancelling pacman update: {e}")
            event.stop()


class TuxApp(App):
    """Main Tuxagotchi Textual App"""

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        css_file = os.path.join(script_dir, "styles.css")
        if os.path.exists(css_file):
            self.CSS_PATH = css_file
        else:
            # Fallback for development
            self.CSS_PATH = "styles.css"

    async def on_mount(self) -> None:
        # Preload ascii for better performance
        preload_ascii_frames()

        # Load config for theme colors
        config = load_config()
        self.theme_colors = config["colors"]

        # Pacman update tracking
        self.last_valid_update_time = None
        self.last_checked = datetime.min.replace(tzinfo=timezone.utc)

        # Initialize Tux logic and UI
        self.tux = Tux(username="arch", repo="system-updates")
        self.tux_widget = TuxWidget(self.tux, "pacman-updates")
        self._style_tux_widget()

        # Replace TODO widget with Pacman widget
        self.pacman_widget = PacmanWidget(id="pacman-widget")
        self._style_pacman_widget()

        top_row = Horizontal(self.tux_widget, self.pacman_widget, id="main-container")
        await self.mount(top_row)

        # Updated keybinds bar (removed TODO-specific bindings, added pacman info)
        self.keybinds = Static(
            "[bold][/bold]【q ➡ Quit】【u ➡ Update】【Click Button ➡ Update】【ESC ➡ Cancel Update】",
            id="keybinds",
        )
        self.keybinds.styles.dock = "bottom"
        self.keybinds.styles.height = 1
        self.keybinds.styles.background = "transparent"
        self.keybinds.styles.color = "white"
        self.keybinds.styles.padding = (0, 1)
        await self.mount(self.keybinds)

        # Check for pacman updates every 3 seconds
        self.set_interval(3, self.check_pacman_updates)

    def _style_tux_widget(self) -> None:
        self.tux_widget.styles.padding = (0, 0)
        self.tux_widget.styles.height = 35
        self.tux_widget.styles.width = 50
        self.tux_widget.styles.margin = (0, 0, 0, 0)

    def _style_pacman_widget(self) -> None:
        """Style the pacman widget to match the old TODO widget dimensions"""
        self.pacman_widget.styles.width = 20
        self.pacman_widget.styles.min_width = 20
        self.pacman_widget.styles.max_width = 20
        self.pacman_widget.styles.height = 35
        self.pacman_widget.styles.max_height = 35
        self.pacman_widget.styles.margin = (0, 0, 0, 0)
        self.pacman_widget.styles.padding = (0, 0)

    async def check_pacman_updates(self) -> None:
        now = datetime.now(timezone.utc)
        if now - self.last_checked < timedelta(seconds=3):
            return
        self.last_checked = now

        update_time = await asyncio.to_thread(get_last_pacman_update_time)
        if update_time and update_time != self.last_valid_update_time:
            self.last_valid_update_time = update_time
            self.tux.last_update_time = update_time
            self.tux.update_mood(update_time)
            self.tux_widget.refresh()
            log(f"[✓] Last pacman update: {update_time}")


def generate_css_file():
    """Generate the CSS file with current config colors"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(script_dir, "styles.css")

    # Only generate if it doesn't exist or if we're in development mode
    if not os.path.exists(css_path) or os.path.exists("config.toml"):
        config = load_config()
        colors = config["colors"]
        css = generate_css(colors)

        # Make sure the directory exists
        os.makedirs(os.path.dirname(css_path), exist_ok=True)

        with open(css_path, "w") as f:
            f.write(css)


if __name__ == "__main__":
    generate_css_file()
    app = TuxApp()
    app.run()
