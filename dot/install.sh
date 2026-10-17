#!/usr/bin/env bash
# Dot - Installation script for Debian/Ubuntu based systems.
set -Eeuo pipefail

DOT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOT_DEST="/opt/dot"

if [[ "$EUID" -eq 0 ]]; then
    echo "❌ Run this script as your normal desktop user, not with sudo."
    echo "   The script will request sudo only for system-level operations."
    exit 1
fi

INSTALL_USER="${USER}"
INSTALL_GROUP="$(id -gn "$INSTALL_USER")"
DESKTOP_LOWER="${XDG_CURRENT_DESKTOP:-}:${XDG_SESSION_DESKTOP:-}:${DESKTOP_SESSION:-}"
DESKTOP_LOWER="${DESKTOP_LOWER,,}"

on_error() {
    local exit_code=$?
    echo "❌ Installation failed near line ${BASH_LINENO[0]} (exit ${exit_code})." >&2
    echo "   Review the error above before trying again." >&2
    exit "$exit_code"
}
trap on_error ERR

# Remove the exact permissive sudoers rule written by older Dot installers.
# If the file contains additional rules, leave it intact and warn for manual review.
LEGACY_SUDOERS="/etc/sudoers.d/dot"
LEGACY_SUDOERS_RULE="$INSTALL_USER ALL=(ALL) NOPASSWD: /usr/bin/chattr, /usr/bin/chown"
if sudo test -f "$LEGACY_SUDOERS"; then
    LEGACY_SUDOERS_CONTENT="$(sudo cat "$LEGACY_SUDOERS" 2>/dev/null || true)"
    if [[ "$LEGACY_SUDOERS_CONTENT" == "$LEGACY_SUDOERS_RULE" ]]; then
        sudo rm -f "$LEGACY_SUDOERS"
        echo "🔐 Removed Dot's old unrestricted chown/chattr sudoers rule."
    elif sudo grep -Fq 'NOPASSWD: /usr/bin/chattr, /usr/bin/chown' "$LEGACY_SUDOERS"; then
        echo "⚠️  Review $LEGACY_SUDOERS manually: it contains a legacy privileged rule."
    fi
fi

echo "🛡️  Dot - Installation"
echo "======================"

# ----- 0. Validate source -----
if [[ ! -f "$DOT_SRC/main.py" || ! -d "$DOT_SRC/core" ]]; then
    echo "❌ main.py or core/ not found in $DOT_SRC"
    echo "   Run this script from the project's dot/ directory."
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "❌ This installer currently supports Debian/Ubuntu systems using APT."
    echo "   Install the dependencies manually on other distributions."
    exit 1
fi

# ----- 1. Prepare the installation directory -----
sudo mkdir -p "$DOT_DEST"

# Older Dot installers marked source files immutable. Clear those flags before
# copying so that upgrades can succeed. This is scoped to /opt/dot only.
if command -v chattr >/dev/null 2>&1; then
    sudo find "$DOT_DEST" -type f -exec chattr -i {} + 2>/dev/null || true
fi

# Don't copy an installation directory onto itself (for example when the user
# runs `dot install` from the already-installed copy).
if [[ ! "$DOT_SRC" -ef "$DOT_DEST" ]]; then
    echo "📦 Copying files to $DOT_DEST ..."
    if command -v rsync >/dev/null 2>&1; then
        sudo rsync -a \
            --exclude='.venv/' \
            --exclude='data/' \
            --exclude='.git/' \
            --exclude='__pycache__/' \
            --exclude='tests/' \
            --exclude='*.pyc' \
            --exclude='config.json' \
            "$DOT_SRC"/ "$DOT_DEST"/
    else
        shopt -s dotglob nullglob
        for source_item in "$DOT_SRC"/*; do
            item_name="${source_item##*/}"
            case "$item_name" in
                .git|.venv|data|tests|config.json|__pycache__)
                    continue
                    ;;
            esac
            sudo cp -a "$source_item" "$DOT_DEST/"
        done
        shopt -u dotglob nullglob
    fi
fi

# Preserve existing user settings and access history across upgrades.
if [[ ! -f "$DOT_DEST/config.json" && -f "$DOT_SRC/config.json" ]]; then
    sudo cp "$DOT_SRC/config.json" "$DOT_DEST/config.json"
fi
sudo chown -R "$INSTALL_USER:$INSTALL_GROUP" "$DOT_DEST"

# ----- 2. Install system dependencies -----
echo "🔍 Installing system packages ..."
sudo apt-get update
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    python3-venv \
    python3-pip \
    xdotool

# Prefer Ayatana AppIndicator; fall back to the legacy AppIndicator typelib.
if ! sudo apt-get install -y gir1.2-ayatanaappindicator3-0.1; then
    echo "ℹ️  Ayatana bindings unavailable; trying legacy AppIndicator3 ..."
    sudo apt-get install -y gir1.2-appindicator3-0.1
fi

# The GNOME tray extension is optional and package names vary by Ubuntu release.
if [[ "$DESKTOP_LOWER" == *gnome* ]] && apt-cache show gnome-shell-extension-appindicator >/dev/null 2>&1; then
    sudo apt-get install -y gnome-shell-extension-appindicator || \
        echo "⚠️  Could not install the GNOME AppIndicator extension automatically."
fi

# ----- 3. Python environment -----
echo "🐍 Preparing virtual environment ..."
python3 -m venv "$DOT_DEST/.venv" --system-site-packages
"$DOT_DEST/.venv/bin/python" -m pip install --upgrade pip psutil

# ----- 4. User systemd service -----
echo "⚙️  Creating systemd user service ..."
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/dot.service" <<'SERVICE_EOF'
[Unit]
Description=Dot Privacy Indicator
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/opt/dot/.venv/bin/python3 /opt/dot/startup_watchdog.py
Restart=always
RestartSec=2

[Install]
WantedBy=graphical-session.target
SERVICE_EOF

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
    systemctl --user enable --now dot.service || \
        echo "⚠️  Could not enable/start the user service in this session."
fi

# Add a standard XDG autostart entry for every desktop environment. Some
# environments do not activate graphical-session.target, and users may switch
# desktop environments after installing Dot. Starting the same systemd unit
# from both systemd and XDG autostart is safe: `systemctl start` is idempotent.
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/dot.desktop"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_FILE" <<'AUTOSTART_EOF'
[Desktop Entry]
Type=Application
Name=Dot Privacy Indicator
Comment=Start Dot Privacy Indicator
Exec=systemctl --user start dot.service
Terminal=false
AUTOSTART_EOF
chmod 644 "$AUTOSTART_FILE"
echo "🖥️  Configured desktop login autostart: $AUTOSTART_FILE"

# ----- 5. CLI wrapper -----
echo "🔗 Installing CLI wrapper ..."
sudo tee /usr/local/bin/dot >/dev/null <<WRAPPER_EOF
#!/usr/bin/env bash
exec "$DOT_DEST/.venv/bin/python3" "$DOT_DEST/cli.py" "\$@"
WRAPPER_EOF
sudo chmod 755 /usr/local/bin/dot

# ----- 6. Desktop-aware Kill Switch shortcut -----
if "$DOT_DEST/.venv/bin/python3" "$DOT_DEST/cli.py" setup-shortcut; then
    :
else
    echo "⚠️  Could not configure the desktop shortcut automatically."
    echo "   Command: /usr/local/bin/dot kill"
fi

echo
echo "✅ Dot installation steps completed."
echo "   Files:       $DOT_DEST"
echo "   Python env:  $DOT_DEST/.venv"
echo "   Service:     ~/.config/systemd/user/dot.service"
echo "   CLI:         /usr/local/bin/dot"
echo ""
echo "👉 Test the CLI with: dot help"
echo "   Service status: systemctl --user status dot.service"
