import os
import json
import re

EXCLUDED = {".git", ".github", "__pycache__", "res"}

def normalize_filename(filename):
    stem, ext = os.path.splitext(filename)

    # Convert only the last %% into -a-
    if "%%" in stem:
        name, author = stem.rsplit("%%", 1)
        stem = f"{name.strip()}-a-{author.strip()}"
    else:
        stem = stem.strip()

    # Clean accidental spaces around existing -a-
    stem = re.sub(r"\s*-a-\s*", "-a-", stem)

    # Convert all remaining spaces to underscores
    stem = re.sub(r"\s+", "_", stem)

    return stem + ext

def normalize_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDED and not d.startswith(".")
        ]

        for filename in filenames:
            if filename.startswith("."):
                continue

            new_filename = normalize_filename(filename)

            if new_filename == filename:
                continue

            old_path = os.path.join(dirpath, filename)
            new_path = os.path.join(dirpath, new_filename)

            if os.path.exists(new_path):
                raise FileExistsError(f"Cannot rename {old_path} to {new_path}: target already exists")

            os.rename(old_path, new_path)

def build_structure(root):
    structure = {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDED and not d.startswith(".")
        ]

        rel_path = os.path.relpath(dirpath, root)

        if rel_path == ".":
            parts = []
        else:
            parts = rel_path.split(os.sep)

        files = [
            f for f in filenames
            if not f.startswith(".")
        ]

        if not files:
            continue

        current = structure
        for part in parts:
            current = current.setdefault(part, {})

        current.setdefault("_files", []).extend(files)

    return structure

normalize_files(".")

with open("structure.json", "w") as f:
    json.dump(build_structure("."), f, indent=2)
