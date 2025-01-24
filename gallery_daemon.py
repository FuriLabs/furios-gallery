# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs

import os
import sys
from pathlib import Path
from gi.repository import GLib
import pyinotify
from concurrent.futures import ThreadPoolExecutor
from furios_gallery.thumbnail_utils import ensure_cache_dir, generate_thumbnail, has_thumbnail
from furios_gallery.media_manager import (
    create_connection, create_tables, insert_file_and_albums,
    delete_from_albums, extract_file_date, get_file_creation_date
)

class BaseDaemon:
    WATCH_DIRS = [
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Videos")
    ]

    PICTURE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.svg'}
    VIDEO_FORMATS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

    def __init__(self, loop):
        super().__init__()
        self.wm = pyinotify.WatchManager()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = loop
        self.setup()

    def setup(self):
        pass

    def run(self):
        raise NotImplementedError

class ThumbnailDaemon(BaseDaemon):
    def setup(self):
        ensure_cache_dir()

    def process_existing_files(self):
        tasks = []

        def process_files():
            for watch_dir in self.WATCH_DIRS:
                path = Path(watch_dir)
                for file_path in path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in (self.PICTURE_FORMATS | self.VIDEO_FORMATS):
                        if not has_thumbnail(str(file_path)):
                            print(f"Processing thumbnail for: {file_path}")
                            tasks.append(self.executor.submit(generate_thumbnail, str(file_path)))

            if tasks:
                for task in tasks:
                    task.result()
            return False

        GLib.idle_add(process_files)

    def run(self):
        print("Starting thumbnail daemon...")
        self.process_existing_files()

        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, daemon):
                super().__init__()
                self.daemon = daemon

            def process_IN_CLOSE_WRITE(self, event):
                if Path(event.pathname).suffix.lower() in (self.daemon.PICTURE_FORMATS | self.daemon.VIDEO_FORMATS):
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

class DatabaseDaemon(BaseDaemon):
    def setup(self):
        app_dir = Path(os.path.expanduser("~/.local/share/io.FuriOS.Gallery"))
        app_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(app_dir / "gallery-albums.db")
        conn = create_connection(self.db_path)
        if conn is not None:
            create_tables(conn)
            conn.close()

    def _process_file(self, file_path, file_type, albums):
        conn = create_connection(self.db_path)
        try:
            insert_file_and_albums(conn, str(file_path), file_type, albums)
        finally:
            conn.close()

    def process_existing_files(self):
        tasks = []
        conn = create_connection(self.db_path)

        def process_files():
            for watch_dir in self.WATCH_DIRS:
                path = Path(watch_dir)
                for file_path in path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in (self.PICTURE_FORMATS | self.VIDEO_FORMATS):
                        if not has_thumbnail(str(file_path)):
                            print(f"Processing thumbnail for: {file_path}")
                            tasks.append(self.executor.submit(generate_thumbnail, str(file_path)))

            if tasks:
                for task in tasks:
                    task.result()
            return False

        GLib.idle_add(process_files)

    def process_existing_files(self):
        tasks = []
        conn = create_connection(self.db_path)
        try:
            cur = conn.cursor()
            for watch_dir in self.WATCH_DIRS:
                path = Path(watch_dir)
                for file_path in path.rglob("*"):
                    file_suffix = file_path.suffix.lower()
                    if file_suffix in (self.PICTURE_FORMATS | self.VIDEO_FORMATS):
                        cur.execute("SELECT file_id FROM files WHERE file_path = ?", (str(file_path),))
                        if not cur.fetchone():
                            print(f"Adding to database: {file_path}")
                            file_type = 'video' if file_suffix in self.VIDEO_FORMATS else 'picture'
                            albums = [file_path.parent.name]
                            if file_type == "video":
                                albums.append("Videos")
                            if file_type == "picture":
                                albums.append("Pictures")
                            albums.append("Recents")
                            tasks.append((file_path, file_type, albums))
        finally:
            conn.close()

        if tasks:
            def process_tasks():
                for task in tasks:
                    self.executor.submit(self._process_file, *task).result()
                print("Finished processing existing files.")
                return False

            GLib.idle_add(process_tasks)

    def run(self):
        print("Starting database daemon...")
        self.process_existing_files()

        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, daemon):
                super().__init__()
                self.daemon = daemon

            def process_IN_CLOSE_WRITE(self, event):
                file_suffix = Path(event.pathname).suffix.lower()
                if file_suffix in (self.daemon.PICTURE_FORMATS | self.daemon.VIDEO_FORMATS):
                    conn = create_connection(self.daemon.db_path)
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT file_id FROM files WHERE file_path = ?", (event.pathname,))
                        if not cur.fetchone():
                            print(f"Adding to database: {event.pathname}")
                            file_type = 'video' if file_suffix in self.daemon.VIDEO_FORMATS else 'picture'
                            albums = [Path(event.pathname).parent.name]
                            if file_type == "video":
                                albums.append("Videos")
                            if file_type == "picture":
                                albums.append("Pictures")
                            albums.append("Recents")
                            self.daemon.executor.submit(
                                self.daemon._process_file,
                                Path(event.pathname),
                                file_type,
                                albums
                            )
                    finally:
                        conn.close()

            def process_IN_DELETE(self, event):
                print(f"Removing from database: {event.pathname}")
                conn = create_connection(self.daemon.db_path)
                try:
                    delete_from_albums(conn, event.pathname)
                finally:
                    conn.close()

        handler = EventHandler(self)

        notifier = pyinotify.Notifier(self.wm, default_proc_fun=handler)
        mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_DELETE
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
    database_daemon = DatabaseDaemon(main_loop)

    thumbnail_daemon.run()
    database_daemon.run()

    main_loop.run()

if __name__ == "__main__":
    main_loop = GLib.MainLoop()
    try:
        main(main_loop)
    except KeyboardInterrupt:
        print("Shutting down...")
        main_loop.quit()
        sys.exit(0)
