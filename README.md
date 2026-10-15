# Code Standards Tool 1.1.0

The client CLI/CI sends only the application repository URL, branch/commit, checks branch, selection, parameters, and policy. The server clones both repositories, scans the full application branch, uploads partitioned reports to private Azure Blob Storage, then deletes both clones and all temporary files.

## Blob layout

```text
code-standards-results/
└── <repository-name>/
    └── <sanitized-branch>/
        └── <run-id>/
            ├── report_index.json
            ├── code_standards_<run-id>.xlsx
            └── results_001.json
```

## Install and start

```bash
pip install -e .
az login
codestandards serve --host 0.0.0.0 --port 8000
```

## Client

```bash
codestandards configure --server http://SERVER:8000
codestandards run \
  --application-repo https://github.com/CLIENT/application.git \
  --application-branch main \
  --checks-branch dev/data-engineering
```

All enabled checks run automatically. Use only `--include-test` to run specific tests, or only `--exclude-test` to run all except specific tests.
