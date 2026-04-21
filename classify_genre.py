#!/usr/bin/env python3
# From FluffyBeanAce
# Licence:
#   - GNU GPL v3.0
#   - OQL v1.2
# See README.md
#
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import argparse
import shutil
from collections import Counter
from pathlib import Path

try:
    import curses
except ImportError:
    print("Error: 'ncurses' module not found. Install via 'pip install ncurses' or system package 'python3-ncurses'.")
    sys.exit(1)

# --- Default Config Paths ---
CONFIG_FILE = "music_classifier.conf"

def load_config(config_path):
    """Parses the .conf file safely."""
    config = {"paths": {}, "genre_map": {}}

    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key in ["UNCCLASSIFIED_DIR", "CLASSIFIED_DIR", "NO_GENRE_ROOT", "LOG_FILE"]:
                    config["paths"][key] = value
                else:
                    config["genre_map"][key] = value
    except Exception as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)
    return config

def get_genre_from_file(filepath):
    try:
        abs_path = str(filepath.resolve())
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format_tags=genre", "-of", "default=noprint_wrappers=1:nokey=1", abs_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return None

def normalize_genre(raw_genre, genre_map):
    if not raw_genre:
        return []
    parts = [p.strip() for p in raw_genre.split(';')]
    mapped_parts = []
    for part in parts:
        matched = False
        for key, value in genre_map.items():
            if key.lower() == part.lower():
                mapped_parts.append(value)
                matched = True
                break
        if not matched:
            mapped_parts.append(part)
    return mapped_parts

def log(message, log_path):
    timestamp = subprocess.check_output(["date", "+%Y-%m-%d %H:%M:%S"]).decode().strip()
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def scan_albums(base_path):
    albums = []
    base = Path(base_path)
    if not base.exists():
        return albums
    for artist_dir in base.iterdir():
        if not artist_dir.is_dir():
            continue
        artist_name = artist_dir.name
        for album_dir in artist_dir.iterdir():
            if not album_dir.is_dir():
                continue
            flac_files = list(album_dir.glob("*.flac"))
            if flac_files:
                albums.append({"path": album_dir, "artist": artist_name, "album": album_dir.name, "files": flac_files})
    return albums

def resolve_conflict(stdscr, album_data, genre_counts, dry_run):
    """Interactive TUI to resolve genre conflicts."""
    height, width = stdscr.getmaxyx()
    suggestion = genre_counts.most_common(1)[0][0]

    while True:
        stdscr.clear()
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(0, 0, "⚠️  Genre Conflict Detected".center(width)[:width-1])
        stdscr.attroff(curses.A_BOLD)

        artist = album_data['artist']
        album = album_data['album']
        stdscr.addstr(2, 2, f"Artist: {artist}")
        stdscr.addstr(3, 2, f"Album:  {album}")

        stdscr.addstr(5, 2, "Detected Genres (Count):")
        for i, (genre, count) in enumerate(genre_counts.items()):
            stdscr.addstr(6 + i, 4, f"  • {genre}: {count} tracks")

        stdscr.addstr(6 + len(genre_counts) + 1, 2, f"Suggested Folder: {suggestion}")

        opts_y = 6 + len(genre_counts) + 3
        stdscr.addstr(opts_y, 2, "[1] Accept Suggestion (Move to {})".format(suggestion))
        stdscr.addstr(opts_y + 1, 2, "[2] Manual Override (Type custom name)")
        stdscr.addstr(opts_y + 2, 2, "[3] Skip this album")

        stdscr.addstr(opts_y + 4, 2, "Choice [1-3]: ", curses.A_BOLD)
        stdscr.refresh()

        try:
            key = stdscr.getch()
        except:
            continue

        if key == ord('1'):
            return suggestion, False
        elif key == ord('2'):
            stdscr.addstr(opts_y + 4, 2, "Choice [1-3]: ")
            stdscr.addstr(opts_y + 4, 18, " " * 20)
            stdscr.addstr(opts_y + 4, 18, "Custom Name: ", curses.A_DIM)
            stdscr.refresh()
            curses.echo()
            curses.curs_set(1)
            try:
                custom_input = stdscr.getstr(opts_y + 4, 32, 50).decode('utf-8').strip()
            except:
                custom_input = ""
            curses.noecho()
            curses.curs_set(0)
            if custom_input:
                return custom_input, False
            else:
                continue
        elif key == ord('3'):
            return None, True
        else:
            continue

def move_folder_robust(src, dst):
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        raise FileExistsError(f"Destination already exists: {dst}")

    try:
        # Try standard move first
        shutil.move(str(src), str(dst))
        if src.exists():
            raise RuntimeError(f"Move failed: Source {src} still exists.")
        if not dst.exists():
            raise RuntimeError(f"Move failed: Destination {dst} does not exist.")
        return
    except Exception as e:
        if "cross-device" not in str(e).lower() and not isinstance(e, OSError):
            raise  # Re-raise non-cross-device errors immediately

    # Cross-device move: Copy then verify then delete
    try:
        shutil.copytree(str(src), str(dst))
    except Exception as copy_err:
        raise RuntimeError(f"Copy failed: {copy_err}") from copy_err

    # Verify copy succeeded before deleting source
    if not dst.exists():
        shutil.rmtree(str(dst), ignore_errors=True)
        raise RuntimeError("Copy succeeded but destination not found after copytree")

    # Now safely delete source
    try:
        shutil.rmtree(str(src))
    except Exception as delete_err:
        # CRITICAL: Restore dst if delete fails? Or just warn?
        # For safety, we could restore from dst back to src, but that's complex.
        # Better to leave both and warn user.
        raise RuntimeError(
            f"Copy succeeded but source deletion failed: {delete_err}. "
            f"Manual cleanup required. Both {src} and {dst} exist."
        ) from delete_err

    if src.exists():
        raise RuntimeError(f"Source {src} still exists after attempted deletion.")



def cleanup_empty_dirs(base_path):
    base = Path(base_path)
    if not base.exists():
        return 0
    removed_count = 0
    for dirpath, dirnames, filenames in os.walk(base, topdown=False):
        current_path = Path(dirpath)
        if current_path == base:
            continue
        try:
            if not any(current_path.iterdir()):
                current_path.rmdir()
                removed_count += 1
        except OSError:
            pass
    return removed_count

def run_tui(stdscr, albums_data, config, dry_run):
    curses.curs_set(0)
    stdscr.nodelay(False)
    height, width = stdscr.getmaxyx()

    processed = 0
    skipped = 0
    total = len(albums_data)

    unc_dir = config["paths"].get("UNCCLASSIFIED_DIR", "./Unclassified")
    cls_dir = config["paths"].get("CLASSIFIED_DIR", "./Classified")
    nog_dir = config["paths"].get("NO_GENRE_ROOT", "./No_Genre_Metadata")
    log_path = config["paths"].get("LOG_FILE", "music_classifier.log")
    genre_map = config["genre_map"]

    os.makedirs(cls_dir, exist_ok=True)
    os.makedirs(nog_dir, exist_ok=True)

    def draw_screen():
        stdscr.clear()
        title = f"Music Classifier {'[DRY RUN]' if dry_run else '[LIVE]'}"
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(0, 0, title.center(width)[:width-1])
        stdscr.attroff(curses.A_BOLD)

        pct = int((processed / total) * 100) if total > 0 else 0
        bar_len = width - 20
        filled = int(bar_len * processed / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        stdscr.addstr(2, 0, f"Progress: [{bar}] {pct}% ({processed}/{total})")

        if processed < total:
            item = albums_data[processed]
            stdscr.addstr(4, 0, f"Scanning: {item['artist']} / {item['album']}")
        else:
            stdscr.addstr(4, 0, "Processing Complete!")
            stdscr.addstr(6, 0, f"Processed: {processed} | Skipped: {skipped}")
            stdscr.addstr(8, 0, "Press 'q' to exit.")
        stdscr.refresh()

    for idx, item in enumerate(albums_data):
        processed = idx
        draw_screen()

        flac_files = item['files']
        if not flac_files:
            skipped += 1
            continue

        all_mapped_genres = []
        for f in flac_files:
            raw = get_genre_from_file(f)
            if raw:
                mapped = normalize_genre(raw, genre_map)
                all_mapped_genres.extend(mapped)

        # --- LOGIC UPDATE START ---
        target_root = None
        target_genre_folder = None
        should_skip = False
        auto_move = False

        if not all_mapped_genres:
            # No metadata case
            target_root = nog_dir
            target_genre_folder = ""
            should_skip = False
            auto_move = True # Always auto-move for no-genre
            log(f"No metadata found for: {item['artist']}/{item['album']} -> Moving to {nog_dir}", log_path)
        else:
            target_root = cls_dir
            genre_counts = Counter(all_mapped_genres)
            unique_count = len(genre_counts)

            # Check existing folders for this artist
            existing_folders = []
            for genre in genre_counts.keys():
                check_path = Path(cls_dir) / genre / item['artist']
                if check_path.exists():
                    existing_folders.append(genre)

            if unique_count == 1:
                # Single genre: Auto-move if folder exists, else proceed to create
                genre = list(genre_counts.keys())[0]
                if genre in existing_folders:
                    target_genre_folder = genre
                    auto_move = True
                    log(f"Auto-move (Existing Folder): {item['artist']}/{item['album']} -> {genre}", log_path)
                else:
                    target_genre_folder = genre
                    auto_move = False # Will create new folder
            else:
                # Multiple genres (Conflict)
                if len(existing_folders) == 1:
                    # Exactly one existing folder: Auto-move there
                    target_genre_folder = existing_folders[0]
                    auto_move = True
                    log(f"Auto-move (Only One Existing): {item['artist']}/{item['album']} -> {target_genre_folder}", log_path)
                else:
                    # None exist OR Multiple exist: Ask user
                    target_genre_folder, should_skip = resolve_conflict(stdscr, item, genre_counts, dry_run)
                    if should_skip:
                        skipped += 1
                        log(f"Skipped (User): {item['artist']}/{item['album']}", log_path)
                        continue
                    auto_move = False # Just a normal move after decision

        # --- LOGIC UPDATE END ---

        if not should_skip and target_genre_folder is not None:
            if not all_mapped_genres:
                dest_dir = Path(target_root) / item['artist'] / item['album']
                display_path = f"{nog_dir}/{item['artist']}/{item['album']}"
            else:
                dest_dir = Path(target_root) / target_genre_folder / item['artist'] / item['album']
                display_path = f"{cls_dir}/{target_genre_folder}/{item['artist']}/{item['album']}"

            if dest_dir.exists():
                log(f"Warning: Destination exists: {dest_dir}. Skipping.", log_path)
                skipped += 1
                continue

            if not dry_run:
                try:
                    move_folder_robust(item['path'], dest_dir)
                    log(f"Moved: {item['artist']}/{item['album']} -> {display_path}", log_path)
                except Exception as e:
                    log(f"Error moving {item['artist']}/{item['album']}: {e}", log_path)
            else:
                log(f"[DRY-RUN] Would move: {item['artist']}/{item['album']} -> {display_path}", log_path)

    if not dry_run:
        stdscr.addstr(4, 0, "Cleaning up empty folders...")
        stdscr.refresh()
        removed = cleanup_empty_dirs(unc_dir)
        if removed > 0:
            log(f"Cleanup: Removed {removed} empty folders.", log_path)
            stdscr.addstr(6, 0, f"Cleanup: Removed {removed} empty folders.")
        else:
            stdscr.addstr(6, 0, "Cleanup: No empty folders found.")
    else:
        stdscr.addstr(6, 0, "(Dry Run: Cleanup skipped)")

    draw_screen()
    stdscr.addstr(height-2, 0, "Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()

def main():
    parser = argparse.ArgumentParser(description="Organize music files by genre.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate moves.")
    parser.add_argument("--config", default=CONFIG_FILE, help="Path to config file.")
    args = parser.parse_args()

    config = load_config(args.config)
    unc_dir = config["paths"].get("UNCCLASSIFIED_DIR", "./Unclassified")

    if not os.path.isdir(unc_dir):
        print(f"Error: Directory '{unc_dir}' not found.")
        sys.exit(1)

    albums_data = scan_albums(unc_dir)
    if not albums_data:
        print("No albums found.")
        sys.exit(0)

    print(f"Found {len(albums_data)} albums. Starting TUI...")

    try:
        curses.wrapper(run_tui, albums_data, config, args.dry_run)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)

if __name__ == "__main__":
    main()
