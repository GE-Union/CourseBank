from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "build_catalog.py"
SPEC = importlib.util.spec_from_file_location("build_catalog", SCRIPT)
assert SPEC and SPEC.loader
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)

REVISION = "1" * 40


def source() -> dict:
    return {
        "repository": {"rawBase": "https://raw.githubusercontent.com/GE-Union/CourseBank"},
        "site": {
            "title": "Course bank",
            "tagline": "Student resources",
            "links": [{"id": "upload", "heading": "Upload", "label": "Here", "url": "https://example.com/upload"}],
        },
        "categories": [{
            "id": "foundations",
            "folder": "foundations",
            "name": "Foundations",
            "shortName": "Base",
            "emphasis": "Foundations",
            "description": "The Foundations courses.",
            "courses": [{"id": "math", "folder": "math", "code": "01001", "name": "Math"}],
        }],
    }


class CatalogCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "foundations" / "math").mkdir(parents=True)
        (self.root / "foundations" / "math" / "Useful_Notes-a-Ada_Lovelace.pdf").write_bytes(b"pdf")
        (self.root / "catalog.source.json").write_text(json.dumps(source()), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def compile(self):
        return catalog.compile_catalog(self.root, REVISION)

    def test_compiles_versioned_and_legacy_manifests(self) -> None:
        manifest, legacy = self.compile()
        self.assertEqual(manifest["schemaVersion"], 2)
        self.assertEqual(manifest["sourceRevision"], REVISION)
        resource = manifest["categories"][0]["courses"][0]["files"][0]
        self.assertEqual(resource["title"], "Useful Notes")
        self.assertEqual(resource["author"], "Ada Lovelace")
        self.assertEqual(resource["extension"], "PDF")
        self.assertEqual(resource["path"], "foundations/math/Useful_Notes-a-Ada_Lovelace.pdf")
        self.assertEqual(legacy, {"foundations": {"math": ["Useful_Notes-a-Ada_Lovelace.pdf"]}})

    def test_uses_last_author_separator(self) -> None:
        title, author, extension = catalog.parse_filename("Q-a-A-a-Final_Author.ipynb")
        self.assertEqual((title, author, extension), ("Q-a-A", "Final Author", "IPYNB"))

    def test_output_is_deterministic(self) -> None:
        first = self.compile()
        second = self.compile()
        self.assertEqual(first, second)

    def test_reads_the_revision_recorded_by_a_published_catalog(self) -> None:
        (self.root / "catalog.v2.json").write_text(
            json.dumps({"sourceRevision": REVISION}), encoding="utf-8"
        )
        self.assertEqual(catalog.published_revision(self.root), REVISION)

    def test_rejects_undeclared_resource_folder(self) -> None:
        undeclared = self.root / "foundations" / "unknown"
        undeclared.mkdir()
        (undeclared / "Notes.pdf").write_bytes(b"pdf")
        with self.assertRaisesRegex(catalog.CatalogError, "undeclared course folder"):
            self.compile()

    def test_rejects_unsupported_resource_type(self) -> None:
        (self.root / "foundations" / "math" / "malware.exe").write_bytes(b"no")
        with self.assertRaisesRegex(catalog.CatalogError, "Unsupported resource type"):
            self.compile()

    def test_rejects_duplicate_course_code_in_category(self) -> None:
        value = source()
        duplicate = {"id": "more-math", "folder": "more-math", "code": "01001", "name": "More Math"}
        value["categories"][0]["courses"].append(duplicate)
        (self.root / "foundations" / "more-math").mkdir()
        (self.root / "catalog.source.json").write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(catalog.CatalogError, "Duplicate course code"):
            self.compile()

    def test_supports_a_course_in_a_different_storage_root(self) -> None:
        value = source()
        value["categories"][0]["courses"][0]["rootFolder"] = "obligatory"
        (self.root / "obligatory").mkdir()
        (self.root / "foundations" / "math").rename(self.root / "obligatory" / "math")
        (self.root / "catalog.source.json").write_text(json.dumps(value), encoding="utf-8")
        manifest, legacy = self.compile()
        self.assertEqual(manifest["categories"][0]["courses"][0]["path"], "obligatory/math")
        self.assertIn("obligatory", legacy)


if __name__ == "__main__":
    unittest.main()
