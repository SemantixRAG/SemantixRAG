#!/usr/bin/env python3
"""RAG Ingestion Pipeline — CLI entry point.

Usage:
    python main.py init                     # Initialize OpenSearch index
    python main.py ingest <file_or_dir>     # Ingest a document or directory
    python main.py watch <directory>        # Watch a directory for changes
    python main.py search <query>           # Search indexed documents
    python main.py stats                    # Show index statistics
"""
import sys
import argparse
import logging
from pathlib import Path

# Add src to path for proper imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from semantixrag.config.settings import settings
from semantixrag import IngestionPipeline, setup_logging


def main():
    """Main CLI entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Production-Grade RAG Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize the OpenSearch index
  python main.py init

  # Ingest a single document
  python main.py ingest ./documents/report.pdf

  # Ingest all documents in a directory
  python main.py ingest ./documents/

  # Watch a directory for changes (CDC)
  python main.py watch ./documents/

  # Search indexed documents
  python main.py search "machine learning"

  # Show index statistics
  python main.py stats
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    subparsers.add_parser("init", help="Initialize OpenSearch index")

    # ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a document or directory")
    ingest_parser.add_argument("path", type=str, help="Path to document or directory")
    ingest_parser.add_argument(
        "--force", action="store_true", help="Recreate index before ingestion"
    )
    ingest_parser.add_argument(
        "--mock", action="store_true", default=True,
        help="Use mock summaries (no LLM required)"
    )

    # watch command
    watch_parser = subparsers.add_parser(
        "watch", help="Watch a directory for file changes (CDC)"
    )
    watch_parser.add_argument(
        "directory", type=str, nargs="?",
        default=settings.watch_directory,
        help="Directory to watch",
    )

    # search command
    search_parser = subparsers.add_parser("search", help="Search indexed documents")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument(
        "--top-k", type=int, default=5, help="Number of results (default: 5)"
    )

    # stats command
    subparsers.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    try:
        _execute_command(args, logger)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)


def _execute_command(args, logger):
    """Execute the CLI command."""
    pipeline = IngestionPipeline(use_mock_summaries=getattr(args, 'mock', True))

    if args.command == "init":
        _handle_init(pipeline, logger)

    elif args.command == "ingest":
        _handle_ingest(pipeline, args, logger)

    elif args.command == "watch":
        _handle_watch(pipeline, args, logger)

    elif args.command == "search":
        _handle_search(pipeline, args, logger)

    elif args.command == "stats":
        _handle_stats(pipeline, logger)


def _handle_init(pipeline, logger):
    """Initialize the OpenSearch index."""
    logger.info("Initializing OpenSearch index...")
    pipeline.initialize_index(force=False)
    logger.info(f"Index '{settings.opensearch_index}' is ready")


def _handle_ingest(pipeline, args, logger):
    """Ingest a document or directory."""
    path = Path(args.path)

    if args.force:
        logger.info("Force-recreating index...")
        pipeline.initialize_index(force=True)

    if path.is_dir():
        logger.info(f"Ingesting all documents from '{path}'...")
        results = pipeline.process_directory(path)
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(
            f"Ingested {success_count}/{len(results)} documents "
            f"from '{path}'"
        )
        for result in results:
            status = "✓" if result.get("success") else "✗"
            logger.info(f"  [{status}] {result.get('filename', '?')}: "
                        f"{result.get('chunks_count', 0)} chunks")

    elif path.is_file():
        logger.info(f"Ingesting document '{path}'...")
        result = pipeline.process_document(path)
        if result.get("success"):
            logger.info(
                f"✓ Ingested '{path.name}': "
                f"{result['chunks_count']} chunks, "
                f"{result['total_tokens']} tokens"
            )
        else:
            logger.error(f"✗ Failed to ingest '{path.name}': {result.get('error')}")

    else:
        logger.error(f"Path not found: {path}")


def _handle_watch(pipeline, args, logger):
    """Watch a directory for file changes."""
    from src.cdc import DirectoryWatcher, IncrementalUpdater
    from src.extractors.unstructured_extractor import UnstructuredExtractor

    watch_dir = Path(args.directory)
    watch_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting CDC watcher on '{watch_dir}'...")

    incremental = IncrementalUpdater()

    def on_created(file_path):
        logger.info(f"[CDC] New file detected: {file_path.name}")
        document_id = UnstructuredExtractor.generate_document_id(file_path)
        pipeline.process_document(file_path, document_id)

    def on_modified(file_path):
        logger.info(f"[CDC] File modified: {file_path.name}")
        document_id = UnstructuredExtractor.generate_document_id(file_path)
        incremental.before_reindex(file_path, document_id)
        pipeline.process_document(file_path, document_id)

    def on_deleted(file_path):
        logger.info(f"[CDC] File deleted: {file_path.name}")
        document_id = UnstructuredExtractor.generate_document_id(file_path)
        incremental.process_deletion(file_path, document_id)

    watcher = DirectoryWatcher(
        watch_dir=watch_dir,
        on_created=on_created,
        on_modified=on_modified,
        on_deleted=on_deleted,
    )

    try:
        watcher.start()
        logger.info("CDC watcher is running. Press Ctrl+C to stop.")
        import time
        while watcher.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping CDC watcher...")
        watcher.stop()


def _handle_search(pipeline, args, logger):
    """Search indexed documents."""
    try:
        query_vector = pipeline.embedder.encode([args.query])[0]
    except Exception:
        logger.warning("Embedding model not available; using zero vector")
        query_vector = [0.0] * settings.embedding_dimension

    results = pipeline.hybrid_search.search(
        query_text=args.query,
        query_vector=query_vector,
        size=args.top_k,
    )

    hits = results.get("hits", [])
    total = results.get("total", 0)

    if not hits:
        logger.info(f"No results found for: '{args.query}'")
        return

    logger.info(f"\nSearch results for: '{args.query}' ({total} total)")
    logger.info("=" * 80)

    for i, hit in enumerate(hits, 1):
        title = hit.get("document_title", "Untitled")
        header = hit.get("header_path", "")
        score = hit.get("score", 0)
        text_preview = hit.get("chunk_text", "")[:200].replace("\n", " ")

        logger.info(f"  {i}. [{score:.4f}] {title}")
        if header:
            logger.info(f"     Section: {header}")
        logger.info(f"     Preview: {text_preview}...")
        logger.info("")

    logger.info("=" * 80)


def _handle_stats(pipeline, logger):
    """Show index statistics."""
    stats = pipeline.index_manager.get_index_stats()
    if "error" in stats:
        logger.warning(stats["error"])
        return

    logger.info("\nOpenSearch Index Statistics")
    logger.info("=" * 40)
    logger.info(f"  Index:       {stats.get('index', 'N/A')}")
    logger.info(f"  Documents:   {stats.get('doc_count', 0)}")
    size_mb = stats.get("size_bytes", 0) / (1024 * 1024)
    logger.info(f"  Size:        {size_mb:.2f} MB")
    logger.info("=" * 40)


if __name__ == "__main__":
    main()