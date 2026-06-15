# 🟢 Dot - Privacy Indicator for Linux

> **Take back control of your privacy.**  
> A sleek system tray indicator that shows you exactly when apps are spying through your microphone or camera.

<p align="center">
  <img src="screenshots/dot-tray.png" alt="Dot in system tray" width="400"/>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🟢 **Green Dot** | A single app is using your device |
| 🟠 **Orange Dot** | Multiple apps are accessing your device simultaneously |
| ⚪ **Gray Dot** | All clear — no activity detected |
| 📊 **History Log** | SQLite database with timestamps, app names, and duration |
| ⚙️ **Settings GUI** | Enable/disable monitoring per device, customize colors with live preview |
| 🎨 **Color Picker** | Built-in color chooser for each indicator state |
| ⏱️ **Configurable Check Interval** | Adjust how often Dot checks for device access (0.1s - 5s) |
| 🚀 **Auto-start Toggle** | Enable/disable run on boot from Settings |
| 🔍 **App Menu Entry** | Search "dot" in Activities to launch |
| 🔒 **Single Instance** | Only one Dot runs at a time |
| 🐧 **Native Linux** | Built with GTK3 and AppIndicator, integrates with GNOME/Ubuntu |

---

## 🎯 Why Dot?

Android 12 introduced the famous green dot indicator. iOS has it. Windows has it.  
**Linux desktop didn't — until now.**

Dot monitors **PipeWire/PulseAudio streams** and **video devices** in real-time.
If any app accesses your microphone or camera, you'll know immediately.

---

## 📸 Screenshots

| System Tray | Menu | History | Settings |
|-------------|------|---------|----------|
| ![Tray](screenshots/tray.png) | ![Menu](screenshots/menu.png) | ![History](screenshots/history.png) | ![Settings](screenshots/settings.png) |

---

## 🛠️ Tech Stack

- **Python 3** — Core logic
- **GTK3 + AppIndicator3** — Native Linux UI
- **SQLite3** — Lightweight local logging
- **PipeWire / D-Bus** — Audio/video stream monitoring
- **psutil** — Process information
- **YAML** — User configuration
- **Cairo** — Color preview rendering

---

## 📦 Installation

### ۱. پیش‌نیازها
```bash
sudo apt install gir1.2-appindicator3-0.1 python3-pip python3-venv xdotool -y
```

### ۲. Clone و اجرا
```bash
git clone https://github.com/OandONE/dot.git && cd dot/dot
python3 -m venv .venv && source .venv/bin/activate
pip install psutil pyyaml pygobject
python3 main.py
```

### ۳. برای دفعات بعد
```bash
cd dot/dot && source .venv/bin/activate && python3 main.py
```

## 🎨 Configuration

Edit `config.yaml` or use the built-in Settings GUI:

```yaml
devices:
  microphone: true
  camera: true
  location: false        # coming soon
  screenshare: false     # coming soon

colors:
  active: "#00FF00"      # Green - single app
  multiple: "#FFA500"    # Orange - multiple apps
  idle: "#808080"        # Gray - no activity

settings:
  check_interval: 0.8    # seconds (0.1 - 5.0)
  auto_delete_logs: 30   # days
```

---

## 📊 How It Works

```mermaid
graph TD
    A[PipeWire / D-Bus] -->|Stream events| B[Watcher]
    B -->|Check foreground| C[Detector]
    B -->|Log access| D[SQLite Database]
    B -->|Get status| E[Indicator]
    E -->|Show dot| F[System Tray]
    D -->|Read history| G[History Window]
    H[config.yaml] -->|User settings| B
    H -->|Custom colors| E
    I[Settings GUI] -->|Save| H
    H -->|Reload| B
```

---

## 🚧 Roadmap

### v1.3 (Next)
- [ ] 🛡️ **Secure installation** (`install.sh` + systemd service + `chattr` protection)

### v2.0
- [ ] 🔔 **Desktop notifications** on device access
- [ ] 🚫 **Kill Switch** (keyboard shortcut + menu button)
- [ ] 📍 **Location monitoring** (GPS / GeoClue)
- [ ] 🖥️ **Screenshare detection** (PipeWire video streams)
- [ ] 📈 **Statistics dashboard**
- [ ] 🌐 **Web panel** (localhost with authentication)
- [ ] 🎨 **Custom themes**
- [ ] 📦 **Debian/Flatpak/Snap** packages

---

## 🤝 Contributing

Pull requests are welcome!  
Found a bug? Open an [issue](https://github.com/OandONE/Dot/issues).

### Development

```bash
git clone https://github.com/OandONE/dot.git
cd dot/dot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

---

## 📄 License

MIT © [OandONE] (2026)

---

## 🙏 Acknowledgments

- Inspired by Android 12 Privacy Indicators
- Built for the Linux community with ❤️
- Thanks to PipeWire, GTK, and the open-source community

---

<p align="center">
  <sub>If this project helped you, consider giving it a ⭐</sub>
</p>
