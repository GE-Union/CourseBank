# Contributing to the course bank

Most contributions only require uploading a file. GitHub validates every change and publishes the catalog automatically after a valid commit reaches `main`.

## Choose the right change

| Goal | Change |
| --- | --- |
| Upload a resource | Add it to the existing course folder. |
| Add a course | Add its folder and an entry in `catalog.source.json`. |
| Rename a label or link | Edit `catalog.source.json`. |
| Change validation or publishing | Edit `.github/scripts/build_catalog.py` and its tests. |

`catalog.v2.json` and `structure.json` are generated files. Never edit them by hand.

## Upload a resource

1. Find the course in `catalog.source.json` and open the folder named by its `path`.
2. Add the resource using `Resource_title-a-Author_Name.ext`.
3. Commit the file and check that the **Publish course catalog** workflow succeeds.

Use underscores instead of spaces. The optional `-a-` part separates the title from the author:

- `Physics_equations-a-Andrew_Davison.pdf`
- `Atomic_electron_geometries.pdf`

Supported extensions are listed once in `MEDIA_TYPES` in `.github/scripts/build_catalog.py`. Keep each file below 50 MiB. Course folders cannot contain subfolders.

## Add a course

1. Add the course folder. Include an empty `.blank` file if it has no resources yet.
2. Add the course to the correct category in `catalog.source.json`.
3. Give it a unique `id`, five-digit `code`, folder name, display name, and description.
4. Run the validation commands below.

The source catalog is the editable model. The compiler checks that its folder mappings match the repository before producing the public model consumed by the website.

## Validate locally

Python 3 is the only requirement:

```sh
python3 -m unittest discover -s .github/tests -v
python3 .github/scripts/build_catalog.py --validate
```

Before committing, make sure both commands pass and that unrelated generated or system files are not included.

## Publishing flow

```text
uploaded files + catalog.source.json
                ↓
        validation and compiler
                ↓
      catalog.v2.json + structure.json
                ↓
          GitHub-hosted website data
```

If validation fails, the previous public catalog remains available. Fix the reported source or file-layout error instead of editing a generated manifest.
