"""
MongoDB client manager with connection pooling, health checks, and resilient offline fallback.
"""
from typing import Optional
import pymongo
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("database.mongo_client")


class MongoDBManager:
    """Manages the MongoDB client lifecycle and connection health."""

    def __init__(self):
        self._client: Optional[pymongo.MongoClient] = None
        self._is_connected: bool = False
        self._last_error: Optional[str] = None
        self.connect()

    def connect(self) -> bool:
        """Establishes connection to MongoDB and performs an active ping check."""
        try:
            logger.info(f"Connecting to MongoDB at '{settings.mongo_uri}' (DB: '{settings.mongo_db_name}')...")
            self._client = pymongo.MongoClient(
                settings.mongo_uri,
                serverSelectionTimeoutMS=settings.mongo_timeout_ms,
                connectTimeoutMS=settings.mongo_timeout_ms,
                socketTimeoutMS=settings.mongo_timeout_ms,
                maxPoolSize=50,
                minPoolSize=5,
            )
            # Force immediate ping to verify connection
            self._client.admin.command("ping")
            self._is_connected = True
            self._last_error = None
            logger.info(f"Successfully connected to MongoDB server at '{settings.mongo_uri}'.")
            return True

        except (ServerSelectionTimeoutError, ConnectionFailure) as conn_err:
            self._is_connected = False
            self._last_error = f"MongoDB server unreachable at {settings.mongo_uri}: {conn_err}"
            logger.warning(
                f"{self._last_error}. Operational resilience mode enabled: snapshots will be saved to local disk cache ({settings.offline_cache_dir})."
            )
            return False

        except PyMongoError as p_err:
            self._is_connected = False
            self._last_error = f"PyMongo error: {p_err}"
            logger.error(self._last_error)
            return False

        except Exception as exc:
            self._is_connected = False
            self._last_error = f"Unexpected MongoDB connection error: {exc}"
            logger.error(self._last_error)
            return False

    @property
    def is_connected(self) -> bool:
        """Indicates whether MongoDB is currently reachable."""
        return self._is_connected

    @property
    def client(self) -> Optional[pymongo.MongoClient]:
        """Returns the raw MongoClient instance."""
        return self._client

    def get_database(self) -> Optional[pymongo.database.Database]:
        """Returns the configured database instance if connected."""
        if self._is_connected and self._client is not None:
            return self._client[settings.mongo_db_name]
        return None

    def get_collection(self) -> Optional[pymongo.collection.Collection]:
        """Returns the snapshots collection if connected."""
        db = self.get_database()
        if db is not None:
            return db[settings.mongo_collection_name]
        return None

    def check_health(self) -> dict:
        """Performs a live health check and returns connection metrics."""
        if not self._client:
            self.connect()

        try:
            if self._client:
                self._client.admin.command("ping")
                self._is_connected = True
                return {
                    "connected": True,
                    "uri": settings.mongo_uri,
                    "database": settings.mongo_db_name,
                    "collection": settings.mongo_collection_name,
                    "status": "healthy",
                    "error": None,
                }
        except Exception as e:
            self._is_connected = False
            self._last_error = str(e)

        return {
            "connected": False,
            "uri": settings.mongo_uri,
            "database": settings.mongo_db_name,
            "collection": settings.mongo_collection_name,
            "status": "degraded_offline_fallback",
            "error": self._last_error,
        }

    def close(self) -> None:
        """Closes the MongoDB connection pool."""
        if self._client:
            self._client.close()
            self._is_connected = False
            logger.info("MongoDB client connections closed.")


# Singleton instance
_mongo_manager: Optional[MongoDBManager] = None


def get_mongo_manager() -> MongoDBManager:
    """Returns the singleton MongoDBManager instance."""
    global _mongo_manager
    if _mongo_manager is None:
        _mongo_manager = MongoDBManager()
    return _mongo_manager
