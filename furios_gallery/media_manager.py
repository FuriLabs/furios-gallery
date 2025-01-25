# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

from pathlib import Path
import os, time, subprocess
from PIL import Image, ExifTags
import datetime
from datetime import datetime
import sqlite3

PICTURE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'bmp', 'webp', 'svg']
VIDEO_EXTENSIONS = ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'mpg', 'mpeg']

def extract_extension(filepath: str) -> str:
    # Grab file extension without leading dot
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lstrip(".").lower()

    return file_extension

def extract_file_date(filepath):
    try:
        if extract_extension(filepath) in ['jpg', 'jpeg']:
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
        """
        )

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS albums (
            album_id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_name TEXT NOT NULL
        );
        """
        )

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_albums (
            file_id INTEGER NOT NULL,
            album_id INTEGER NOT NULL,
            PRIMARY KEY (file_id, album_id),
            FOREIGN KEY (file_id) REFERENCES files(file_id),
            FOREIGN KEY (album_id) REFERENCES albums(album_id)
        );
        """
        )

        print("Tables created successfully")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

    populate_database(conn)

def populate_database(conn):
    pictures_root = Path.home() / 'Pictures'
    videos_root = Path.home() / 'Videos'

    media_items = []

    def file_exists_in_database(conn, file_path):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE file_path = ?", (file_path,))
        exists = cursor.fetchone()[0] > 0
        cursor.close()
        return exists

    def process_directory(directory, file_type, extensions):
        for subdir, dirs, files in os.walk(directory):
            album_name = os.path.basename(subdir)
            for file in files:
                file_path = os.path.join(subdir, file)
                if file_path.lower().endswith(tuple(extensions)):
                    if not file_exists_in_database(conn, file_path):
                        if check_file_integrity(file_path):
                            albums = [album_name, "Recents"]
                            media_items.append((file_path, file_type, albums))

    process_directory(pictures_root, 'picture', PICTURE_EXTENSIONS)
    process_directory(videos_root, 'video', VIDEO_EXTENSIONS)

    for file_path, file_type, albums in media_items:
        insert_file_and_albums(conn, file_path, file_type, albums)

    print(f"Processed {len(media_items)} media files.")

def check_picture_integrity(file_path):
    if not os.path.exists(file_path):
        print(file_path)
        return False

    if os.path.getsize(file_path) == 0:
        print(file_path)
        return False

    try:
        with Image.open(file_path) as img:
            img.verify()

            img = Image.open(file_path)
            img.getpixel((0, 0))
            return True
    except (IOError, ValueError) as e:
        print(f"Image could not be opened or is corrupted: {str(e)}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return False

def check_video_integrity(file_path):
    # TBD: Do not use subprocess, no bueno, and we need to do smt about .mkv
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-'],
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"An error occurred while checking {file_path}: {e}")
        return False

def check_file_integrity(file_path):
    if extract_extension(file_path) in PICTURE_EXTENSIONS:
        return check_picture_integrity(file_path)
    elif extract_extension(file_path) in VIDEO_EXTENSIONS:
        return check_video_integrity(file_path)

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
        albums = [album[0] for album in albums]

        priority_order = ['Recents', 'Pictures', 'Videos', 'Screenshots']

        def album_sort_key(album):
            try:
                return priority_order.index(album)
            except ValueError:
                return len(priority_order) + ord(album[0].lower()) - ord('a')

        albums.sort(key=lambda album: (album not in priority_order, album_sort_key(album) if album not in priority_order else priority_order.index(album)))

        return albums
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
    """
    ,(album_name,))

    file_paths = [row[0] for row in cur.fetchall()]
    valid_paths = []

    for path in file_paths:
        if os.path.exists(path):
            valid_paths.append(path)
        else:
            print(f"File not found, removing from database: {path}")
            delete_from_albums(conn, path)

    sorted_paths = sorted(valid_paths, key=lambda path: os.path.getmtime(path))
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

        media_paths = []
        for row in rows:
            if os.path.exists(row[0]):
                media_paths.append(row[0])
            else:
                print(f"File not found, removing from database: {row[0]}")
                delete_from_albums(conn, row[0])

        if album_name.lower() in ['pictures', 'recents']:
            media_paths.extend(get_album_database_paths(conn, "Pictures"))
        if album_name.lower() in ['videos', 'recents']:
            media_paths.extend(get_album_database_paths(conn, "Videos"))

        return media_paths
    except Exception as e:
        print(f"Error retrieving media paths for album {album_name}: {e}")
        return []

def delete_from_albums(conn, file_path):
    try:
        cur = conn.cursor()

        cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
        file_id = cur.fetchone()

        if file_id:
            file_id = file_id[0]

            cur.execute("DELETE FROM file_albums WHERE file_id = ?", (file_id,))

            cur.execute("DELETE FROM files WHERE file_id = ?", (file_id,))

            conn.commit()
            print(f"Successfully deleted all entries for {file_path}")
        else:
            print("No entry found for the given file path.")

    except Exception as e:
        conn.rollback()
        print(f"An error occurred: {e}")

def delete_file_from_album(conn, file_path, album_name):
    if album_name != "Recents" and album_name != "Videos" and album_name != "Pictures":
        try:
            cur = conn.cursor()
            cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
            file_id = cur.fetchone()
            cur.execute("SELECT album_id FROM albums WHERE album_name = ?", (album_name,))
            album_id = cur.fetchone()

            if file_id and album_id:
                cur.execute("DELETE FROM file_albums WHERE file_id = ? AND album_id = ?", (file_id[0], album_id[0]))
                conn.commit()
                print(f"Successfully removed {file_path} from {album_name}")
            else:
                print("File or album does not exist")
        except Exception as e:
            print(f"Error when trying to remove file from album: {e}")
            conn.rollback()
    else:
        print("Cant delete from default albums")

def add_file_to_album(conn, file_path, album_name):
    try:
        cur = conn.cursor()
        cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
        file_id = cur.fetchone()
        cur.execute("SELECT album_id FROM albums WHERE album_name = ?", (album_name,))
        album_id = cur.fetchone()

        if file_id and album_id:
            cur.execute("INSERT INTO file_albums (file_id, album_id) VALUES (?, ?)", (file_id[0], album_id[0]))
            conn.commit()
            print(f"Successfully added {file_path} to {album_name}")
        else:
            print("File or album does not exist, make sure both are created before linking them.")
    except Exception as e:
        print(f"Error when trying to add file to album: {e}")
        conn.rollback()
