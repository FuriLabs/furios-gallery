# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import fnmatch
from pathlib import Path
import os, time
from PIL import Image, ExifTags
import datetime
from datetime import datetime
import pyinotify
import pyinotify
import threading
import sqlite3

def extract_file_date(filepath):
    try:
        if filepath.lower().endswith(('.jpg', '.jpeg')):
            with Image.open(filepath) as img:
                exif_data = img._getexif()
                if exif_data:
                    date_str = exif_data.get(36867)
                    if date_str:
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"Error reading EXIF data from {filepath}: {e}")

    stat = os.stat(filepath)
    return datetime.fromtimestamp(stat.st_mtime)

def get_file_creation_date(file_path):
    if not os.path.exists(file_path):
        return "File does not exist"

    creation_time = os.path.getctime(file_path)

    time_struct = time.localtime(creation_time)

    month = time.strftime('%b', time_struct)
    day = int(time.strftime('%d', time_struct))
    year = time.strftime('%Y', time_struct)

    if 11 <= day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

    readable_time = f"{month} {day}{suffix}, {year}"
    return readable_time

# ************* Database Management ************* #
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

def create_tables(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_type TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS albums (
            album_id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_name TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_albums (
            file_id INTEGER NOT NULL,
            album_id INTEGER NOT NULL,
            PRIMARY KEY (file_id, album_id),
            FOREIGN KEY (file_id) REFERENCES files(file_id),
            FOREIGN KEY (album_id) REFERENCES albums(album_id)
        );
        """)
        print("Tables created successfully")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

    populate_database(conn)

def populate_database(conn):
    pictures_root = Path.home() / 'Pictures'
    videos_root = Path.home() / 'Videos'

    media_items = []

    def process_directory(directory, file_type, extensions):
        for subdir, dirs, files in os.walk(directory):
            album_name = os.path.basename(subdir)
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(subdir, file)
                    albums = [album_name, "Recents"]
                    media_items.append((file_path, file_type, albums))

    process_directory(pictures_root, 'picture', '*.jpg')
    process_directory(videos_root, 'video', '*.mkv')

    for file_path, file_type, albums in media_items:
        insert_file_and_albums(conn, file_path, file_type, albums)

    print(f"Processed {len(media_items)} media files.")

def insert_file(conn, file_path, file_type):
    cur = conn.cursor()
    cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
    exists = cur.fetchone()
    if exists:
        return exists[0]
    else:
        sql = "INSERT INTO files (file_path, file_type) VALUES (?, ?)"
        cur.execute(sql, (file_path, file_type))
        conn.commit()
        return cur.lastrowid

def insert_file_album(conn, file_id, album_id):
    cur = conn.cursor()
    sql = "INSERT OR IGNORE INTO file_albums (file_id, album_id) VALUES (?, ?)"
    cur.execute(sql, (file_id, album_id))
    conn.commit()

def insert_file_and_albums(conn, file_path, file_type, albums):
    if "Recents" not in albums:
        albums.append("Recents")
    if file_type == "video" and "Videos" not in albums:
        albums.append("Videos")
    if file_type == "picture" and "Pictures" not in albums:
        albums.append("Pictures")
    file_id = insert_file(conn, file_path, file_type)
    for album in set(albums):
        album_id = insert_or_get_album(conn, album)
        insert_file_album(conn, file_id, album_id)

def insert_or_get_album(conn, album_name):
    cursor = conn.cursor()
    cursor.execute("SELECT album_id FROM albums WHERE album_name = ?", (album_name,))
    album = cursor.fetchone()
    if album:
        return album[0]
    else:
        cursor.execute("INSERT INTO albums (album_name) VALUES (?)", (album_name,))
        conn.commit()
        return cursor.lastrowid

def list_database_albums(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT album_name FROM albums")
        albums = cursor.fetchall()
        return [album[0] for album in albums]
    except Exception as e:
        print(f"Error fetching albums: {e}")
        return []

def get_album_database_paths(conn, album_name):
    cur = conn.cursor()
    cur.execute("""
        SELECT file_path FROM files
        JOIN file_albums ON files.file_id = file_albums.file_id
        JOIN albums ON file_albums.album_id = albums.album_id
        WHERE albums.album_name = ?
    """, (album_name,))

    file_paths = [row[0] for row in cur.fetchall()]

    sorted_paths = sorted(file_paths, key=lambda path: os.path.getmtime(path))

    return sorted_paths

def get_album_media_paths(conn, album_name):
    try:
        cur = conn.cursor()
        query = """
        SELECT file_path FROM files
        JOIN file_albums ON files.file_id = file_albums.file_id
        JOIN albums ON file_albums.album_id = albums.album_id
        WHERE albums.album_name = ?
        """
        cur.execute(query, (album_name,))
        rows = cur.fetchall()

        media_paths = [row[0] for row in rows]

        if album_name.lower() in ['pictures', 'recents']:
            media_paths.extend(get_album_database_paths(conn, "Pictures"))
        if album_name.lower() in ['videos', 'recents']:
            media_paths.extend(get_album_database_paths(conn, "Videos"))

        return media_paths
    except Exception as e:
        print(f"Error retrieving media paths for album {album_name}: {e}")
        return []