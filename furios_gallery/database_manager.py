# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import os
from pathlib import Path
import sqlite3

from .media_manager import PICTURE_EXTENSIONS, VIDEO_EXTENSIONS, check_file_integrity, extract_extension

# ************* Database Management ************* #
def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # Optional performance tweaks:
        # - Faster commits, less durability: conn.execute("PRAGMA synchronous = OFF")
        # - Allow concurrent reads: conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

# Temporary method for handling migrations, if this grows to big switch over to a tool that
# can handle migrations in a better way
def update_table_schema(conn):
    """Check and update the schema of the albums table if necessary."""
    try:
        with conn:  # Ensure changes are in a single transaction
            cursor = conn.cursor()

            # Check if the 'custom' column exists in the 'albums' table
            cursor.execute("PRAGMA table_info(albums)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]

            # Add the 'custom' column if it doesn't exist
            if 'custom' not in column_names:
                cursor.execute("ALTER TABLE albums ADD COLUMN custom BOOLEAN NOT NULL DEFAULT FALSE")
                print("Added 'custom' column to the 'albums' table.")

    except sqlite3.Error as e:
        print(f"Error updating table schema: {e}")

def create_tables(conn):
    """Create the necessary tables and indexes if they do not exist."""
    try:
        with conn:  # This ensures changes are in a single transaction
            cursor = conn.cursor()
            # Create tables
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
                    album_name TEXT NOT NULL,
                    custom BOOLEAN NOT NULL
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

            update_table_schema(conn)

            # Create indexes to optimize lookups
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_files_path ON files(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(album_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_custom_albumns ON albums(custom ASC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_albums_albums ON file_albums(album_id ASC)")

        print("Tables and indexes created successfully")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

    # Populate database after tables are guaranteed to exist
    populate_database(conn)

def file_exists_in_database(conn, file_path):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE file_path = ?", (file_path,))
        exists = cursor.fetchone()[0] > 0
        cursor.close()
        return exists

def populate_database(conn):
    """Walk through user Pictures and Videos directories, check their integrity,
    and insert them into the database if not present."""
    pictures_root = Path.home() / 'Pictures'
    videos_root = Path.home() / 'Videos'

    media_items = []

    def process_directory(directory, extensions):
        for subdir, _, files in os.walk(directory):
            album_name = os.path.basename(subdir)
            for file in files:
                file_path = os.path.join(subdir, file)
                if file_path.lower().endswith(tuple(extensions)):
                    if not file_exists_in_database(conn, file_path):
                        if check_file_integrity(file_path):
                            albums = [album_name, "Recents"]
                            media_items.append((file_path, albums))

    process_directory(pictures_root, PICTURE_EXTENSIONS)
    process_directory(videos_root, VIDEO_EXTENSIONS)

    # Insert valid items in a single transaction for speed
    with conn:
        for file_path, albums in media_items:
                insert_file_and_albums(conn, file_path, albums)

    print(f"Processed {len(media_items)} media files.")

def insert_file_and_albums(conn, file_path, albums):
    """Insert a single file into the database (if not present) and link it to albums."""
    file_type = "picture" if extract_extension(file_path) in PICTURE_EXTENSIONS else "video"

    # Ensure default albums exist for the given file type
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

def insert_file(conn, file_path, file_type):
    """Insert a file if it does not exist and return its file_id."""
    cursor = conn.cursor()
    # First try an insert or ignore:
    cursor.execute("""
        INSERT OR IGNORE INTO files (file_path, file_type)
        VALUES (?, ?)
    """
    , (file_path, file_type))

    # If the row was ignored, we need to fetch its existing ID.
    if cursor.lastrowid == 0:
        # The file already exists. Fetch its ID.
        cursor.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
        return cursor.fetchone()[0]
    else:
        # New row inserted, return the new ID
        return cursor.lastrowid

def insert_or_get_album(conn, album_name):
    """Insert an album if not present and return its album_id."""
    cursor = conn.cursor()
    cursor.execute("SELECT album_id FROM albums WHERE album_name = ?", (album_name,))
    album = cursor.fetchone()
    if album:
        return album[0]
    else:
        cursor.execute("INSERT INTO albums (album_name, custom) VALUES (?, FALSE)", (album_name,))
        return cursor.lastrowid

def insert_file_album(conn, file_id, album_id):
    """Link a file to an album (if not already linked)."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO file_albums (file_id, album_id) 
        VALUES (?, ?)
    """
    , (file_id, album_id))

def list_database_albums(conn):
    """Return a list of album names with a custom priority sort."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.album_name
            FROM albums a
                JOIN file_albums fa ON a.album_id = fa.album_id
            WHERE a.custom = FALSE
            UNION
            SELECT DISTINCT album_name
            FROM albums
            WHERE custom = TRUE
        """
        )

        albums = [row[0] for row in cursor.fetchall()]

        priority_order = ['Recents', 'Pictures', 'Videos', 'Screenshots']

        def album_sort_key(album):
            if album in priority_order:
                # (0, the album's index in priority_order)
                return (0, priority_order.index(album))
            else:
                # (1, album.lower())
                return (1, album.lower())

        albums.sort(key=album_sort_key)
        return albums
    except Exception as e:
        print(f"Error fetching albums: {e}")
        return []


def get_album_database_paths(conn, album_name):
    """Return a sorted-by-mtime list of valid file paths in a given album."""
    cur = conn.cursor()
    cur.execute("""
        SELECT files.file_path
        FROM files
        JOIN file_albums ON files.file_id = file_albums.file_id
        JOIN albums ON file_albums.album_id = albums.album_id
        WHERE albums.album_name = ?
    """
    , (album_name,))

    file_paths = [row[0] for row in cur.fetchall()]
    valid_paths = []

    for path in file_paths:
        if os.path.exists(path):
            valid_paths.append(path)
        else:
            print(f"File not found, removing from database: {path}")
            delete_from_albums(conn, path)

    # Sort existing files by last modification time
    return sorted(valid_paths, key=lambda p: os.path.getmtime(p))

def get_album_media_paths(conn, album_name):
    """Example of specialized retrieval with fallback logic to pictures/videos."""
    try:
        cur = conn.cursor()
        query = """
            SELECT files.file_path
            FROM files
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

        # Optional logic to include "Pictures" or "Videos" from the "Recents" album
        # (If the intention is to unify content between them, fine. Otherwise, remove this logic.)
        if album_name.lower() in ['pictures', 'recents']:
            media_paths.extend(get_album_database_paths(conn, "Pictures"))
        if album_name.lower() in ['videos', 'recents']:
            media_paths.extend(get_album_database_paths(conn, "Videos"))

        return media_paths
    except Exception as e:
        print(f"Error retrieving media paths for album {album_name}: {e}")
        return []

def delete_from_albums(conn, file_path):
    """Completely remove a file and its references from the database."""
    try:
        with conn:  # single transaction
            cur = conn.cursor()
            cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
            row = cur.fetchone()

            if row:
                file_id = row[0]
                # Remove the references in file_albums first
                cur.execute("DELETE FROM file_albums WHERE file_id = ?", (file_id,))
                # Remove the file entry
                cur.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                print(f"Successfully deleted all entries for {file_path}")
            else:
                print("No entry found for the given file path.")
    except Exception as e:
        print(f"An error occurred: {e}")

def delete_file_from_album(conn, file_path, album_name):
    """Remove a file from a specific album if it's not a default album."""
    if album_name in ["Recents", "Videos", "Pictures"]:
        print("Can't delete from default albums")
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
            file_id = cur.fetchone()
            cur.execute("SELECT album_id FROM albums WHERE album_name = ?", (album_name,))
            album_id = cur.fetchone()

            if file_id and album_id:
                cur.execute("DELETE FROM file_albums WHERE file_id = ? AND album_id = ?", (file_id[0], album_id[0]))
                print(f"Successfully removed {file_path} from {album_name}")
            else:
                print("File or album does not exist")
    except Exception as e:
        print(f"Error when trying to remove file from album: {e}")

def add_file_to_album(conn, file_path, album_name):
    """Add an existing file to an existing album."""
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path,))
            file_id = cur.fetchone()
            cur.execute("SELECT album_id FROM albums WHERE album_name = ?", (album_name,))
            album_id = cur.fetchone()

            if file_id and album_id:
                cur.execute("INSERT OR IGNORE INTO file_albums (file_id, album_id) VALUES (?, ?)",
                            (file_id[0], album_id[0]))
                print(f"Successfully added {file_path} to {album_name}")
            else:
                print("File or album does not exist, make sure both are created before linking them.")
    except Exception as e:
        print(f"Error when trying to add file to album: {e}")
