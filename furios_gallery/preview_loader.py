# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Bardia Moshiri <bardia@furilabs.com>

from collections import OrderedDict
from itertools import count
from queue import PriorityQueue
from threading import Lock, Thread
from PIL import Image, ImageOps
from gi.repository import GLib

class PreviewLoader:
    def __init__(self):
        self._lock = Lock()
        self._queue = PriorityQueue()
        self._sequence = count()
        self._pending = {}
        self._cache = OrderedDict()
        self._max_cached = 12
        for i in range(2):
            Thread(target=self.worker, name=f"gallery-preview-{i}", daemon=True).start()

    def request(self, path, size, callback=None, priority=10):
        key = (path, size)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
            else:
                entry = self._pending.get(key)
                if entry is None:
                    entry = {"priority": priority, "generation": 0, "callbacks": []}
                    self._pending[key] = entry
                    self._queue.put((priority, next(self._sequence), key, 0))
                elif priority < entry["priority"]:
                    entry["priority"] = priority
                    entry["generation"] += 1
                    self._queue.put((priority, next(self._sequence), key, entry["generation"]))
                if callback is not None:
                    entry["callbacks"].append(callback)
        if cached is not None and callback is not None:
            GLib.idle_add(callback, cached)

    def worker(self):
        while True:
            priority, _, key, generation = self._queue.get()
            with self._lock:
                entry = self._pending.get(key)
                if entry is None or entry["generation"] != generation:
                    continue
                entry["priority"] = -1
            try:
                decoded = self.load_preview(*key)
            except Exception as exc:
                print(f"Failed to load gallery preview {key[0]}: {exc}", flush=True)
                decoded = None
            with self._lock:
                entry = self._pending.pop(key, None)
                callbacks = entry["callbacks"] if entry else []
                if decoded is not None:
                    self._cache[key] = decoded
                    self._cache.move_to_end(key)
                    while len(self._cache) > self._max_cached:
                        self._cache.popitem(last=False)
            if decoded is not None:
                for callback in callbacks:
                    GLib.idle_add(callback, decoded)

    def load_preview(self, path, max_dimension):
        with Image.open(path) as source:
            source.draft("RGB", (max_dimension, max_dimension))
            image = ImageOps.exif_transpose(source)
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.BILINEAR)
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            return image.width, image.height, image.tobytes()

_PREVIEW_LOADER = None

def get_preview_loader():
    global _PREVIEW_LOADER
    if _PREVIEW_LOADER is None:
        _PREVIEW_LOADER = PreviewLoader()
    return _PREVIEW_LOADER
