"""Register SIGINT/SIGTERM handlers that trigger the same cleanup path as Ctrl+C."""

from __future__ import annotations

import signal
from typing import Callable, List, Optional

_installed = False
_cleanup_fns: List[Callable[[], None]] = []


def register_cleanup(fn: Callable[[], None]) -> None:
    _cleanup_fns.append(fn)


def install_interrupt_handlers() -> None:
    global _installed
    if _installed:
        return
    _installed = True

    def _handler(signum, frame):  # noqa: ARG001
        for fn in reversed(_cleanup_fns):
            try:
                fn()
            except Exception:
                pass
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, _handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handler)
