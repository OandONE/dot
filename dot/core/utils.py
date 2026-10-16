import importlib
import os
import subprocess


def get_install_dir():
    """
    Return the root directory where Dot is installed.
    """
    return os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )


def get_main_script():
    return os.path.join(
        get_install_dir(),
        "main.py"
    )


def get_autostart_dir():
    return os.path.expanduser(
        "~/.config/autostart"
    )


def get_autostart_file():
    return os.path.join(
        get_autostart_dir(),
        "dot.desktop"
    )


def is_autostart_enabled():
    """Return True if Dot's systemd user service is enabled."""
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "is-enabled",
                "dot.service"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        return result.returncode == 0 and result.stdout.strip() == "enabled"

    except (subprocess.SubprocessError, OSError):
        return False


def set_autostart(enabled):
    """
    Enable or disable Dot's systemd user service.

    This changes whether Dot starts automatically on login.
    It intentionally does NOT start/stop the currently running Dot process.
    """
    try:
        command = (
            ["systemctl", "--user", "enable", "dot.service"]
            if enabled
            else ["systemctl", "--user", "disable", "dot.service"]
        )

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10
        )

        return result.returncode == 0

    except (subprocess.SubprocessError, OSError):
        return False

def update_desktop_entry():
    """
    Update the application launcher entry.
    """

    desktop_dir = os.path.expanduser(
        "~/.local/share/applications"
    )

    desktop_file = os.path.join(
        desktop_dir,
        "dot.desktop"
    )

    os.makedirs(
        desktop_dir,
        exist_ok=True
    )

    main_script = get_main_script()

    content = f"""[Desktop Entry]
Type=Application
Name=Dot
Comment=Privacy Indicator - Monitor microphone and camera access
Exec=/usr/bin/python3 {main_script}
Icon=security-high
StartupNotify=false
Terminal=false
Categories=Utility;Security;
Keywords=privacy;microphone;camera;indicator;monitor;
"""

    with open(
        desktop_file,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(content)

    os.chmod(
        desktop_file,
        0o755
    )

    subprocess.run(
        [
            "update-desktop-database",
            desktop_dir
        ],
        capture_output=True,
        check=False
    )


def detect_distro():
    try:
        with open(
            "/etc/os-release",
            encoding="utf-8"
        ) as f:

            for line in f:
                if line.startswith("ID="):
                    distro = (
                        line.split("=")[1]
                        .strip()
                        .strip('"')
                    )

                    if "ubuntu" in distro:
                        return "ubuntu"

                    if "debian" in distro:
                        return "debian"

    except OSError:
        pass

    return "other"


def get_appindicator_module():
    """Return the first AppIndicator binding that can actually be imported.

    Prefer Ayatana on systems where it is available, but do not infer library
    availability from the Linux distribution name alone.
    """
    try:
        import gi
    except ImportError as exc:
        raise RuntimeError(
            "PyGObject is unavailable; install the python3-gi system package."
        ) from exc

    errors = []
    for module_name, version in (
        ("AyatanaAppIndicator3", "0.1"),
        ("AppIndicator3", "0.1"),
    ):
        try:
            gi.require_version(module_name, version)
            importlib.import_module("gi.repository." + module_name)
            return module_name, version
        except (ValueError, ImportError, OSError) as exc:
            errors.append(f"{module_name}: {exc}")

    details = "; ".join(errors)
    raise RuntimeError(
        "No usable AppIndicator binding was found. Install Ayatana or "
        f"legacy AppIndicator3 bindings. Details: {details}"
    )
