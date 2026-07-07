# SemantixRAG — AI-Native Data Platform (v2.0)

[![GitHub](https://img.shields.io/badge/GitHub-SemantixRAG-6c5ce7?style=flat&logo=github)](https://github.com/SemantixRAG/SemantixRAG)
[![License: MIT](https://img.shields.io/badge/License-MIT-00e676?style=flat)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-00e5ff?style=flat&logo=python)](https://python.org)
[![CI](https://img.shields.io/github/actions/workflow/status/SemantixRAG/SemantixRAG/ci.yml?branch=main&style=flat)](https://github.com/SemantixRAG/SemantixRAG/actions)

A production-grade, open-source AI-native data platform featuring end-to-end RAG ingestion, knowledge graph integration (GraphRAG), AI observability (Obsidian), automated compliance (GuardRail), multi-modal extraction, and a REST API server — all running locally with zero cloud dependencies.

**🌐 Website:** [https://semantixrag.github.io/SemantixRAG/](https://semantixrag.github.io/SemantixRAG/)  
**📦 GitHub:** [github.com/SemantixRAG/SemantixRAG](https://github.com/SemantixRAG/SemantixRAG)  
**📖 License:** MIT

---

## Platform Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           SemantixRAG Platform v2.0                        │
├────────────────────────────────────────────────────────────────────────────┤
│  API Gateway (FastAPI)  ───  OPA Policy Engine ───  AuthZ & Rate Limiting  │
├────────────────────────────────────────────────────────────────────────────┤
│  Core Pipeline:                                                            │
│    Extraction → Chunking → Enrichment → Embedding → Indexing               │
│       │             │            │            │          │                 │
│       │  VLM/Whisper│  Header    │  LLM Summ. │  BGE-m3  │  OpenSearch     │
│       │  Multi-modal│  Splitter  │  Entity    │  JinaCLIP│  Neo4j Graph    │
│       │             │            │  PII Scan  │  CLAP    │  (GraphRAG)     │
├────────────────────────────────────────────────────────────────────────────┤
│  Obsidian    │  GuardRail  │  GraphRAG    │  CostSentinel  │  AdminCopilot │
│  Tracing     │  PII Detect │  Entity      │  Cost Track    │  NL Admin     │
│  Metrics     │  Masking    │  KG Write    │  Optimize      │  Auto Config  │
│  Eval Harness│  DSAR       │  Graph Search│  Budget Guard  │  Reports      │
└────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Status |
|:---|:---|:---|
| **Orchestration** | Python 3.11+ | Core |
| **Containerization** | Docker & Docker Compose | Core |
| **Vector Database** | OpenSearch (k-NN + BM25 search) | Core |
| **Knowledge Graph** | Neo4j 5.15 (Cypher + APOC) | **NEW** |
| **API Server** | FastAPI + Uvicorn + Gunicorn | **NEW** |
| **Policy Engine** | Open Policy Agent (OPA) + Rego | **NEW** |
| **PII Detection** | Microsoft Presidio + Regex fallback | **NEW** |
| **Parsing** | Unstructured.io, PyMuPDF, PyPDF | Core |
| **VLM Fallback** | LLaVA / ColPali (images) | Core |
| **Audio Transcription** | OpenAI Whisper | **NEW** |
| **Embeddings** | BAAI/bge-m3 (1024-dim, multilingual) | Core |
| **Multi-modal Embeddings** | JinaCLIP (text+image), CLAP (audio) | **NEW** |
| **Summarization** | Gemma / Llama (via Ollama or HuggingFace) | Core |
| **CDC** | Python Watchdog | Core |
| **Testing** | Pytest + pytest-asyncio + pytest-cov (41+ tests) | **NEW** |
| **CI/CD** | GitHub Actions (lint, test, Trivy, Docker) | **NEW** |

## Project Structure (v2.0)

```
SemantixRAG/
├── .github/workflows/
│   └── ci.yml                      # CI/CD pipeline
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Pydantic settings (enhanced)
│   └── opa/
│       ├── access.rego             # RBAC/ABAC policy
│       ├── masking.rego            # Conditional masking policy
│       └── audit.rego              # Audit level classification
├── docker/
│   ├── docker-compose.yml          # OpenSearch + Neo4j + Redis + OPA
│   ├── opensearch.yml              # OpenSearch configuration
│   └── Dockerfile                  # Python app container
├── documents/
│   └── sample_document.md
├── src/
│   ├── __init__.py
│   ├── models.py                   # Enhanced Pydantic models
│   ├── pipeline.py                 # Enhanced orchestrator with P0 features
│   ├── api/                        # NEW: FastAPI server
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry point
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── ingestion.py        # POST /v1/ingest
│   │       ├── retrieval.py        # POST /v1/query
│   │       ├── compliance.py       # POST /v1/compliance/pii/scan, /dsar
│   │       ├── observability.py    # POST /v1/observability/traces
│   │       └── admin.py            # POST /v1/admin/query (AdminCopilot)
│   ├── compliance/                 # NEW: GuardRail
│   │   ├── __init__.py
│   │   ├── pii_scanner.py          # Presidio + regex PII detection
│   │   ├── masking.py              # Dynamic PII masking engine
│   │   └── dsar.py                 # GDPR DSAR automation
│   ├── knowledge/                  # NEW: GraphRAG
│   │   ├── __init__.py
│   │   ├── entity_extractor.py     # spaCy NER + entity linking
│   │   └── ontology.py             # Domain ontologies + auto-discovery
│   ├── observability/              # NEW: Obsidian
│   │   ├── __init__.py
│   │   ├── tracer.py               # Distributed tracing
│   │   ├── evaluator.py            # RAG quality metrics
│   │   └── metrics.py              # Counters, histograms, cost tracking
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── unstructured_extractor.py
│   │   ├── table_extractor.py
│   │   └── multimodal_extractor.py # NEW: VLM + Whisper + video
│   ├── chunking/
│   │   ├── __init__.py
│   │   ├── header_splitter.py
│   │   └── enricher.py
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── embedder.py
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── index_manager.py
│   │   ├── bulk_indexer.py
│   │   ├── hybrid_search.py
│   │   └── graph_writer.py         # NEW: Neo4j async writer
│   ├── cdc/
│   │   ├── __init__.py
│   │   ├── watcher.py
│   │   └── incremental.py
│   └── monitoring/
│       ├── __init__.py
│       └── logger.py
├── tests/
│   ├── test_knowledge.py           # NEW: 11 GraphRAG tests
│   ├── test_compliance.py          # NEW: 12 GuardRail tests
│   └── test_observability.py       # NEW: 18 Obsidian tests
├── main.py                         # CLI entry point
├── requirements.txt                # Enhanced dependencies
├── .env.example                    # Enhanced config template
├── README.md
└── index.html                      # Project landing page (v2.0)
```

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/SemantixRAG/SemantixRAG.git
cd SemantixRAG
```

### 2. Start Infrastructure

```bash
cd docker
docker-compose up -d
```

This starts all platform services:
- **OpenSearch** on `localhost:9200` (vector store + BM25 search)
- **OpenSearch Dashboards** on `localhost:5601` (visualization)
- **Neo4j** on `localhost:7687` / `7474` (knowledge graph)
- **Redis** on `localhost:6379` (caching + queue)
- **OPA** on `localhost:8181` (policy engine)

### 3. Install Python Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 4. Initialize Indexes

```bash
python main.py init
```

### 5. Ingest Documents

```bash
python main.py ingest ./documents/sample_document.md
python main.py ingest ./documents/
```

### 6. Search

```bash
python main.py search "machine learning"
python main.py search "reinforcement learning" --top-k 10
```

### 7. Start API Server

```bash
python -m uvicorn src.api.main:app --reload
```

Now you can query via REST:

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "reinforcement learning", "strategy": "graph"}'
```

### 8. Run Tests

```bash
python -m pytest tests/ -v
```

## CLI Commands

| Command | Description |
|:---|:---|
| `init` | Initialize OpenSearch index with k-NN mapping |
| `ingest <path>` | Ingest a document or directory with entity extraction + PII scan |
| `watch <dir>` | Watch a directory for file changes (CDC) with auto-reindex |
| `search <query>` | Search indexed documents with hybrid retrieval |
| `stats` | Show index statistics |

## API Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/health` | Health check |
| POST | `/v1/ingest` | Upload and process a document |
| GET | `/v1/ingest/{id}/status` | Check ingestion status |
| POST | `/v1/query` | Semantic search with hybrid/graph retrieval |
| POST | `/v1/admin/query` | Natural-language platform administration |
| POST | `/v1/observability/traces` | Ingest telemetry traces |
| GET | `/v1/observability/metrics` | Query pipeline metrics |
| GET | `/v1/observability/evaluation` | Query RAG quality metrics |
| POST | `/v1/compliance/pii/scan` | Scan text for PII |
| POST | `/v1/compliance/dsar` | Execute GDPR DSAR request |
| GET | `/v1/compliance/dsar/{id}` | Check DSAR status |

## P0 Products (v2.0)

### 🕵️ Obsidian — AI Observability
- End-to-end distributed tracing for every pipeline stage (extraction, chunking, enrichment, embedding, indexing, graph write, PII scan)
- RAG quality metrics: faithfulness, answer relevancy, context precision, MRR, Recall@k, Precision@k
- Cost tracking with per-operation, per-model, per-tenant attribution
- Latency histograms with P50/P95/P99 aggregation
- Sampling configuration for high-volume pipelines

### 🕸️ GraphRAG — Knowledge Graph Integration
- Automatic named entity recognition via spaCy at ingestion time
- Entity linking: chunks → entities via `MENTIONS` relationships in Neo4j
- Entity resolution and coreference grouping
- Multi-hop Cypher traversal: `search_related_entities(names, hops=2)`
- Domain ontologies: general, healthcare, legal, finance with auto-discovery
- Graph traversal results fused with vector + BM25 via RRF

### 🛡️ GuardRail — Automated Compliance
- PII detection via Microsoft Presidio (30+ types, score-thresholded) with regex fallback
- Dynamic masking: type-specific tokens ([EMAIL], [SSN]) or uniform masking
- Risk level classification: low / medium / high based on PII type
- GDPR DSAR automation: find / delete / export subject data across document, chunk, embedding, and memory indexes
- OPA policy engine: Rego policies for access control, masking strategy, audit level

### 🎨 Multi-Modal RAG
- **Images**: VLM (LLaVA) captioning for images
- **Audio**: Whisper transcription for MP3, WAV, M4A, OGG, FLAC
- **Video**: OpenCV frame sampling at configurable intervals
- Text-only fallback when models are unavailable (mock mode)

## Configuration

All settings configurable via `.env` file (prefix `RAG_`):

### Core

| Variable | Default | Description |
|:---|:---|:---|
| `RAG_OPENSEARCH_HOST` | `localhost` | OpenSearch host |
| `RAG_OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `RAG_OPENSEARCH_INDEX` | `rag_documents` | Index name |
| `RAG_EMBEDDING_MODEL_NAME` | `BAAI/bge-m3` | Embedding model |
| `RAG_EMBEDDING_DIMENSION` | `1024` | Vector dimension |
| `RAG_CHUNK_MAX_TOKENS` | `512` | Max tokens per chunk |
| `RAG_CHUNK_OVERLAP_TOKENS` | `64` | Chunk overlap tokens |
| `RAG_WATCH_DIRECTORY` | `./documents` | Watch directory |

### Neo4j (GraphRAG)

| Variable | Default | Description |
|:---|:---|:---|
| `RAG_NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `RAG_NEO4J_USER` | `neo4j` | Neo4j username |
| `RAG_NEO4J_PASSWORD` | `password` | Neo4j password |
| `RAG_NEO4J_DATABASE` | `rag` | Neo4j database name |

### Observability (Obsidian)

| Variable | Default | Description |
|:---|:---|:---|
| `RAG_OBSERVABILITY_ENABLED` | `True` | Enable tracing |
| `RAG_OBSERVABILITY_INDEX` | `rag_observability` | OpenSearch telemetry index |
| `RAG_OBSERVABILITY_SAMPLE_RATE` | `1.0` | Trace sampling rate (0-1) |

### Compliance (GuardRail)

| Variable | Default | Description |
|:---|:---|:---|
| `RAG_PII_SCAN_ENABLED` | `True` | Enable PII scanning on ingestion |
| `RAG_PII_SCAN_DEPTH` | `standard` | Scan depth (standard/deep) |
| `RAG_MASKING_ENABLED` | `True` | Auto-mask PII in chunks |
| `RAG_AUDIT_LOG_ENABLED` | `True` | Enable audit logging |

### Knowledge Graph

| Variable | Default | Description |
|:---|:---|:---|
| `RAG_ENTITY_EXTRACTION_ENABLED` | `True` | Enable NER at ingestion |
| `RAG_ENTITY_CONFIDENCE_THRESHOLD` | `0.8` | Minimum entity confidence |

### Cost Sentinel

| Variable | Default | Description |
|:---|:---|:---|
| `RAG_COST_TRACKING_ENABLED` | `True` | Enable cost tracking |
| `RAG_COST_ALERT_THRESHOLD_USD` | `100.0` | Alert threshold |

## Risk Mitigations

| Risk | Mitigation |
|:---|:---|
| Table structure loss | VLM fallback for complex tables |
| OpenSearch memory | Tuned `ef_construction` and `m` parameters |
| Orphaned chunks | Contextual enrichment (title+summary in every chunk) |
| Indexing bottlenecks | Batch processing, `_bulk` API, async |
| Neo4j connection failure | Graceful degradation — pipeline continues without graph |
| PII false positives | Tunable confidence threshold; human-in-the-loop |
| LLM API failure | Circuit breaker pattern with exponential backoff |
| Embedding model unavailable | Graceful fallback to zero vectors |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_knowledge.py -v
python -m pytest tests/test_compliance.py -v
python -m pytest tests/test_observability.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Contributing

Contributions are welcome! Please open an issue or pull request on [GitHub](https://github.com/SemantixRAG/SemantixRAG).

## License

MIT — see [LICENSE](LICENSE) for details.
