"""Common interface for desktop-environment-specific features.

Core monitoring code should depend on this interface rather than calling a
particular desktop's D-Bus API directly.
"""

from typing import Tuple


class DesktopBackend:
    """Safe fallback implementation for unsupported/unknown desktops."""

    def __init__(self, name: str = "unknown") -> None:
        self.name = name

    def is_foreground_process(self, pid: int) -> bool:
        """Return whether *pid* belongs to the focused application.

        The generic backend deliberately returns False because there is no
        portable, desktop-independent way to identify the focused window.
        """
        return False

    def register_kill_switch_shortcut(
        self, command: str, binding: str = "<Ctrl><Shift>K"
    ) -> Tuple[bool, str]:
        """Register a desktop shortcut when the environment supports it."""
        return False, (
            f"Automatic shortcut registration is not implemented for the "
            f"{self.name} desktop. Configure {binding} manually to run: {command}"
        )

    def stop_screenshare(self) -> Tuple[bool, str]:
        """Attempt to stop screen sharing, if supported by the desktop."""
        return False, (
            f"Automatic screen-sharing control is not implemented for "
            f"the {self.name} desktop. Stop sharing from the application."
        )
