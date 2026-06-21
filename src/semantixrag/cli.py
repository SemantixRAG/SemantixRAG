#!/usr/bin/env python3
"""SemantixRAG CLI entry point for the global command-line interface.

This module provides the main entry point for the 'semantixrag' command,
which is registered in pyproject.toml as:

    [project.scripts]
    semantixrag = "semantixrag.cli:main"

This ensures that after `pip install semantixrag`, users can run:
    semantixrag init
    semantixrag ingest <path>
    semantixrag watch <directory>
    semantixrag search <query>
    semantixrag stats

Usage:
    semantixrag init                     # Initialize OpenSearch index
    semantixrag ingest <file_or_dir>     # Ingest a document or directory
    semantixrag watch <directory>        # Watch a directory for changes (CDC)
    semantixrag search <query>           # Search indexed documents
    semantixrag stats                    # Show index statistics
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Import from the semantixrag package
from semantixrag import IngestionPipeline, setup_logging
from semantixrag.config.settings import settings
from semantixrag.resources import get_rego_policy, get_all_rego_policies

logger = logging.getLogger(__name__)


def main() -> int:
    """Main CLI entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        prog="semantixrag",
        description="SemantixRAG v2.0 — AI-Native Data Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize the OpenSearch index
  semantixrag init

  # Ingest a single document
  semantixrag ingest ./documents/report.pdf

  # Ingest all documents in a directory
  semantixrag ingest ./documents/

  # Watch a directory for changes (CDC)
  semantixrag watch ./documents/

  # Search indexed documents
  semantixrag search "machine learning"

  # Show index statistics
  semantixrag stats
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
        help="Use mock summaries (no LLM required)",
    )

    # watch command
    watch_parser = subparsers.add_parser(
        "watch", help="Watch a directory for file changes (CDC)"
    )
    watch_parser.add_argument(
        "directory",
        type=str,
        nargs="?",
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
        return 0

    try:
        return _execute_command(args, logger)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1


def _execute_command(args, logger: logging.Logger) -> int:
    """Execute the CLI command."""
    pipeline = IngestionPipeline(use_mock_summaries=getattr(args, "mock", True))

    if args.command == "init":
        return _handle_init(pipeline, logger)

    elif args.command == "ingest":
        return _handle_ingest(pipeline, args, logger)

    elif args.command == "watch":
        return _handle_watch(pipeline, args, logger)

    elif args.command == "search":
        return _handle_search(pipeline, args, logger)

    elif args.command == "stats":
        return _handle_stats(pipeline, logger)

    return 0


def _handle_init(pipeline: IngestionPipeline, logger: logging.Logger) -> int:
    """Initialize the OpenSearch index."""
    logger.info("Initializing OpenSearch index...")
    try:
        pipeline.initialize_index(force=False)
        logger.info(f"Index '{settings.opensearch_index}' is ready")
        return 0
    except Exception as e:
        logger.error(f"Failed to initialize index: {e}")
        return 1


def _handle_ingest(
    pipeline: IngestionPipeline, args: argparse.Namespace, logger: logging.Logger
) -> int:
    """Ingest a document or directory."""
    path = Path(args.path)

    if args.force:
        logger.info("Force-recreating index...")
        try:
            pipeline.initialize_index(force=True)
        except Exception as e:
            logger.error(f"Failed to recreate index: {e}")
            return 1

    if path.is_dir():
        logger.info(f"Ingesting all documents from '{path}'...")
        try:
            results = pipeline.process_directory(path)
            success_count = sum(1 for r in results if r.get("success"))
            logger.info(
                f"Ingested {success_count}/{len(results)} documents from '{path}'"
            )
            for result in results:
                status = "✓" if result.get("success") else "✗"
                logger.info(
                    f"  [{status}] {result.get('filename', '?')}: "
                    f"{result.get('chunks_count', 0)} chunks"
                )
            return 0 if success_count == len(results) else 1
        except Exception as e:
            logger.error(f"Failed to ingest directory: {e}")
            return 1

    elif path.is_file():
        logger.info(f"Ingesting document '{path}'...")
        try:
            result = pipeline.process_document(path)
            if result.get("success"):
                logger.info(
                    f"✓ Ingested '{path.name}': "
                    f"{result['chunks_count']} chunks, "
                    f"{result['total_tokens']} tokens"
                )
                return 0
            else:
                logger.error(f"✗ Failed to ingest '{path.name}': {result.get('error')}")
                return 1
        except Exception as e:
            logger.error(f"Failed to ingest file: {e}")
            return 1

    else:
        logger.error(f"Path not found: {path}")
        return 1


def _handle_watch(
    pipeline: IngestionPipeline, args: argparse.Namespace, logger: logging.Logger
) -> int:
    """Watch a directory for file changes."""
    from semantixrag.cdc import DirectoryWatcher, IncrementalUpdater
    from semantixrag.extractors.unstructured_extractor import UnstructuredExtractor

    watch_dir = Path(args.directory)
    watch_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting CDC watcher on '{watch_dir}'...")

    incremental = IncrementalUpdater()

    def on_created(file_path: Path) -> None:
        logger.info(f"[CDC] New file detected: {file_path.name}")
        document_id = UnstructuredExtractor.generate_document_id(file_path)
        try:
            pipeline.process_document(file_path, document_id)
        except Exception as e:
            logger.error(f"Failed to process new file: {e}")

    def on_modified(file_path: Path) -> None:
        logger.info(f"[CDC] File modified: {file_path.name}")
        document_id = UnstructuredExtractor.generate_document_id(file_path)
        try:
            incremental.before_reindex(file_path, document_id)
            pipeline.process_document(file_path, document_id)
        except Exception as e:
            logger.error(f"Failed to process modified file: {e}")

    def on_deleted(file_path: Path) -> None:
        logger.info(f"[CDC] File deleted: {file_path.name}")
        document_id = UnstructuredExtractor.generate_document_id(file_path)
        try:
            incremental.process_deletion(file_path, document_id)
        except Exception as e:
            logger.error(f"Failed to process deletion: {e}")

    try:
        watcher = DirectoryWatcher(
            watch_dir=watch_dir,
            on_created=on_created,
            on_modified=on_modified,
            on_deleted=on_deleted,
        )
        watcher.start()
        logger.info("Press Ctrl+C to stop watching")
        watcher.wait()
        return 0
    except KeyboardInterrupt:
        logger.info("CDC watcher stopped")
        return 0
    except Exception as e:
        logger.error(f"CDC watcher error: {e}")
        return 1


def _handle_search(
    pipeline: IngestionPipeline, args: argparse.Namespace, logger: logging.Logger
) -> int:
    """Search indexed documents."""
    query = args.query
    top_k = args.top_k
    logger.info(f"Searching for: '{query}'")

    try:
        results = pipeline.search(query, top_k=top_k)
        if not results:
            logger.info("No results found")
            return 0

        logger.info(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            logger.info(f"\n[{i}] {result.get('source', {}).get('filename', 'Unknown')}")
            logger.info(f"    Score: {result.get('score', 'N/A')}")
            logger.info(f"    Content: {result.get('_source', {}).get('content', '')[:200]}...")
        return 0
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return 1


def _handle_stats(pipeline: IngestionPipeline, logger: logging.Logger) -> int:
    """Show index statistics."""
    try:
        stats = pipeline.get_stats()
        logger.info("Index Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        return 0
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
