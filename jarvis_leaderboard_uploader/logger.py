"""
Colored, structured logging for jarvis_leaderboard_uploader.
Gives users clear step-by-step progress and pinpoints the exact
location of any error (file + line where possible).
"""

import sys
import traceback
import logging
from typing import Optional


def _supports_colour() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_USE_COLOR = _supports_colour()


class Colour:
    RESET   = "\033[0m"  if _USE_COLOR else ""
    BOLD    = "\033[1m"  if _USE_COLOR else ""
    RED     = "\033[91m" if _USE_COLOR else ""
    YELLOW  = "\033[93m" if _USE_COLOR else ""
    GREEN   = "\033[92m" if _USE_COLOR else ""
    CYAN    = "\033[96m" if _USE_COLOR else ""
    MAGENTA = "\033[95m" if _USE_COLOR else ""
    DIM     = "\033[2m"  if _USE_COLOR else ""


class JarvisLogger:
    """
    A lightweight logger that wraps Python's standard logging but adds
    colour, step counters, and structured error blocks.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._step = 0
        self._log = logging.getLogger("jarvis_leaderboard_uploader")
        if not self._log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._log.addHandler(handler)
        self._log.setLevel(logging.DEBUG if verbose else logging.WARNING)
        self._log.propagate = False

    def step(self, message: str) -> None:
        self._step += 1
        prefix = f"{Colour.CYAN}{Colour.BOLD}[Step {self._step}]{Colour.RESET} "
        self._log.info(f"{prefix}{message}")

    def success(self, message: str) -> None:
        self._log.info(f"  {Colour.GREEN}✓{Colour.RESET}  {message}")

    def info(self, message: str) -> None:
        self._log.info(f"  {Colour.DIM}→{Colour.RESET}  {message}")

    def warning(self, message: str) -> None:
        self._log.warning(
            f"  {Colour.YELLOW}⚠{Colour.RESET}  {Colour.YELLOW}{message}{Colour.RESET}"
        )

    def error(
        self,
        message: str,
        *,
        hint: Optional[str] = None,
        exc: Optional[Exception] = None,
        filepath: Optional[str] = None,
        line: Optional[int] = None,
    ) -> None:
        sep = f"{Colour.RED}{'─' * 60}{Colour.RESET}"
        self._log.error(sep)
        self._log.error(
            f"  {Colour.RED}{Colour.BOLD}✗  ERROR{Colour.RESET}  {message}"
        )
        if filepath:
            loc = f"{filepath}:{line}" if line else filepath
            self._log.error(f"  {Colour.MAGENTA}Location:{Colour.RESET} {loc}")
        if hint:
            self._log.error(f"  {Colour.YELLOW}Hint:{Colour.RESET}     {hint}")
        if exc:
            tb = traceback.format_exc()
            self._log.error(f"\n{Colour.DIM}{tb}{Colour.RESET}")
        self._log.error(sep)

    def section(self, title: str) -> None:
        bar = "═" * 60
        self._log.info(f"\n{Colour.CYAN}{bar}\n  {title}\n{bar}{Colour.RESET}")

    def reset_steps(self) -> None:
        self._step = 0