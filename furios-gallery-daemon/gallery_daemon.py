#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import os
import sys
from pathlib import Path
from gi.repository import GLib
import pyinotify
from concurrent.futures import ThreadPoolExecutor
from furios_gallery.thumbnail_utils import ensure_cache_dir, generate_thumbnail, has_thumbnail
from furios_gallery.media_manager import (
    PICTURE_EXTENSIONS, VIDEO_EXTENSIONS, extract_extension, check_file_integrity
)
from furios_gallery.database_manager import should_skip_path, is_svg_file

class ThumbnailDaemon:
    WATCH_DIRS = [
        os.path.expanduser("~")
    ]

    def __init__(self, loop):
        self.wm = pyinotify.WatchManager()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = loop
        self.setup()

    def setup(self):
        ensure_cache_dir()

    def should_process_file(self, file_path):
        """Check if a file should be processed (not a dotfile, not SVG)"""
        path_str = str(file_path)

        # Skip dotfiles and files in dot directories
        if should_skip_path(path_str):
            return False

        # Skip SVG files
        if is_svg_file(path_str):
            return False

        # Skip if filename starts with dot
        if Path(path_str).name.startswith('.'):
            return False
        return True

    def run(self):
        print("Starting thumbnail daemon...")

        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, daemon):
                super().__init__()
                self.daemon = daemon

            def process_IN_CLOSE_WRITE(self, event):
                if (self.daemon.should_process_file(event.pathname) and
                    extract_extension(event.pathname) in (PICTURE_EXTENSIONS + VIDEO_EXTENSIONS)):
                    print(f"Generating thumbnail for: {event.pathname}")
                    self.daemon.executor.submit(generate_thumbnail, event.pathname)

        handler = EventHandler(self)
        notifier = pyinotify.Notifier(self.wm, default_proc_fun=handler)
        mask = pyinotify.IN_CLOSE_WRITE
        for watch_dir in self.WATCH_DIRS:
            self.wm.add_watch(watch_dir, mask, rec=True, auto_add=True)

        def glib_inotify_handler(fd, condition):
            if condition == GLib.IO_IN:
                notifier.process_events()
                if notifier.check_events():
                    notifier.read_events()
                    notifier.process_events()
            return True

        GLib.io_add_watch(notifier._fd, GLib.IO_IN, glib_inotify_handler)

def main(main_loop):
    thumbnail_daemon = ThumbnailDaemon(main_loop)
    thumbnail_daemon.run()
    main_loop.run()

if __name__ == "__main__":
    main_loop = GLib.MainLoop()

    try:
        main(main_loop)
    except KeyboardInterrupt:
        print("Shutting down...")
        main_loop.quit()
        sys.exit(0)
