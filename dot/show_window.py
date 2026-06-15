import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from ui.windows import HistoryWindow, SettingsWindow

if len(sys.argv) > 1:
    if sys.argv[1] == "history":
        win = HistoryWindow()
    elif sys.argv[1] == "settings":
        win = SettingsWindow()
    else:
        sys.exit(1)
    
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
