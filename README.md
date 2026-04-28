# PythonMusicClassifier
Python TUI script to move music albums based on their genre metadata (Currently only working with FLAC file, but I plan to add support other file formats)

# Features
- Automatic Genre Extraction: Reads ID3 tags from FLAC files using ffprobe.
- Smart Conflict Resolution: Detects albums with mixed genres and prompts you via a clean TUI to choose the best folder.
- Genre Normalization: Maps varied tag formats (e.g., "Prog Rock", "Progressive Rock") to consistent folder names via a configurable .conf file.
- Dry-Run Mode: Simulate moves without touching your files to verify logic first.
- Cross-Device Support: Handles moves across different filesystems (e.g., HDD to SSD) by copying then verifying before deletion.
- Logging: All actions, skips, and errors are logged to music_classifier.log.
- Cleanup: Automatically removes empty directories after processing.

# Project Structure
```
music_classifier/
├── music_classifier.py       # Main script
├── music_classifier.conf     # Configuration file
├── Unclassified/             # Source directory (input)
│   ├── Artist Name/
│   │   └── Album Title/
│   │       └── *.flac
├── Classified/               # Destination for genre-organized music
│   ├── Rock/
│   ├── Electronic/
│   └── ...
├── No_Genre_Metadata/        # Albums with no genre tags
└── music_classifier.log      # Execution logs
```
# Configuration
Edit music_classifier.conf to customize paths and genre mappings.

Paths are relative to the script location:

```music_classifier.conf
UNCCLASSIFIED_DIR=./Unclassified
CLASSIFIED_DIR=./Classified
NO_GENRE_ROOT=./No_Genre_Metadata
LOG_FILE=music_classifier.log

# Format: RAW_TAG=TARGET_FOLDER
Video Game Music=Video Game Music
Chiptune=Video Game Music
Progressive Rock=Rock
Modern Classical=Classical
French=World Music
```

# Installation
Dependancies :

- Python 3.6+
- ffprobe (part of FFmpeg)
- ncurses

Setup

1. Clone or download the project.
2. Ensure ffprobe is in your system PATH:
    ```bash
        ffprobe -version
    ```

3. Create the Unclassified folder and place your unorganized albums inside:
    ```
    Unclassified/
    └── Artist/
        └── Album/
            └── track01.flac
    ```

# Usage

Standard Run

```
python3 music_classifier.py
```

The TUI will launch, showing progress and prompting for genre conflicts.

Dry Run (Safe Preview)

```
python3 music_classifier.py --dry-run
```

Custom Config Path

```
python3 music_classifier.py --config /path/to/custom.conf
```

# How It Works

- Scan: Recursively scans `UNCCLASSIFIED_DIR` for album folders containing `.flac` files.
- Extract: Uses `ffprobe` to read the genre tag from each file.
- Normalize: Applies mappings from `music_classifier.conf` to standardize genre names.
- Resolve:
  - Single Genre: Auto-moves to `CLASSIFIED_DIR/<Genre>/<Artist>/<Album>`.
  - No Genre: Moves to `NO_GENRE_ROOT/<Artist>/<Album>`.
  - Multiple Genres: Launches TUI to let you pick the primary genre or skip.
- Move: Executes the move (or copy+delete for cross-device).
- Cleanup: Removes empty parent directories.

### Conflict Resolution Logic

| Scenario                                      | Action                                                                      |
|----------------------------------------------|-----------------------------------------------------------------------------|
| 1 Genre                                      | Auto-move                                                                   |
| 0 Genres                                     | Auto-move to No_Genre_Metadata                                              |
| >1 Genres, 1 existing folder                  | Auto-move to existing folder                                                |
| >1 Genres, 0 or >1 existing folders           | TUI Prompt (Accept suggestion, manual override, or skip)                    |

# Troubleshooting

### Error: 'ncurses' module not found

- Linux (Ubuntu/Debian for example): `sudo apt-get install python3-ncurses`
- macOS: Usually built-in. If missing, `brew install python`
- Windows: `pip install windows-curses`

### ffprobe not found

Install FFmpeg:

- Linux (Ubuntu/Debian for example): `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from ffmpeg.org and add to PATH.

### Move Failed (Cross-Device)

If you see "Copy succeeded but source deletion failed," check permissions on the source folder. The script intentionally keeps both copies to prevent data loss.

# Logging

All operations are logged to `music_classifier.log`:

```
[2026-04-21 19:20:36] Auto-move (Existing Folder): Pink Floyd / The Dark Side of the Moon -> Progressive Rock
[2026-04-21 19:21:05] Skipped (User): Radiohead / OK Computer
[2026-04-21 19:22:10] Moved: Daft Punk / Discovery -> Electronic
```

# Safety Notes

- Backup First: Always backup your music library before running bulk operations.
- Dry Run: Use `--dry-run` to verify logic before committing.
- Permissions: Ensure you have read/write access to all target directories.

# Contributing

Found a bug or want a new feature? Open an issue or submit a PR!

# Disclaimer

This project cannot be used to plagiarize my work into someone else's academic code without prior authorization from my part. Please check your local academic institution's ethics committee for the potential consequences resulting from plagiarizing my work.

However, since this project is under the [GPL-3.0 license](https://www.gnu.org/licenses/gpl-3.0.en.html) and the [Opinionated Queer License (OQL) v1.2](https://oql.avris.it/license?c=FluffyAceBean), inclusion of my code can be redistributed and modified without proper authorization from myself with respect to their license agreements. If any license issue occurs between the GPL-3.0 and the OQL v1.2, the OQL v1.2 should remain superior.

Please contact me or open an issue if needed.

### Important notice

This project is vibe-coded as of 28 april 2026. I don't like that it is the case, but the complexity of the program and my non-knowledge of Python made me use AI. Future revisions should decrease the use of A.I. in the code to human-made code. Code starting with `# AI+` and ending with `# AI-` delimit section where vibe-coded code is used.

PLEASE DO NOT USE THIS IN A SECURE ENVIRONMENT.

`SPDX-License-Identifier: GPL-3.0 AND LicenseRef-OQL-1.2`
