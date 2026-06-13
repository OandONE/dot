import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib
from core.config import load_config
from core.watcher import Watcher
from ui.indicator import DotIndicator

def main():
    config = load_config()
    watcher = Watcher(config)
    
    GLib.timeout_add(config['settings']['check_interval'] * 1000, watcher.check_all)
    
    indicator = DotIndicator(config, watcher)
    Gtk.main()

if __name__ == "__main__":
    main()
