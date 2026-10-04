"""
Repository for persisting and querying system snapshots in MongoDB with local file fallback.
"""
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import pymongo
from config.settings import settings
from config.logging_config import get_logger
from database.mongo_client import get_mongo_manager
from models.system_models import CompleteSystemSnapshot

logger = get_logger("database.repository")


class SystemSnapshotRepository:
    """Provides high-level CRUD operations for CompleteSystemSnapshot entities."""

    def __init__(self):
        self.manager = get_mongo_manager()
        self.cache_dir = settings.offline_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Creates compound and single-field MongoDB indexes for fast querying."""
        collection = self.manager.get_collection()
        if collection is not None:
            try:
                collection.create_index([("timestamp", pymongo.DESCENDING)], background=True)
                collection.create_index(
                    [("machine_name", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                    background=True,
                )
                collection.create_index([("availability.status", pymongo.ASCENDING)], background=True)
                logger.debug("MongoDB indexes verified.")
            except Exception as exc:
                logger.warning(f"Could not initialize MongoDB indexes: {exc}")

    def save_snapshot(self, snapshot: CompleteSystemSnapshot) -> str:
        """
        Stores the snapshot into MongoDB collection and mirrors a backup copy to local disk cache.
        Returns the snapshot identifier.
        """
        doc = snapshot.to_mongo_doc()
        saved_to_mongo = False

        # 1. Attempt MongoDB storage
        collection = self.manager.get_collection()
        if collection is not None:
            try:
                collection.replace_one({"_id": doc["_id"]}, doc, upsert=True)
                saved_to_mongo = True
                logger.info(f"Snapshot '{snapshot.snapshot_id}' stored in MongoDB ({collection.full_name}).")
            except Exception as exc:
                logger.warning(f"Failed to write snapshot to MongoDB ({exc}). Falling back to local disk storage.")

        # 2. Resilient local disk mirroring (latest + historical timestamped JSON)
        try:
            clean_machine = re.sub(r"[^\w\-_\.]", "_", snapshot.machine_name)
            clean_ts = snapshot.timestamp.replace(":", "-").replace(".", "-")

            latest_file = self.cache_dir / f"{clean_machine}_latest.json"
            history_file = self.cache_dir / f"{clean_machine}_{clean_ts}.json"

            json_data = snapshot.model_dump_json(indent=2)
            latest_file.write_text(json_data, encoding="utf-8")
            history_file.write_text(json_data, encoding="utf-8")

            logger.info(f"Snapshot mirrored to local cache: {latest_file.name}")
        except Exception as file_err:
            logger.error(f"Error mirroring snapshot to local disk: {file_err}")

        return snapshot.snapshot_id

    def get_latest_snapshot(self, machine_name: Optional[str] = None) -> Optional[CompleteSystemSnapshot]:
        """
        Retrieves the most recent snapshot for a target machine (or overall latest).
        Queries MongoDB first; falls back to local JSON cache if offline.
        """
        # Try MongoDB
        collection = self.manager.get_collection()
        if collection is not None:
            try:
                query: Dict[str, Any] = {}
                if machine_name:
                    query["machine_name"] = machine_name
                raw_doc = collection.find_one(query, sort=[("timestamp", pymongo.DESCENDING)])
                if raw_doc:
                    if "_id" in raw_doc:
                        raw_doc["snapshot_id"] = str(raw_doc["_id"])
                    return CompleteSystemSnapshot.model_validate(raw_doc)
            except Exception as exc:
                logger.warning(f"Failed to query MongoDB for latest snapshot: {exc}")

        # Fallback to local cache files
        try:
            candidates: List[Path] = []
            if machine_name:
                clean_m = re.sub(r"[^\w\-_\.]", "_", machine_name)
                latest_p = self.cache_dir / f"{clean_m}_latest.json"
                if latest_p.exists():
                    candidates.append(latest_p)
                candidates.extend(self.cache_dir.glob(f"{clean_m}_*.json"))
            else:
                candidates.extend(self.cache_dir.glob("*_latest.json"))
                candidates.extend(self.cache_dir.glob("*.json"))

            if candidates:
                # Sort by file modification time descending
                candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                for cand in candidates:
                    try:
                        content = cand.read_text(encoding="utf-8")
                        return CompleteSystemSnapshot.model_validate_json(content)
                    except Exception:
                        continue
        except Exception as exc:
            logger.error(f"Error reading latest snapshot from local cache: {exc}")

        return None

    def get_snapshot_history(
        self, machine_name: Optional[str] = None, limit: int = 50
    ) -> List[CompleteSystemSnapshot]:
        """
        Retrieves a historical series of snapshots, ordered from newest to oldest.
        """
        results: List[CompleteSystemSnapshot] = []

        # Try MongoDB
        collection = self.manager.get_collection()
        if collection is not None:
            try:
                query: Dict[str, Any] = {}
                if machine_name:
                    query["machine_name"] = machine_name
                cursor = collection.find(query).sort("timestamp", pymongo.DESCENDING).limit(limit)
                for doc in cursor:
                    if "_id" in doc:
                        doc["snapshot_id"] = str(doc["_id"])
                    results.append(CompleteSystemSnapshot.model_validate(doc))
                return results
            except Exception as exc:
                logger.warning(f"Failed to retrieve snapshot history from MongoDB: {exc}")

        # Fallback to local cache files
        try:
            pattern = "*.json" if not machine_name else f"*{re.sub(r'[^\\w\\-_\\.]', '_', machine_name)}*.json"
            files = list(self.cache_dir.glob(pattern))
            # Filter out '_latest.json' duplicate aliases if raw historical files exist
            hist_files = [f for f in files if not f.name.endswith("_latest.json")] or files
            hist_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            for p in hist_files[:limit]:
                try:
                    content = p.read_text(encoding="utf-8")
                    results.append(CompleteSystemSnapshot.model_validate_json(content))
                except Exception:
                    continue
        except Exception as exc:
            logger.error(f"Error reading snapshot history from local cache: {exc}")

        return results

    def get_all_machines(self) -> List[str]:
        """Returns the distinct list of monitored machine names."""
        collection = self.manager.get_collection()
        if collection is not None:
            try:
                return sorted(collection.distinct("machine_name"))
            except Exception:
                pass

        # Scan local cache
        machines = set()
        for p in self.cache_dir.glob("*.json"):
            parts = p.name.split("_")
            if parts:
                machines.add(parts[0])
        return sorted(list(machines))

    def get_health_status(self) -> Dict[str, Any]:
        """Returns storage telemetry, MongoDB connectivity, and cache counts."""
        mongo_status = self.manager.check_health()
        local_files_count = len(list(self.cache_dir.glob("*.json")))

        db_count = 0
        collection = self.manager.get_collection()
        if collection is not None:
            try:
                db_count = collection.count_documents({})
            except Exception:
                pass

        return {
            "mongodb": mongo_status,
            "storage": {
                "mongodb_documents": db_count,
                "local_cache_files": local_files_count,
                "cache_directory": str(self.cache_dir),
            },
        }


# Singleton repository instance
snapshot_repository = SystemSnapshotRepository()
