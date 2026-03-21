## Offline usage

Models downloaded into: /Users/<user>/.cache/docling/models.

Docling can now be configured for running offline using the local artifacts.

Using the CLI: `docling --artifacts-path=/Users/<user>/.cache/docling/models FILE` 
Using Python: see the documentation at <https://docling-project.github.io/docling/usage>.

Or using the DOCLING_ARTIFACTS_PATH environment variable:

```bash
export DOCLING_ARTIFACTS_PATH="/local/path/to/models"
python my_docling_script.py
```