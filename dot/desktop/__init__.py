"""Desktop detection and backend selection for Dot.

Add new environment-specific integrations here; callers in ``core`` should
use ``get_desktop_backend`` instead of checking GNOME/LXQt themselves.
"""

import os
import re
from typing import Mapping, Optional

from desktop.base import DesktopBackend
from desktop.gnome import GnomeBackend


def _normalize_desktop_name(value: str) -> str:
    tokens = set(re.split(r"[^a-z0-9]+", value.casefold()))

    # Check explicit desktop identifiers rather than substring-matching distro
    # names (for example, "xubuntu" must not be mistaken for Ubuntu GNOME).
    is_gnome = any(
        token == "gnome" or token.startswith("gnome-")
        for token in tokens
    )
    if is_gnome or "ubuntu" in tokens:
        return "gnome"
    if "lxqt" in tokens:
        return "lxqt"
    if "kde" in tokens or "plasma" in tokens:
        return "kde"
    if "xfce" in tokens or "xubuntu" in tokens:
        return "xfce"
    if "mate" in tokens:
        return "mate"
    if "cinnamon" in tokens:
        return "cinnamon"
    if "pantheon" in tokens:
        return "pantheon"
    return "unknown"


def detect_desktop_name(environ: Optional[Mapping[str, str]] = None) -> str:
    """Detect the desktop session from standard session environment variables.

    Prefer XDG_CURRENT_DESKTOP and consult legacy variables only when newer
    ones are unavailable/unrecognized. This avoids combining conflicting
    values left over from an earlier desktop session.
    """
    env = os.environ if environ is None else environ
    for key in ("XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION"):
        value = env.get(key, "").strip()
        if not value:
            continue
        normalized = _normalize_desktop_name(value)
        if normalized != "unknown":
            return normalized
        # An explicit but unfamiliar current desktop is more trustworthy than
        # a potentially stale legacy session variable.
        if key == "XDG_CURRENT_DESKTOP":
            return "unknown"
    return "unknown"


def get_desktop_backend(
    desktop_name: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> DesktopBackend:
    """Return a backend for the detected or explicitly supplied desktop.

    ``desktop_name`` is useful for tests and for future callers that already
    know the session. Unsupported environments receive a safe generic backend.
    """
    name = (desktop_name or detect_desktop_name(environ)).casefold()
    if name in {"gnome", "ubuntu"}:
        return GnomeBackend()
    return DesktopBackend(name or "unknown")


__all__ = ["DesktopBackend", "GnomeBackend", "detect_desktop_name", "get_desktop_backend"]
