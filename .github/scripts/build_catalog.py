#!/usr/bin/env python3
"""Validate CourseBank content and compile its public catalog manifests."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
SOURCE_FILE = "catalog.source.json"
CATALOG_FILE = "catalog.v2.json"
LEGACY_FILE = "structure.json"
MAX_FILE_BYTES = 50 * 1024 * 1024
IGNORED_FILES = {".blank", ".DS_Store"}
IGNORED_ROOTS = {".git", ".github", "res"}
SUPPORTED_EXTENSIONS = {
    ".csv", ".doc", ".docx", ".html", ".ipynb", ".jpeg", ".jpg",
    ".json", ".pdf", ".png", ".ppt", ".pptx", ".py", ".svg",
    ".txt", ".xls", ".xlsx", ".zip",
}


class CatalogError(ValueError):
    """Raised when source metadata or published resources are invalid."""


def is_safe_segment(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and not value.startswith(".")
        and "/" not in value
        and "\\" not in value
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def require_string(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise CatalogError(f"{field} must be a non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CatalogError(f"{field} contains a control character")
    return value.strip() if not allow_empty else value


def require_unique(value: str, seen: set[str], field: str) -> None:
    key = unicodedata.normalize("NFC", value).casefold()
    if key in seen:
        raise CatalogError(f"Duplicate {field}: {value}")
    seen.add(key)


def source_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    revision = result.stdout.strip().lower()
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise CatalogError("Could not resolve a full Git source revision")
    return revision


def parse_filename(filename: str) -> tuple[str, str, str]:
    stem = Path(filename).stem
    resource, separator, author = stem.rpartition("-a-")
    if not separator:
        resource, author = stem, "Unknown"
    title = resource.replace("_", " ").strip()
    author = author.replace("_", " ").strip() or "Unknown"
    if not title:
        raise CatalogError(f"Resource filename has no title: {filename}")
    return title, author, Path(filename).suffix[1:].upper()


def resource_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise CatalogError(f"Declared course folder does not exist: {folder}")
    files: list[Path] = []
    seen: set[str] = set()
    for entry in sorted(folder.iterdir(), key=lambda path: unicodedata.normalize("NFC", path.name).casefold()):
        if entry.name in IGNORED_FILES or entry.name.startswith("."):
            continue
        if entry.is_symlink():
            raise CatalogError(f"Symbolic links are not published: {entry}")
        if not entry.is_file():
            raise CatalogError(f"Nested directories are not allowed in a course folder: {entry}")
        if not is_safe_segment(entry.name):
            raise CatalogError(f"Unsafe resource filename: {entry.name}")
        require_unique(entry.name, seen, "resource filename")
        if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise CatalogError(f"Unsupported resource type: {entry}")
        if entry.stat().st_size > MAX_FILE_BYTES:
            raise CatalogError(f"Resource exceeds the {MAX_FILE_BYTES // 1024 // 1024} MiB limit: {entry}")
        files.append(entry)
    return files


def read_source(root: Path) -> dict[str, Any]:
    try:
        value = json.loads((root / SOURCE_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CatalogError(f"Could not read {SOURCE_FILE}: {error}") from error
    if not isinstance(value, dict):
        raise CatalogError(f"{SOURCE_FILE} must contain a JSON object")
    return value


def compile_catalog(root: Path, revision: str) -> tuple[dict[str, Any], dict[str, Any]]:
    source = read_source(root)
    repository = source.get("repository")
    site = source.get("site")
    categories = source.get("categories")
    if not isinstance(repository, dict) or not isinstance(site, dict) or not isinstance(categories, list):
        raise CatalogError("Source requires repository, site, and categories")

    raw_base = require_string(repository.get("rawBase"), "repository.rawBase").rstrip("/")
    if not raw_base.startswith("https://raw.githubusercontent.com/"):
        raise CatalogError("repository.rawBase must use raw.githubusercontent.com over HTTPS")

    links = site.get("links")
    if not isinstance(links, list):
        raise CatalogError("site.links must be an array")
    public_site = {
        "title": require_string(site.get("title"), "site.title"),
        "tagline": require_string(site.get("tagline"), "site.tagline"),
        "links": [],
    }
    link_ids: set[str] = set()
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            raise CatalogError(f"site.links[{index}] must be an object")
        link_id = require_string(link.get("id"), f"site.links[{index}].id")
        require_unique(link_id, link_ids, "site link id")
        url = require_string(link.get("url"), f"site.links[{index}].url")
        if not url.startswith("https://"):
            raise CatalogError(f"site.links[{index}].url must use HTTPS")
        public_site["links"].append({
            "id": link_id,
            "heading": require_string(link.get("heading"), f"site.links[{index}].heading"),
            "label": require_string(link.get("label"), f"site.links[{index}].label"),
            "url": url,
        })

    category_ids: set[str] = set()
    category_folders: set[str] = set()
    course_paths: set[str] = set()
    declared_paths: set[Path] = set()
    public_categories: list[dict[str, Any]] = []
    legacy: dict[str, Any] = {}

    for category_index, category in enumerate(categories):
        prefix = f"categories[{category_index}]"
        if not isinstance(category, dict) or not isinstance(category.get("courses"), list):
            raise CatalogError(f"{prefix} must be an object with a courses array")
        category_id = require_string(category.get("id"), f"{prefix}.id")
        folder = require_string(category.get("folder"), f"{prefix}.folder")
        if not is_safe_segment(folder):
            raise CatalogError(f"Unsafe category folder: {folder}")
        require_unique(category_id, category_ids, "category id")
        require_unique(folder, category_folders, "category folder")

        public_category = {
            "id": category_id,
            "folder": folder,
            "name": require_string(category.get("name"), f"{prefix}.name"),
            "shortName": require_string(category.get("shortName"), f"{prefix}.shortName"),
            "emphasis": require_string(category.get("emphasis"), f"{prefix}.emphasis", allow_empty=True),
            "description": require_string(category.get("description"), f"{prefix}.description"),
            "courses": [],
        }

        course_ids: set[str] = set()
        course_codes: set[str] = set()
        for course_index, course in enumerate(category["courses"]):
            course_prefix = f"{prefix}.courses[{course_index}]"
            if not isinstance(course, dict):
                raise CatalogError(f"{course_prefix} must be an object")
            course_id = require_string(course.get("id"), f"{course_prefix}.id")
            course_folder = require_string(course.get("folder"), f"{course_prefix}.folder")
            code = require_string(course.get("code"), f"{course_prefix}.code")
            if not is_safe_segment(course_folder):
                raise CatalogError(f"Unsafe course folder: {course_folder}")
            require_unique(course_id, course_ids, "course id within category")
            require_unique(code, course_codes, "course code within category")
            root_folder = require_string(course.get("rootFolder", folder), f"{course_prefix}.rootFolder")
            if not is_safe_segment(root_folder):
                raise CatalogError(f"Unsafe course root folder: {root_folder}")
            path = f"{root_folder}/{course_folder}"
            require_unique(path, course_paths, "course path")
            absolute_path = root / root_folder / course_folder
            declared_paths.add(absolute_path.resolve())

            files: list[dict[str, Any]] = []
            legacy_files: list[str] = []
            for file in resource_files(absolute_path):
                title, author, extension = parse_filename(file.name)
                relative_path = file.relative_to(root).as_posix()
                media_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                files.append({
                    "filename": file.name,
                    "path": relative_path,
                    "title": title,
                    "author": author,
                    "extension": extension,
                    "mediaType": media_type,
                    "bytes": file.stat().st_size,
                })
                legacy_files.append(file.name)

            public_course: dict[str, Any] = {
                "id": course_id,
                "folder": course_folder,
                "path": path,
                "code": code,
                "name": require_string(course.get("name"), f"{course_prefix}.name"),
                "description": require_string(course.get("description", ""), f"{course_prefix}.description", allow_empty=True),
                "files": files,
            }
            if course.get("separated") is True:
                public_course["separated"] = True
            public_category["courses"].append(public_course)
            if legacy_files:
                legacy.setdefault(root_folder, {})[course_folder] = legacy_files
        public_categories.append(public_category)

    validate_no_undeclared_resources(root, declared_paths)
    catalog = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceRevision": revision,
        "repository": {"rawBase": raw_base},
        "assets": {"fileIcon": "res/file-icon.svg"},
        "site": public_site,
        "categories": public_categories,
    }
    return catalog, legacy


def validate_no_undeclared_resources(root: Path, declared_paths: set[Path]) -> None:
    for category in root.iterdir():
        if category.name.startswith(".") or category.name in IGNORED_ROOTS or not category.is_dir():
            continue
        for course in category.iterdir():
            if course.name.startswith(".") or not course.is_dir():
                continue
            has_resources = any(
                child.is_file() and not child.name.startswith(".") and child.name not in IGNORED_FILES
                for child in course.iterdir()
            )
            if has_resources and course.resolve() not in declared_paths:
                raise CatalogError(f"Resources found in undeclared course folder: {course.relative_to(root)}")


def encoded(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_atomic(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-revision")
    parser.add_argument("--validate", action="store_true", help="Validate without writing manifests")
    parser.add_argument("--check", action="store_true", help="Fail if committed manifests are stale")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    revision = arguments.source_revision or source_revision(root)
    try:
        catalog, legacy = compile_catalog(root, revision)
        outputs = {CATALOG_FILE: encoded(catalog), LEGACY_FILE: encoded(legacy)}
        if arguments.validate:
            print(f"Validated {sum(len(category['courses']) for category in catalog['categories'])} courses")
            return 0
        if arguments.check:
            stale = [name for name, content in outputs.items() if not (root / name).is_file() or (root / name).read_text(encoding="utf-8") != content]
            if stale:
                raise CatalogError(f"Generated manifests are stale: {', '.join(stale)}")
            print("Generated manifests are current")
            return 0
        for name, content in outputs.items():
            write_atomic(root / name, content)
        print(f"Published {len(catalog['categories'])} categories to {CATALOG_FILE} and {LEGACY_FILE}")
        return 0
    except CatalogError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
