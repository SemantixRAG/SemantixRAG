"""Directory watcher using watchdog for Change Data Capture on local files."""
import os
import logging
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from config.settings import settings

logger = logging.getLogger(__name__)


class DocumentEventHandler(FileSystemEventHandler):
    """Handles file system events for the watched directory."""

    def __init__(
        self,
        on_created: Callable[[Path], None],
        on_modified: Callable[[Path], None],
        on_deleted: Callable[[Path], None],
        supported_extensions: set[str] = None,
    ):
        self.on_created = on_created
        self.on_modified = on_modified
        self.on_deleted = on_deleted
        self.supported_extensions = supported_extensions or {
            ".pdf", ".txt", ".md", ".docx", ".html", ".xml", ".csv"
        }
        self._last_events: dict[str, float] = {}
        self._debounce_seconds = 2.0

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in self.supported_extensions:
            return
        if self._is_debounced(str(path)):
            return
        logger.info(f"File created: {path.name}")
        self.on_created(path)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in self.supported_extensions:
            return
        if self._is_debounced(str(path)):
            return
        logger.info(f"File modified: {path.name}")
        self.on_modified(path)

    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in self.supported_extensions:
            return
        logger.info(f"File deleted: {path.name}")
        self.on_deleted(path)

    def _is_debounced(self, path_str: str) -> bool:
        """Debounce rapid-fire file system events."""
        now = time.time()
        last = self._last_events.get(path_str, 0)
        if now - last < self._debounce_seconds:
            return True
        self._last_events[path_str] = now
        return False


class DirectoryWatcher:
    """Watches a directory for file changes and triggers the ingestion pipeline.

    Uses watchdog to monitor file creation, modification, and deletion events.
    """

    def __init__(
        self,
        watch_dir: Optional[Path] = None,
        on_created: Optional[Callable] = None,
        on_modified: Optional[Callable] = None,
        on_deleted: Optional[Callable] = None,
    ):
        self.watch_dir = Path(watch_dir or settings.watch_directory)
        self.recursive = settings.watch_recursive
        self._observer: Optional[Observer] = None
        self._running = False

        # Default no-op callbacks
        self._on_created = on_created or (lambda p: None)
        self._on_modified = on_modified or (lambda p: None)
        self._on_deleted = on_deleted or (lambda p: None)

    def start(self) -> None:
        """Start watching the directory for changes."""
        if self._running:
            logger.warning("Watcher is already running")
            return

        self.watch_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Starting directory watcher on '{self.watch_dir}' "
            f"(recursive={self.recursive})"
        )

        event_handler = DocumentEventHandler(
            on_created=self._on_created,
            on_modified=self._on_modified,
            on_deleted=self._on_deleted,
        )

        self._observer = Observer()
        self._observer.schedule(
            event_handler,
            str(self.watch_dir),
            recursive=self.recursive,
        )
        self._observer.start()
        self._running = True
        logger.info(f"Directory watcher started on '{self.watch_dir}'")

    def stop(self) -> None:
        """Stop watching the directory."""
        if self._observer is not None and self._running:
            self._observer.stop()
            self._observer.join()
            self._running = False
            logger.info("Directory watcher stopped")

    @property
    def is_running(self) -> bool:
        return self._running