import os
import json
import re

EXCLUDED = {".git", ".github", "__pycache__", "res"}

def normalize_filename(filename):
    name, ext = os.path.splitext(filename)

    # If %% exists, only convert the last one into -a-
    if "%%" in name:
        resource_name, author = name.rsplit("%%", 1)
        name = f"{resource_name.strip()}-a-{author.strip()}"
    else:
        name = name.strip()

    # Remove spaces around existing -a-
    name = re.sub(r"\s*-a-\s*", "-a-", name)

    # Convert spaces to underscores
    name = re.sub(r"\s+", "_", name)

    return name + ext

def normalize_files(root):
    for dirpath, _, filenames in os.walk(root):
        rel_path = os.path.relpath(dirpath, root)
        parts = rel_path.split(os.sep)

        # Same exclusion logic as build_structure
        if parts[0] in EXCLUDED or rel_path.startswith("."):
            continue

        if any(p.startswith(".") for p in parts):
            continue

        for filename in filenames:
            if filename.startswith("."):
                continue

            new_filename = normalize_filename(filename)

            if new_filename == filename:
                continue

            old_path = os.path.join(dirpath, filename)
            new_path = os.path.join(dirpath, new_filename)

            if os.path.exists(new_path):
                raise FileExistsError(
                    f"Cannot rename '{old_path}' to '{new_path}': target already exists"
                )

            os.rename(old_path, new_path)

def build_structure(root):
    structure = {}
    for dirpath, _, filenames in os.walk(root):
        rel_path = os.path.relpath(dirpath, root)
        parts = rel_path.split(os.sep)

        # Skip base and unwanted folders
        if parts[0] in EXCLUDED or rel_path.startswith("."):
            continue

        # Skip hidden folders/files
        if any(p.startswith(".") for p in parts):
            continue

        # Skip if no files in directory
        files = [f for f in filenames if not f.startswith(".")]
        if not files:
            continue

        current = structure
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current.setdefault(parts[-1], []).extend(files)
    return structure

normalize_files(".")

with open("structure.json", "w") as f:
    json.dump(build_structure("."), f, indent=2)
