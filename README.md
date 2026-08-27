# DTU Course Bank

This repository is both the file store and the backend for the [GE Union course bank](https://geunion.dk/course-bank). GitHub serves the resources and the generated catalog, so the website does not need to bundle or proxy them.

## Upload a resource

1. Open the course folder listed in `catalog.source.json`.
2. Add the file using `Resource_title-a-Author_Name.ext`.
3. Commit the file to `main`.

Use underscores in place of spaces where practical. The `-a-Author_Name` part is optional; resources without it appear with an unknown author. Existing Unicode and space-containing filenames remain supported, so publishing never renames or breaks an uploaded URL.

Examples:

- `Physics_equations-a-Andrew_Davison.pdf`
- `Statistics_test_calculator_scripts-a-s24.zip`
- `Atomic_electron_geometries.pdf`

The GitHub workflow validates the complete repository before atomically publishing `catalog.v2.json`. An invalid upload fails safely and leaves the last valid public catalog available. `structure.json` is also generated for older clients.

## Add or edit a course

Course/category labels, descriptions, folder mappings and external links live in `catalog.source.json`. Add the folder (a tracked `.blank` file is enough), update the source catalog, and commit both changes. The website builds its tabs, disclosures and resources directly from the generated catalog.

## Validate locally

```sh
python3 -m unittest discover -s .github/tests -v
python3 .github/scripts/build_catalog.py --validate
```

The compiler is deterministic, uses only the Python standard library, rejects undeclared resource folders and unsupported files, and never mutates uploaded resources.
