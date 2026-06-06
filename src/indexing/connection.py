"""OpenSearch connection singleton with connection pooling."""
import logging
from typing import Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings

logger = logging.getLogger(__name__)


class OpenSearchConnection:
    """Singleton managing the OpenSearch connection pool."""

    _instance: Optional["OpenSearchConnection"] = None
    _client: Optional[OpenSearch] = None

    def __new__(cls) -> "OpenSearchConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._client is not None:
            return
        self._connect()

    @retry(
        stop=stop_after_attempt(settings.opensearch_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(OpenSearchConnectionError),
    )
    def _connect(self) -> None:
        """Establish connection to OpenSearch."""
        host = settings.opensearch_host
        port = settings.opensearch_port

        logger.info(f"Connecting to OpenSearch at {host}:{port}...")

        self._client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection,
            timeout=settings.opensearch_timeout,
            max_retries=settings.opensearch_max_retries,
            retry_on_timeout=True,
        )

        # Verify connection
        info = self._client.info()
        logger.info(
            f"Connected to OpenSearch cluster: "
            f"{info.get('cluster_name', 'unknown')} "
            f"(version {info.get('version', {}).get('number', 'unknown')})"
        )

    @property
    def client(self) -> OpenSearch:
        """Get the OpenSearch client instance."""
        if self._client is None:
            self._connect()
        return self._client

    def ping(self) -> bool:
        """Check if the OpenSearch cluster is reachable."""
        try:
            return self._client.ping()
        except Exception:
            return False

    def close(self) -> None:
        """Close the connection."""
        if self._client is not None:
            try:
                self._client.transport.close()
            except Exception:
                pass
            self._client = None

    @classmethod
    def get_instance(cls) -> "OpenSearchConnection":
        """Get or create the singleton connection instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        if cls._instance is not None:
            cls._instance.close()
        cls._instance = None
        cls._client = None