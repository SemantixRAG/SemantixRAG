# SemantixRAG v2.0 → PyPI Refactoring Commands & Summary

This document contains the exact commands used to refactor SemantixRAG from a flat structure to PEP 621 src-layout for PyPI publication.

---

## 📋 Step-by-Step Refactoring Commands

### Step 1: Create Directory Structure
```powershell
cd c:\Users\Dell\Parser_app\SemantixRAG

# Create the new src/semantixrag directory
mkdir -p src\semantixrag
```

### Step 2: Migrate Package Files

```powershell
# Move all subdirectories from src/ into src/semantixrag/
Get-ChildItem src -Directory | Where-Object { $_.Name -ne 'semantixrag' } | ForEach-Object { 
    Move-Item $_.FullName src\semantixrag\ 
}

# Move all .py files from src/ into src/semantixrag/
Get-ChildItem src -File -Filter "*.py" | ForEach-Object { 
    Move-Item $_.FullName src\semantixrag\ 
}

# Move config/ directory into src/semantixrag/
Move-Item config src\semantixrag\
```

### Step 3: Create New Files

#### A. `pyproject.toml` (PEP 621 Configuration)
- Location: `c:\Users\Dell\Parser_app\SemantixRAG\pyproject.toml`
- Contains:
  - Project metadata (name, version, description)
  - All dependencies from `requirements.txt`
  - Optional dependency groups (dev, api, docs)
  - Package data directives for `.rego` files
  - CLI entry point: `semantixrag = "semantixrag.cli:main"`
  - Tool configurations (black, isort, pytest, coverage)

#### B. `MANIFEST.in` (Package Data Manifest)
- Location: `c:\Users\Dell\Parser_app\SemantixRAG\MANIFEST.in`
- Ensures inclusion of:
  - All `.rego` files in `src/semantixrag/config/opa/`
  - HTML files
  - Example configuration files

#### C. `src/semantixrag/resources.py` (Resource Loader)
- Safe loading of `.rego` files using `importlib.resources`
- Functions:
  - `get_rego_policy(policy_name)` — Load a single policy
  - `get_all_rego_policies()` — Load all policies
  - `get_resource_path(resource_name)` — Get file path (debugging)
- Handles Python 3.11 (importlib_resources) and 3.12+ (importlib.resources)

#### D. `src/semantixrag/cli.py` (Global CLI Entry Point)
- Replaces `main.py` with package namespace
- Implements all commands:
  - `semantixrag init` — Initialize OpenSearch index
  - `semantixrag ingest <path>` — Ingest documents
  - `semantixrag watch <directory>` — CDC file watching
  - `semantixrag search <query>` — Search documents
  - `semantixrag stats` — Show statistics
- Proper exit codes (0=success, 1=error, 130=interrupt)

### Step 4: Update Imports

#### Test Files
```python
# test_observability.py
from src.observability.tracer import Tracer  # OLD
→ from semantixrag.observability.tracer import Tracer  # NEW

# test_knowledge.py
from src.models import ExtractedElement  # OLD
→ from semantixrag.models import ExtractedElement  # NEW

# test_compliance.py
from src.compliance.pii_scanner import PIIScanner  # OLD
→ from semantixrag.compliance.pii_scanner import PIIScanner  # NEW
```

#### Main Package Files (18 replacements)
```python
# OLD pattern in all files:
from config.settings import settings

# NEW pattern (relative imports):
from .config.settings import settings  # In src/semantixrag/pipeline.py
from ..config.settings import settings  # In src/semantixrag/indexing/*.py
```

**Files Updated:**
- `src/semantixrag/pipeline.py`
- `src/semantixrag/indexing/bulk_indexer.py`
- `src/semantixrag/indexing/connection.py`
- `src/semantixrag/indexing/index_manager.py`
- `src/semantixrag/indexing/hybrid_search.py`
- `src/semantixrag/monitoring/logger.py`
- `src/semantixrag/cdc/incremental.py`
- `src/semantixrag/cdc/watcher.py`

#### Main.py Updates
```python
# OLD
sys.path.insert(0, str(Path(__file__).parent))
from config.settings import settings
from src import IngestionPipeline, setup_logging

# NEW
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from semantixrag.config.settings import settings
from semantixrag import IngestionPipeline, setup_logging
```

---

## 📊 Refactoring Statistics

| Metric | Count |
|--------|-------|
| Python files migrated | 47 |
| Test files updated | 3 |
| Package modules | 8 (api, cdc, chunking, compliance, config, embeddings, extractors, indexing, knowledge, monitoring, observability) |
| Import replacements | 27+ |
| New configuration files | 3 (pyproject.toml, MANIFEST.in, PYPI_PUBLICATION_GUIDE.md) |
| New utility modules | 2 (resources.py, cli.py) |
| Rego policy files | 3 (access.rego, audit.rego, masking.rego) |

---

## 🔍 Verification Commands

### Check Directory Structure
```powershell
# Verify src/semantixrag exists with all subdirectories
Get-ChildItem -Path src\semantixrag -Recurse -Directory

# Count Python files
(Get-ChildItem -Path src\semantixrag -Recurse -File -Filter "*.py" | Measure-Object).Count
# Expected: 47

# Verify .rego files
Get-ChildItem -Path src\semantixrag\config\opa -File
# Expected: access.rego, audit.rego, masking.rego
```

### Check Imports
```powershell
# Verify no old imports remain
grep -r "from src\." src/semantixrag/  # Should be empty
grep -r "from config\." src/semantixrag/  # Should be empty

# Verify test imports updated
grep -r "from src\." tests/  # Should be empty
```

### Validate pyproject.toml
```bash
pip install toml
python -c "import toml; print(toml.load('pyproject.toml')['project']['name'])"
# Expected: semantixrag

# Check entry points
python -c "import toml; print(toml.load('pyproject.toml')['project']['scripts'])"
# Expected: {'semantixrag': 'semantixrag.cli:main'}
```

---

## 🛠️ Build & Test Commands

### Build Package
```powershell
# Install build tools
pip install build twine wheel setuptools>=70.0

# Build distribution
python -m build

# Verify wheel contents
python -m zipfile -l dist/semantixrag-2.0.0-py3-none-any.whl | grep "rego"
# Should show:
# - semantixrag/config/opa/access.rego
# - semantixrag/config/opa/audit.rego
# - semantixrag/config/opa/masking.rego
```

### Install Locally
```powershell
# Create test environment
python -m venv test_env
.\test_env\Scripts\activate

# Install wheel
pip install dist/semantixrag-2.0.0-py3-none-any.whl

# Test CLI
semantixrag --help
semantixrag init
```

### Run Tests
```powershell
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/semantixrag --cov-report=html
```

---

## 📦 File Structure Comparison

### BEFORE Migration
```
SemantixRAG/
├── main.py                    ← CLI entry point (local only)
├── config/                    ← Separate directory
│   ├── settings.py
│   └── opa/
│       ├── access.rego
│       ├── audit.rego
│       └── masking.rego
├── src/                       ← Flat structure
│   ├── __init__.py
│   ├── pipeline.py
│   ├── models.py
│   ├── api/
│   ├── cdc/
│   ├── chunking/
│   ├── compliance/
│   ├── embeddings/
│   ├── extractors/
│   ├── indexing/
│   ├── knowledge/
│   ├── monitoring/
│   └── observability/
└── requirements.txt           ← Text file (not PyPI friendly)
```

### AFTER Migration
```
SemantixRAG/
├── pyproject.toml             ← ✅ PEP 621 configuration
├── MANIFEST.in                ← ✅ Package data manifest
├── src/
│   └── semantixrag/           ← ✅ Namespace package
│       ├── __init__.py
│       ├── cli.py             ← ✅ New: Global CLI
│       ├── resources.py       ← ✅ New: Resource loader
│       ├── pipeline.py        ← ✅ Updated: Relative imports
│       ├── models.py
│       ├── config/            ← ✅ Moved: Inside package
│       │   ├── settings.py    ← ✅ Updated: Imports
│       │   └── opa/
│       │       ├── access.rego
│       │       ├── audit.rego
│       │       └── masking.rego
│       ├── api/               ← ✅ Moved
│       ├── cdc/               ← ✅ Moved
│       ├── chunking/          ← ✅ Moved
│       ├── compliance/        ← ✅ Moved
│       ├── embeddings/        ← ✅ Moved
│       ├── extractors/        ← ✅ Moved
│       ├── indexing/          ← ✅ Moved
│       ├── knowledge/         ← ✅ Moved
│       ├── monitoring/        ← ✅ Moved
│       └── observability/     ← ✅ Moved
├── tests/                     ← ✅ Updated: Imports
├── main.py                    ← ℹ️ Backwards compatibility
└── requirements.txt           ← ℹ️ Deprecated (use pyproject.toml)
```

---

## 🚀 Publishing Workflow

### Local Testing
```bash
# 1. Build
python -m build

# 2. Install locally
pip install dist/semantixrag-2.0.0-py3-none-any.whl

# 3. Test CLI
semantixrag init
semantixrag search "test"
```

### TestPyPI (Staging)
```bash
# 1. Upload to TestPyPI
python -m twine upload --repository testpypi dist/semantixrag-2.0.0*

# 2. Install from TestPyPI
pip install -i https://test.pypi.org/simple/ semantixrag==2.0.0

# 3. Verify
semantixrag --help
```

### PyPI (Production)
```bash
# 1. Upload to PyPI
python -m twine upload dist/semantixrag-2.0.0*

# 2. Anyone can now install:
pip install semantixrag

# 3. Global command available:
semantixrag init
```

---

## 📝 Configuration Files Reference

### pyproject.toml Highlights
```toml
[project]
name = "semantixrag"
version = "2.0.0"
requires-python = ">=3.11"

[project.scripts]
semantixrag = "semantixrag.cli:main"  # ← CLI entry point

[tool.setuptools.package-data]
semantixrag = [
    "config/opa/*.rego",              # ← Include .rego files
    "*.html",
    ".env.example",
]
```

### MANIFEST.in Highlights
```
recursive-include src/semantixrag *.py
recursive-include src/semantixrag *.rego    # ← Explicit inclusion
recursive-include tests *.py
```

---

## ✅ Checklist Before Publishing

- [ ] `pyproject.toml` is valid and complete
- [ ] All imports updated (test `grep` commands above)
- [ ] `.rego` files in `src/semantixrag/config/opa/`
- [ ] `MANIFEST.in` includes all necessary files
- [ ] Build succeeds: `python -m build`
- [ ] Wheel contents verified (contains `.rego` files)
- [ ] Local installation works: `pip install dist/semantixrag-2.0.0*`
- [ ] CLI entry point works: `semantixrag --help`
- [ ] Tests pass: `pytest tests/ -v`
- [ ] No circular imports
- [ ] Documentation updated

---

## 🔗 Related Files

- **Main Guide:** `PYPI_PUBLICATION_GUIDE.md`
- **CLI Code:** `src/semantixrag/cli.py`
- **Resource Loader:** `src/semantixrag/resources.py`
- **Configuration:** `pyproject.toml`
- **Package Manifest:** `MANIFEST.in`

---

## 📚 References

- **PEP 517/518:** Build system requirements and configuration
- **PEP 621:** pyproject.toml configuration
- **setuptools:** https://setuptools.pypa.io/
- **importlib.resources:** https://docs.python.org/3.12/library/importlib.resources.html

---

## 🔄 Additional Pipeline Refactoring (Post-PyPI)

### Async/Await Pipeline Modernization

**File:** `src/semantixrag/pipeline.py`

| Change | Detail |
|--------|--------|
| `process_document` | Converted from `def` to `async def` |
| `process_directory` | Converted from `def` to `async def` |
| Graph writes | `await self.graph_writer.write_entities_batch(...)` replaces per-chunk sequential calls |
| CLI integration | `cli.py` and `main.py` updated to call async methods via `asyncio.run()` |

### Batched Graph Writes (Neo4j Bottleneck Fix)

**Problem:** The original pipeline looped sequentially over every chunk, making individual blocking Neo4j network calls.

**Fix:** All entities are now collected into a unified `batch_data` payload and written via a single `write_entities_batch(batch_data, tenant_id)` call.

### Concurrent Directory Processing

**File:** `src/semantixrag/pipeline.py`

- `process_directory` now uses `asyncio.gather(*tasks, return_exceptions=True)`
- A configurable `asyncio.Semaphore(max_concurrency=4)` prevents rate-limit issues on embedding/graph backends
- Failures in one document do not block processing of others

### Granular Fault Tolerance

Every pipeline execution now returns `layer_success`:

```json
{
  "layer_success": {
    "vector": true,
    "graph": true,
    "metadata": true
  }
}
```

- If OpenSearch indexing succeeds but Neo4j fails, the result shows `vector: true, graph: false`
- Metrics are updated appropriately (`documents.processed` vs `documents.failed`)
- No partial state is left unaccounted for

### Config-Driven Table Extraction Mock

**File:** `src/semantixrag/config/settings.py`

- Added `use_mock_tables: bool = False`
- `pipeline.py` now instantiates `TableExtractor(use_mock=settings.use_mock_tables)`
- Removed hardcoded production mock (`use_mock=True`) from the constructor

### Interrupt Safety Fix

**File:** `src/semantixrag/pipeline.py`

- `_normalize_result` now catches `Exception` instead of `BaseException`
- `KeyboardInterrupt` and `SystemExit` propagate correctly during directory batch runs

---

**Last Updated:** June 26, 2026  
**Status:** Production hardened ✅
