# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import os, gi

from pathlib import Path
from gi.repository import GLib, Gio
from .database_manager import (list_database_albums, insert_file_and_albums, file_exists_in_database)

class MediaWatcher():
    def __init__(self, conn, app):
        self.app = app
        self.conn = conn
        self.dir_monitors = {}
        self.root_dirs = [Path.home() / "Pictures", Path.home() / "Videos"]

        self.db_albums = set(list_database_albums(self.conn))

    def start_media_monitors(self):
        # Pictures Root
        if self.root_dirs[0].exists(): 
            self.monitor_tree(self.root_dirs[0])

        # Videos Root
        if self.root_dirs[1].exists():
            self.monitor_tree(self.root_dirs[1])

    def monitor_tree(self, root: Path):
        for dirpath, dirnames, _ in os.walk(root):
            self.monitor_directory(Path(dirpath))   

    def monitor_directory(self, directory: Path):
        key = str(directory)
        if key in self.dir_monitors:
            return

        gfile = Gio.File.new_for_path(key)
        try:
            mon = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        except Exception as e:
            print(f"Failed to monitor {directory}: {e}")
            return

        mon.connect("changed", self.on_dir_changed)
        self.dir_monitors[key] = mon

    def on_dir_changed(self, monitor, file, other_file, event_type):
        path = file.get_path()
        if not path:
            return

        # If a new directory was created, start monitoring it too (recursive)
        if event_type == Gio.FileMonitorEvent.CREATED and os.path.isdir(path):
            self.monitor_directory(Path(path))
            return

        if not os.path.isfile(path):
            return

        p = Path(path)

        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            GLib.idle_add(self.handle_new_media_path, path)
            return
        else:
            return

    def handle_new_media_path(self, file_path: str):
        try:
            if not os.path.isfile(file_path):
                return False

            p = Path(file_path).resolve()

            root = self.get_root_media_dir(p)
            if root is None:
                return False

            # If the media already exists, do not insert again
            if file_exists_in_database(self.conn, str(p)):
                return False

            # Determine candidate album based on folder under root
            candidate_album = self.album_from_path(root, p)

            # Build album list to link
            albums_to_link = []
            if candidate_album and candidate_album in self.db_albums:
                albums_to_link.append(candidate_album)

            # Insert + link
            insert_file_and_albums(self.conn, str(p), albums_to_link)

            self.db_albums = set(list_database_albums(self.conn))
            self.app.media_paths.append(str(p))
            self.app.on_new_file_created(str(p))

            print(f"Inserted new file: {p} (album candidate: {candidate_album}, linked: {albums_to_link})")

        except Exception as e:
            print("Error handling new media file:", e)

        return False

    def get_root_media_dir(self, p: Path) -> Path | None:
        for root in self.root_dirs:
            try:
                root_resolved = root.resolve()
                if p == root_resolved or root_resolved in p.parents:
                    return root_resolved
            except Exception:
                continue
        return None

    def album_from_path(self, root: Path, p: Path) -> str:
        rel = p.relative_to(root)

        if len(rel.parts) <= 1:
            return root.name

        return rel.parts[0]