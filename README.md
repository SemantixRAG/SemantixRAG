# Production-Grade RAG Ingestion Pipeline

A robust, production-ready Retrieval-Augmented Generation (RAG) ingestion pipeline that preserves document structure during extraction, uses semantic chunking, and implements hybrid search indexing with OpenSearch.

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Phase 2     │    │  Phase 3     │    │  Phase 4     │    │  Phase 5     │
│  Extraction  │───▶│  Chunking &  │───▶│  Embedding & │───▶│  CDC &       │
│  & Parsing   │    │  Enrichment  │    │  Indexing    │    │  Maintenance │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  Unstructured.io    Header-Aware        BGE-m3 /           Watchdog
  / PyMuPDF          Splitter +          Sentence-          Directory
  + VLM fallback     LLM Summary         Transformers       Monitor
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | Python 3.11+ |
| **Containerization** | Docker & Docker Compose |
| **Vector Database** | OpenSearch (k-NN + BM25) |
| **Parsing** | Unstructured.io, PyMuPDF, PyPDF |
| **VLM Fallback** | LLaVA / ColPali (via API or Ollama) |
| **Embeddings** | BAAI/bge-m3 (HuggingFace sentence-transformers) |
| **Summarization** | Gemma / Llama (via Ollama) |
| **CDC** | Python Watchdog |

## Project Structure

```
rag_ingestion/
├── config/
│   ├── __init__.py
│   └── settings.py             # Pydantic settings from .env
├── docker/
│   ├── docker-compose.yml      # OpenSearch + Dashboards
│   ├── opensearch.yml          # OpenSearch configuration
│   └── Dockerfile              # Python app container
├── documents/
│   └── sample_document.md      # Sample document for testing
├── src/
│   ├── __init__.py             # Package exports
│   ├── models.py               # Pydantic data models
│   ├── pipeline.py             # Main ingestion orchestrator
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract extractor interface
│   │   ├── unstructured_extractor.py  # PDF/Text via Unstructured
│   │   └── table_extractor.py  # VLM fallback for tables
│   ├── chunking/
│   │   ├── __init__.py
│   │   ├── header_splitter.py  # Header-aware text splitter
│   │   └── enricher.py         # Contextual enrichment (LLM summary)
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── embedder.py         # BGE-m3 embedding model wrapper
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── connection.py       # OpenSearch singleton connection
│   │   ├── index_manager.py    # Index creation with k-NN mapping
│   │   ├── bulk_indexer.py     # High-throughput _bulk API indexing
│   │   └── hybrid_search.py    # Hybrid search (k-NN + BM25 + RRF)
│   ├── cdc/
│   │   ├── __init__.py
│   │   ├── watcher.py          # Directory watcher (watchdog)
│   │   └── incremental.py      # Incremental update logic
│   └── monitoring/
│       ├── __init__.py
│       └── logger.py           # Centralized logging setup
├── tests/                      # Test directory
├── .env                        # Environment variables
├── main.py                     # CLI entry point
├── requirements.txt            # Python dependencies
└── README.md
```

## Quick Start

### 1. Start OpenSearch

```bash
cd docker
docker-compose up -d
```

This starts:
- **OpenSearch** on `localhost:9200` (k-NN plugin enabled)
- **OpenSearch Dashboards** on `localhost:5601`

### 2. Install Python Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
# or: source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 3. Initialize the Index

```bash
python main.py init
```

### 4. Ingest Documents

```bash
# Ingest a single file
python main.py ingest ./documents/sample_document.md

# Ingest all documents in a directory
python main.py ingest ./documents/
```

### 5. Search

```bash
python main.py search "machine learning"
python main.py search "supervised learning" --top-k 10
```

### 6. Watch for Changes (CDC)

```bash
python main.py watch ./documents/
```

### 7. Check Statistics

```bash
python main.py stats
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize OpenSearch index with k-NN mapping |
| `ingest <path>` | Ingest a document or directory |
| `watch <dir>` | Watch a directory for file changes (CDC) |
| `search <query>` | Search indexed documents |
| `stats` | Show index statistics |

## Pipeline Phases

### Phase 1: Infrastructure (Docker)
- OpenSearch single-node cluster with k-NN plugin
- Configurable via `docker-compose.yml` and `opensearch.yml`

### Phase 2: Document Parsing & Extraction
- **Unstructured.io** for standard PDF/text extraction
- Element type mapping: Header, Paragraph, List Item, Table
- **VLM fallback** (LLaVA/ColPali) for complex table layouts

### Phase 3: Structure-Aware Chunking & Enrichment
- **Header-aware splitting**: Groups paragraphs under parent headers
- **Contextual enrichment**: LLM-generated document summary prepended to each chunk
- Configurable max tokens (512) with overlap (64 tokens)

### Phase 4: Embedding & OpenSearch Indexing
- **BAAI/bge-m3** dense embeddings via sentence-transformers
- **Bulk indexing** via OpenSearch `_bulk` API
- **Hybrid search**: k-NN vector search + BM25 keyword search + RRF fusion

### Phase 5: CDC & Maintenance
- **Directory watching** via Python `watchdog`
- **Incremental updates**: Delete+reindex on file modification
- **Centralized logging** with console and file handlers

## Configuration

All settings are configurable via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_OPENSEARCH_HOST` | `localhost` | OpenSearch host |
| `RAG_OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `RAG_OPENSEARCH_INDEX` | `rag_documents` | Index name |
| `RAG_EMBEDDING_MODEL_NAME` | `BAAI/bge-m3` | Embedding model |
| `RAG_EMBEDDING_DIMENSION` | `1024` | Vector dimension |
| `RAG_CHUNK_MAX_TOKENS` | `512` | Max tokens per chunk |
| `RAG_CHUNK_OVERLAP_TOKENS` | `64` | Chunk overlap tokens |
| `RAG_WATCH_DIRECTORY` | `./documents` | Watch directory |

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Table structure loss | VLM fallback for complex tables |
| OpenSearch memory | Tuned `ef_construction` and `m` parameters |
| Orphaned chunks | Contextual enrichment (title+summary in every chunk) |
| Indexing bottlenecks | Batch processing, async decoupling |

## License

MIT