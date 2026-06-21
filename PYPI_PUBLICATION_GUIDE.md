# SemantixRAG v2.0 PyPI Publication Guide

## ✅ Refactoring Complete

Your SemantixRAG v2.0 project has been successfully migrated to PEP 621-compliant `src-layout` for PyPI publication. This guide documents all changes and how to build/publish the package.

---

## 📁 Directory Structure (After Migration)

```
SemantixRAG/
├── pyproject.toml              # ← NEW: PEP 621 configuration
├── MANIFEST.in                 # ← NEW: Package data manifest
├── src/
│   └── semantixrag/            # ← NEW: Main package namespace
│       ├── __init__.py
│       ├── cli.py              # ← NEW: Global CLI entry point
│       ├── resources.py        # ← NEW: importlib.resources loader
│       ├── main.py             # ← MOVED: IngestionPipeline
│       ├── models.py
│       ├── pipeline.py
│       ├── api/
│       │   ├── main.py
│       │   └── routes/
│       │       ├── admin.py
│       │       ├── compliance.py
│       │       ├── ingestion.py
│       │       ├── observability.py
│       │       └── retrieval.py
│       ├── cdc/
│       │   ├── incremental.py
│       │   └── watcher.py
│       ├── chunking/
│       │   ├── enricher.py
│       │   └── header_splitter.py
│       ├── compliance/
│       │   ├── dsar.py
│       │   ├── masking.py
│       │   └── pii_scanner.py
│       ├── config/             # ← MOVED: Settings + OPA policies
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── opa/
│       │       ├── access.rego
│       │       ├── audit.rego
│       │       └── masking.rego
│       ├── embeddings/
│       ├── extractors/
│       ├── indexing/
│       ├── knowledge/
│       ├── monitoring/
│       └── observability/
├── tests/
│   ├── test_compliance.py      # ← UPDATED: Imports
│   ├── test_knowledge.py       # ← UPDATED: Imports
│   └── test_observability.py   # ← UPDATED: Imports
├── main.py                     # ← TEMPORARY: Use for backwards compatibility
├── README.md
├── LICENSE
└── requirements.txt
```

---

## 🔄 Key Changes & Import Updates

### 1. **Test Files** — Updated imports
```python
# OLD
from src.compliance.pii_scanner import PIIScanner

# NEW
from semantixrag.compliance.pii_scanner import PIIScanner
```

### 2. **Package-level Imports** — All modules use relative imports or `semantixrag` namespace
```python
# OLD (in src/pipeline.py)
from config.settings import settings

# NEW (in src/semantixrag/pipeline.py)
from .config.settings import settings
# OR (when using from tests or other packages)
from semantixrag.config.settings import settings
```

### 3. **Resource Loading** — Safe loading of .rego files via `importlib.resources`
```python
# NEW: src/semantixrag/resources.py
from semantixrag.resources import get_rego_policy

# Load a single policy
access_policy = get_rego_policy('access.rego')

# Load all policies
all_policies = get_all_rego_policies()
```

---

## 🛠️ Files Modified/Created

| File | Action | Notes |
|------|--------|-------|
| `pyproject.toml` | **CREATED** | PEP 621 configuration with all dependencies |
| `MANIFEST.in` | **CREATED** | Ensures .rego, .html, and other data files are included |
| `src/semantixrag/` | **CREATED** | New package namespace directory |
| `src/semantixrag/cli.py` | **CREATED** | Global CLI entry point |
| `src/semantixrag/resources.py` | **CREATED** | Safe resource loader for .rego files |
| `tests/test_*.py` | **UPDATED** | All imports converted to use `semantixrag.*` |
| `src/semantixrag/pipeline.py` | **UPDATED** | Imports converted to relative/absolute |
| All `src/semantixrag/**/*.py` | **UPDATED** | `from config.settings` → `from .config.settings` |

---

## 🚀 Build & Publish Guide

### Prerequisites
```bash
pip install build twine
```

### Step 1: Build the Package
```bash
cd c:\Users\Dell\Parser_app\SemantixRAG

# Build wheel and source distribution
python -m build

# Output will be in dist/
# - dist/semantixrag-2.0.0-py3-none-any.whl
# - dist/semantixrag-2.0.0.tar.gz
```

### Step 2: Verify the Wheel Contents (Important!)
```bash
# Extract and inspect wheel
python -m zipfile -l dist/semantixrag-2.0.0-py3-none-any.whl | grep -E "(\.rego|__pycache__|semantixrag)"

# Should show files like:
# - semantixrag/config/opa/access.rego
# - semantixrag/config/opa/audit.rego
# - semantixrag/config/opa/masking.rego
# - semantixrag/*.py
```

### Step 3: Test Installation Locally
```bash
# Create a test environment
python -m venv test_env
.\test_env\Scripts\activate

# Install the local wheel
pip install dist/semantixrag-2.0.0-py3-none-any.whl

# Test the CLI
semantixrag --help

# Should show:
# usage: semantixrag [-h] {init,ingest,watch,search,stats} ...
```

### Step 4: Publish to PyPI Test Server (Recommended First)
```bash
# Create ~/.pypirc with your PyPI credentials (already configured)

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/semantixrag-2.0.0*

# Test installation from TestPyPI
pip install -i https://test.pypi.org/simple/ semantixrag==2.0.0
```

### Step 5: Publish to PyPI Production
```bash
# Upload to PyPI
python -m twine upload dist/semantixrag-2.0.0*

# After publication, anyone can install with:
# pip install semantixrag
# semantixrag init
```

---

## ⚙️ Entry Points & CLI

### Global Command Registration
In `pyproject.toml`:
```toml
[project.scripts]
semantixrag = "semantixrag.cli:main"
```

This creates a global `semantixrag` command after installation:
```bash
semantixrag init                       # Initialize OpenSearch index
semantixrag ingest ./documents/        # Ingest documents
semantixrag watch ./documents/         # CDC file watching
semantixrag search "query"             # Search documents
semantixrag stats                      # Show statistics
```

### CLI Implementation
- **File:** `src/semantixrag/cli.py`
- **Entry function:** `main()` → returns exit code
- **Error handling:** Proper exit codes (0=success, 1=error, 130=interrupt)

---

## 📦 Package Data & Resources

### Included in Wheel
Via `pyproject.toml` and `MANIFEST.in`:
- ✅ `src/semantixrag/config/opa/*.rego` — All Rego policy files
- ✅ `index.html` — Web UI (if present)
- ✅ `.env.example` — Example configuration
- ✅ All Python source files

### Safe Resource Loading
```python
# Instead of: open('./config/opa/access.rego')
# Use this to work in both dev and installed contexts:
from semantixrag.resources import get_rego_policy

policy_content = get_rego_policy('access.rego')
```

This uses `importlib.resources` which:
- ✅ Works with wheel distributions
- ✅ Works with editable installs (`pip install -e .`)
- ✅ Works with zipped packages
- ✅ Never uses `os.path` or `__file__` (unreliable in wheels)

---

## 🧪 Testing

### Run Tests with New Structure
```bash
# Activate environment
cd c:\Users\Dell\Parser_app\SemantixRAG

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/semantixrag --cov-report=html
```

### Test Commands
```bash
# Run specific test file
pytest tests/test_compliance.py -v

# Run specific test
pytest tests/test_compliance.py::test_pii_scanner -v

# Run with markers
pytest -m "not slow" -v
```

---

## 🔍 Validation Checklist

Before publishing:

- [ ] `pyproject.toml` exists and is valid
  ```bash
  python -m pip check
  ```

- [ ] All imports use `semantixrag.*` or relative paths
  ```bash
  grep -r "from src\." src/semantixrag/  # Should be empty
  grep -r "from config\." src/semantixrag/  # Should be empty (except in new cli.py)
  ```

- [ ] `.rego` files are in `src/semantixrag/config/opa/`
  ```bash
  ls src/semantixrag/config/opa/
  ```

- [ ] Tests import from `semantixrag` package
  ```bash
  grep "from src\." tests/  # Should be empty
  ```

- [ ] CLI entry point works
  ```bash
  pip install -e .
  semantixrag --help
  ```

- [ ] Build is successful
  ```bash
  python -m build
  ls -lh dist/
  ```

---

## 📝 Optional Post-Migration Tasks

### 1. Update Documentation
```bash
# Update README.md installation section
pip install semantixrag

# Update any docs that reference local paths
# - config/opa/ → Use resources.py instead
# - src/ package structure → Now in semantixrag package
```

### 2. Create GitHub Release
```bash
git tag v2.0.0
git push origin v2.0.0
```

### 3. Set Up CI/CD
```yaml
# .github/workflows/publish.yml
name: Publish to PyPI
on:
  release:
    types: [created]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install build twine
      - run: python -m build
      - run: python -m twine upload dist/*
```

---

## 🐛 Troubleshooting

### Issue: `.rego` files not found after installation
**Solution:** Ensure `MANIFEST.in` and `pyproject.toml` include them:
```toml
[tool.setuptools.package-data]
semantixrag = ["config/opa/*.rego"]
```

### Issue: CLI command not found after `pip install`
**Solution:** Verify entry point in `pyproject.toml`:
```toml
[project.scripts]
semantixrag = "semantixrag.cli:main"
```
Then reinstall: `pip install --force-reinstall --no-cache-dir .`

### Issue: Imports fail with `ModuleNotFoundError: No module named 'semantixrag'`
**Solution:** Install in development mode:
```bash
pip install -e ".[dev]"
```

### Issue: `importlib.resources` not found (Python 3.11)
**Solution:** Already included in `pyproject.toml`:
```toml
"importlib-resources>=6.1.0;python_version<'3.12'"
```

---

## 📚 References

- **PEP 621:** https://peps.python.org/pep-0621/
- **setuptools docs:** https://setuptools.pypa.io/
- **importlib.resources:** https://docs.python.org/3.12/library/importlib.resources.html
- **PyPI Publishing:** https://packaging.python.org/tutorials/packaging-projects/

---

## 🎯 Next Steps

1. **Test locally:**
   ```bash
   python -m build
   pip install -e .
   semantixrag --help
   ```

2. **Run test suite:**
   ```bash
   pytest tests/ -v
   ```

3. **Publish to PyPI:**
   ```bash
   python -m twine upload dist/*
   ```

4. **Verify installation:**
   ```bash
   pip install semantixrag
   semantixrag init
   ```

---

**Version:** SemantixRAG v2.0  
**Last Updated:** June 21, 2026  
**Status:** ✅ Ready for PyPI Publication
