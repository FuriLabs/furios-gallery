# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs

import os
import sys
from pathlib import Path
import pyinotify
from concurrent.futures import ThreadPoolExecutor
from furios_gallery.thumbnail_utils import ensure_cache_dir, generate_thumbnail, has_thumbnail

class ThumbnailDaemon:
    WATCH_DIRS = [
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Videos")
    ]

    def __init__(self):
        ensure_cache_dir()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.wm = pyinotify.WatchManager()

    def process_existing_files(self):
        for watch_dir in self.WATCH_DIRS:
            path = Path(watch_dir)
            for file_path in path.rglob("*"):
                if file_path.is_file() and not has_thumbnail(str(file_path)):
                    print(f"Processing existing file: {file_path}")
                    self.executor.submit(generate_thumbnail, str(file_path))

    def run(self):
        print("Starting thumbnail daemon...")
        self.process_existing_files()

        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, daemon):
                self.daemon = daemon

            def process_IN_CLOSE_WRITE(self, event):
                print(f"New file detected: {event.pathname}")
                self.daemon.executor.submit(generate_thumbnail, event.pathname)

        handler = EventHandler(self)

        notifier = pyinotify.Notifier(self.wm, handler)
        mask = pyinotify.IN_CLOSE_WRITE

        for watch_dir in self.WATCH_DIRS:
            self.wm.add_watch(watch_dir, mask, rec=True, auto_add=True)

        print("Watching for new files...")
        notifier.loop()

if __name__ == "__main__":
    daemon = ThumbnailDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
