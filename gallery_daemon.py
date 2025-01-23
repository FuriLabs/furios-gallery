# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs

import os
import sys
import asyncio
from pathlib import Path
import pyinotify
from concurrent.futures import ThreadPoolExecutor
from furios_gallery.thumbnail_utils import ensure_cache_dir, generate_thumbnail, has_thumbnail
from furios_gallery.media_manager import (
    create_connection, create_tables, insert_file_and_albums,
    delete_from_albums
)

class BaseDaemon:
    WATCH_DIRS = [
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Videos")
    ]

    def __init__(self):
        self.wm = pyinotify.WatchManager()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.setup()

    def setup(self):
        pass

    async def run(self):
        raise NotImplementedError

class ThumbnailDaemon(BaseDaemon):
    def setup(self):
        ensure_cache_dir()

    async def process_existing_files(self):
        tasks = []
        for watch_dir in self.WATCH_DIRS:
            path = Path(watch_dir)
            for file_path in path.rglob("*"):
                if file_path.is_file() and not has_thumbnail(str(file_path)):
                    print(f"Processing thumbnail for: {file_path}")
                    tasks.append(self.executor.submit(generate_thumbnail, str(file_path)))
        if tasks:
            await asyncio.get_event_loop().run_in_executor(None, lambda: [t.result() for t in tasks])

    async def run(self):
        print("Starting thumbnail daemon...")
        await self.process_existing_files()

        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, daemon):
                self.daemon = daemon

            def process_IN_CLOSE_WRITE(self, event):
                print(f"Generating thumbnail for: {event.pathname}")
                self.daemon.executor.submit(generate_thumbnail, event.pathname)

        handler = EventHandler(self)
        notifier = pyinotify.AsyncioNotifier(self.wm, asyncio.get_event_loop(), default_proc_fun=handler)
        mask = pyinotify.IN_CLOSE_WRITE
        for watch_dir in self.WATCH_DIRS:
            self.wm.add_watch(watch_dir, mask, rec=True, auto_add=True)

        while True:
            await asyncio.sleep(1)

class DatabaseDaemon(BaseDaemon):
    def setup(self):
        app_dir = Path(os.path.expanduser("~/.local/share/io.FuriOS.Gallery"))
        app_dir.mkdir(parents=True, exist_ok=True)
        self.conn = create_connection(str(app_dir / "gallery-albums.db"))
        if self.conn is not None:
            create_tables(self.conn)

    async def process_existing_files(self):
        tasks = []
        cur = self.conn.cursor()
        for watch_dir in self.WATCH_DIRS:
            path = Path(watch_dir)
            for file_path in path.rglob("*"):
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4', '.mkv']:
                    cur.execute("SELECT file_id FROM files WHERE file_path = ?", (str(file_path),))
                    if not cur.fetchone():
                        print(f"Adding to database: {file_path}")
                        file_type = 'video' if file_path.suffix.lower() in ['.mp4', '.mkv'] else 'picture'
                        tasks.append(self.executor.submit(insert_file_and_albums, self.conn, str(file_path), file_type, [file_path.parent.name]))
        if tasks:
            await asyncio.get_event_loop().run_in_executor(None, lambda: [t.result() for t in tasks])

    async def run(self):
        print("Starting database daemon...")
        await self.process_existing_files()

        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, daemon):
                self.daemon = daemon

            def process_IN_CLOSE_WRITE(self, event):
                if Path(event.pathname).suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4', '.mkv']:
                    cur = self.daemon.conn.cursor()
                    cur.execute("SELECT file_id FROM files WHERE file_path = ?", (event.pathname,))
                    if not cur.fetchone():
                        print(f"Adding to database: {event.pathname}")
                        file_type = 'video' if Path(event.pathname).suffix.lower() in ['.mp4', '.mkv'] else 'picture'
                        self.daemon.executor.submit(insert_file_and_albums,
                                                    self.daemon.conn,
                                                    event.pathname,
                                                    file_type,
                                                    [Path(event.pathname).parent.name])

            def process_IN_DELETE(self, event):
                print(f"Removing from database: {event.pathname}")
                self.daemon.executor.submit(delete_from_albums, self.daemon.conn, event.pathname)

        handler = EventHandler(self)
        notifier = pyinotify.AsyncioNotifier(self.wm, asyncio.get_event_loop(), default_proc_fun=handler)
        mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_DELETE
        for watch_dir in self.WATCH_DIRS:
            self.wm.add_watch(watch_dir, mask, rec=True, auto_add=True)

        while True:
            await asyncio.sleep(1)

async def main():
    thumbnail_daemon = ThumbnailDaemon()
    database_daemon = DatabaseDaemon()

    await asyncio.gather(
        thumbnail_daemon.run(),
        database_daemon.run()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
