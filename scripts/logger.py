"""Simple Rich console logger for CLI scripts."""

from dataclasses import dataclass

from rich.console import Console
from rich.markup import escape


@dataclass(frozen=True)
class RichLogger:
    """Small styled logger for human-readable CLI output."""

    name: str
    console: Console

    def info(self, message: str) -> None:
        """Print an informational message."""
        self.console.print(f"[bold blue]INFO[/bold blue] \\[{escape(self.name)}] {message}")

    def warning(self, message: str) -> None:
        """Print a warning message."""
        self.console.print(
            f"[bold yellow]WARNING[/bold yellow] \\[{escape(self.name)}] {message}"
        )

    def error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[bold red]ERROR[/bold red] \\[{escape(self.name)}] {message}")


def get_logger(name: str) -> RichLogger:
    """Return a simple Rich console logger."""
    return RichLogger(name=name, console=Console())
