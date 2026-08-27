#!/usr/bin/env python3
"""Validate CourseBank content and compile its public catalog manifests."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMA_VERSION = 2
SOURCE_FILE = "catalog.source.json"
CATALOG_FILE = "catalog.v2.json"
LEGACY_FILE = "structure.json"
MAX_FILE_BYTES = 50 * 1024 * 1024

IGNORED_FILES = {".blank", ".DS_Store"}
IGNORED_DIRECTORIES = {".git", ".github", "res"}
REPOSITORY_FILES = {
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    SOURCE_FILE,
    CATALOG_FILE,
    LEGACY_FILE,
}
MEDIA_TYPES = {
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".ipynb": "application/x-ipynb+json",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".py": "text/x-python",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
}

JsonObject = dict[str, Any]


class CatalogError(ValueError):
    """Raised when source metadata or published resources are invalid."""


class BuildContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.course_paths: set[str] = set()
        self.declared_directories: set[Path] = set()
        self.legacy: JsonObject = {}


def has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def is_safe_segment(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and not value.startswith(".")
        and "/" not in value
        and "\\" not in value
        and not has_control_character(value)
    )


def require_string(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CatalogError(f"{field_name} must be a string")
    result = value.strip()
    if (not allow_empty and not result) or has_control_character(result):
        requirement = "a string" if allow_empty else "a non-empty string"
        raise CatalogError(f"{field_name} must be {requirement} without control characters")
    return result


def require_object(value: Any, field_name: str) -> JsonObject:
    if not isinstance(value, dict):
        raise CatalogError(f"{field_name} must be an object")
    return value


def require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise CatalogError(f"{field_name} must be an array")
    return value


def require_segment(value: Any, field_name: str) -> str:
    result = require_string(value, field_name)
    if not is_safe_segment(result):
        raise CatalogError(f"{field_name} must be a safe path segment")
    return result


def require_course_code(value: Any, field_name: str) -> str:
    result = require_string(value, field_name)
    if not re.fullmatch(r"\d{5}", result):
        raise CatalogError(f"{field_name} must contain exactly five digits")
    return result


def require_https_url(value: Any, field_name: str) -> str:
    result = require_string(value, field_name)
    parsed = urlsplit(result)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise CatalogError(f"{field_name} must be an HTTPS URL")
    return result


def require_unique(value: str, seen: set[str], field_name: str) -> None:
    key = unicodedata.normalize("NFC", value).casefold()
    if key in seen:
        raise CatalogError(f"Duplicate {field_name}: {value}")
    seen.add(key)


def git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return require_revision(result.stdout.strip().lower(), "Git revision")


def require_revision(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise CatalogError(f"{field_name} must be a full lowercase Git revision")
    return value


def published_revision(root: Path) -> str:
    try:
        catalog = json.loads((root / CATALOG_FILE).read_text(encoding="utf-8"))
        return require_revision(catalog["sourceRevision"], "Published source revision")
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise CatalogError(f"Could not read the published source revision: {error}") from error


def read_source(root: Path) -> JsonObject:
    try:
        value = json.loads((root / SOURCE_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CatalogError(f"Could not read {SOURCE_FILE}: {error}") from error
    return require_object(value, SOURCE_FILE)


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


def sorted_directory(directory: Path) -> list[Path]:
    return sorted(
        directory.iterdir(),
        key=lambda path: unicodedata.normalize("NFC", path.name).casefold(),
    )


def course_resources(directory: Path) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise CatalogError(f"Declared course folder is missing or is a symbolic link: {directory}")

    resources: list[Path] = []
    filenames: set[str] = set()
    for entry in sorted_directory(directory):
        if entry.name in IGNORED_FILES or entry.name.startswith("."):
            continue
        if entry.is_symlink():
            raise CatalogError(f"Symbolic links are not published: {entry}")
        if not entry.is_file():
            raise CatalogError(f"Nested directories are not allowed in a course folder: {entry}")
        if not is_safe_segment(entry.name):
            raise CatalogError(f"Unsafe resource filename: {entry.name}")
        require_unique(entry.name, filenames, "resource filename")
        if entry.suffix.lower() not in MEDIA_TYPES:
            raise CatalogError(f"Unsupported resource type: {entry}")
        if entry.stat().st_size > MAX_FILE_BYTES:
            limit = MAX_FILE_BYTES // 1024 // 1024
            raise CatalogError(f"Resource exceeds the {limit} MiB limit: {entry}")
        resources.append(entry)
    return resources


def compile_resource(root: Path, resource: Path) -> JsonObject:
    title, author, extension = parse_filename(resource.name)
    return {
        "filename": resource.name,
        "path": resource.relative_to(root).as_posix(),
        "title": title,
        "author": author,
        "extension": extension,
        "mediaType": MEDIA_TYPES[resource.suffix.lower()],
        "bytes": resource.stat().st_size,
    }


def compile_links(site: JsonObject) -> list[JsonObject]:
    links: list[JsonObject] = []
    link_ids: set[str] = set()
    for index, value in enumerate(require_list(site.get("links"), "site.links")):
        field_name = f"site.links[{index}]"
        link = require_object(value, field_name)
        link_id = require_segment(link.get("id"), f"{field_name}.id")
        require_unique(link_id, link_ids, "site link id")
        links.append(
            {
                "id": link_id,
                "heading": require_string(link.get("heading"), f"{field_name}.heading"),
                "label": require_string(link.get("label"), f"{field_name}.label"),
                "url": require_https_url(link.get("url"), f"{field_name}.url"),
            }
        )
    return links


def compile_site(site: JsonObject) -> JsonObject:
    return {
        "title": require_string(site.get("title"), "site.title"),
        "tagline": require_string(site.get("tagline"), "site.tagline"),
        "links": compile_links(site),
    }


def compile_course(
    value: Any,
    field_name: str,
    category_folder: str,
    course_ids: set[str],
    course_codes: set[str],
    context: BuildContext,
) -> JsonObject:
    course = require_object(value, field_name)
    course_id = require_segment(course.get("id"), f"{field_name}.id")
    course_folder = require_segment(course.get("folder"), f"{field_name}.folder")
    course_code = require_course_code(course.get("code"), f"{field_name}.code")
    root_folder = require_segment(
        course.get("rootFolder", category_folder),
        f"{field_name}.rootFolder",
    )

    require_unique(course_id, course_ids, "course id within category")
    require_unique(course_code, course_codes, "course code within category")
    course_path = f"{root_folder}/{course_folder}"
    require_unique(course_path, context.course_paths, "course path")

    directory = context.root / root_folder / course_folder
    context.declared_directories.add(directory.resolve())
    resources = course_resources(directory)
    files = [compile_resource(context.root, resource) for resource in resources]
    if resources:
        context.legacy.setdefault(root_folder, {})[course_folder] = [
            resource.name for resource in resources
        ]

    result: JsonObject = {
        "id": course_id,
        "folder": course_folder,
        "path": course_path,
        "code": course_code,
        "name": require_string(course.get("name"), f"{field_name}.name"),
        "description": require_string(
            course.get("description", ""),
            f"{field_name}.description",
            allow_empty=True,
        ),
        "files": files,
    }
    if course.get("separated") is True:
        result["separated"] = True
    return result


def compile_category(
    value: Any,
    index: int,
    category_ids: set[str],
    category_folders: set[str],
    context: BuildContext,
) -> JsonObject:
    field_name = f"categories[{index}]"
    category = require_object(value, field_name)
    category_id = require_segment(category.get("id"), f"{field_name}.id")
    folder = require_segment(category.get("folder"), f"{field_name}.folder")
    require_unique(category_id, category_ids, "category id")
    require_unique(folder, category_folders, "category folder")

    course_ids: set[str] = set()
    course_codes: set[str] = set()
    courses = [
        compile_course(
            course,
            f"{field_name}.courses[{course_index}]",
            folder,
            course_ids,
            course_codes,
            context,
        )
        for course_index, course in enumerate(
            require_list(category.get("courses"), f"{field_name}.courses")
        )
    ]
    if not courses:
        raise CatalogError(f"{field_name}.courses must contain at least one course")
    return {
        "id": category_id,
        "folder": folder,
        "name": require_string(category.get("name"), f"{field_name}.name"),
        "shortName": require_string(
            category.get("shortName"),
            f"{field_name}.shortName",
        ),
        "emphasis": require_string(
            category.get("emphasis"),
            f"{field_name}.emphasis",
            allow_empty=True,
        ),
        "description": require_string(
            category.get("description"),
            f"{field_name}.description",
        ),
        "courses": courses,
    }


def validate_repository_layout(context: BuildContext) -> None:
    for entry in sorted_directory(context.root):
        if entry.name.startswith(".") or entry.name in IGNORED_DIRECTORIES:
            continue
        if entry.is_symlink():
            raise CatalogError(f"Symbolic links are not allowed: {entry.name}")
        if entry.is_file():
            if entry.name not in REPOSITORY_FILES:
                raise CatalogError(f"Unexpected file at repository root: {entry.name}")
            continue

        for path in entry.rglob("*"):
            if path.name.startswith(".") or path.name in IGNORED_FILES:
                continue
            if path.is_symlink():
                raise CatalogError(f"Symbolic links are not allowed: {path.relative_to(context.root)}")
            if path.is_file() and path.parent.resolve() not in context.declared_directories:
                raise CatalogError(
                    f"Resource is outside a declared course folder: {path.relative_to(context.root)}"
                )


def compile_catalog(root: Path, revision: str) -> tuple[JsonObject, JsonObject]:
    source = read_source(root)
    repository = require_object(source.get("repository"), "repository")
    site = require_object(source.get("site"), "site")
    categories = require_list(source.get("categories"), "categories")
    if not categories:
        raise CatalogError("categories must contain at least one category")

    raw_base = require_https_url(repository.get("rawBase"), "repository.rawBase").rstrip("/")
    if urlsplit(raw_base).hostname != "raw.githubusercontent.com":
        raise CatalogError("repository.rawBase must use raw.githubusercontent.com")

    context = BuildContext(root=root)
    category_ids: set[str] = set()
    category_folders: set[str] = set()
    public_categories = [
        compile_category(
            category,
            index,
            category_ids,
            category_folders,
            context,
        )
        for index, category in enumerate(categories)
    ]
    validate_repository_layout(context)

    return (
        {
            "schemaVersion": SCHEMA_VERSION,
            "sourceRevision": require_revision(revision, "sourceRevision"),
            "repository": {"rawBase": raw_base},
            "assets": {"fileIcon": "res/file-icon.svg"},
            "site": compile_site(site),
            "categories": public_categories,
        },
        context.legacy,
    )


def encode_json(value: JsonObject) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_atomic(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def expected_outputs(root: Path, revision: str) -> dict[str, str]:
    catalog, legacy = compile_catalog(root, revision)
    return {
        CATALOG_FILE: encode_json(catalog),
        LEGACY_FILE: encode_json(legacy),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-revision")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true", help="Validate without writing")
    mode.add_argument("--check", action="store_true", help="Fail if manifests are stale")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    root = arguments.root.resolve()
    try:
        revision = arguments.source_revision or (
            published_revision(root) if arguments.check else git_revision(root)
        )
        outputs = expected_outputs(root, revision)
        if arguments.validate:
            catalog = json.loads(outputs[CATALOG_FILE])
            course_count = sum(len(category["courses"]) for category in catalog["categories"])
            print(f"Validated {course_count} courses")
            return 0
        if arguments.check:
            stale = [
                filename
                for filename, content in outputs.items()
                if not (root / filename).is_file()
                or (root / filename).read_text(encoding="utf-8") != content
            ]
            if stale:
                raise CatalogError(f"Generated manifests are stale: {', '.join(stale)}")
            print("Generated manifests are current")
            return 0
        for filename, content in outputs.items():
            write_atomic(root / filename, content)
        print(f"Published {CATALOG_FILE} and {LEGACY_FILE}")
        return 0
    except (CatalogError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
