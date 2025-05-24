import os
import json

EXCLUDED = {".git", ".github", "__pycache__"}

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

with open("structure.json", "w") as f:
    json.dump(build_structure("."), f, indent=2)
