"""
Application configuration management using Pydantic and python-dotenv.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if available
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


class AppSettings(BaseModel):
    """Strongly typed application configuration settings."""

    # Project directories
    base_dir: Path = Field(default=BASE_DIR)
    
    # WMI Target Machine
    wmi_host: str = Field(default_factory=lambda: os.getenv("WMI_HOST", "localhost"))
    wmi_user: Optional[str] = Field(default_factory=lambda: os.getenv("WMI_USER") or None)
    wmi_password: Optional[str] = Field(default_factory=lambda: os.getenv("WMI_PASSWORD") or None)
    wmi_namespace: str = Field(default_factory=lambda: os.getenv("WMI_NAMESPACE", r"root\cimv2"))

    # MongoDB Configuration
    mongo_uri: str = Field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    mongo_db_name: str = Field(default_factory=lambda: os.getenv("MONGO_DB_NAME", "wmi_system_monitor"))
    mongo_collection_name: str = Field(default_factory=lambda: os.getenv("MONGO_COLLECTION_NAME", "system_snapshots"))
    mongo_timeout_ms: int = Field(default_factory=lambda: int(os.getenv("MONGO_TIMEOUT_MS", "5000")))

    # Scheduler Settings
    collection_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("COLLECTION_INTERVAL_SECONDS", "60")))
    scheduler_enabled: bool = Field(default_factory=lambda: os.getenv("SCHEDULER_ENABLED", "true").lower() in ("true", "1", "yes"))

    # API Server Settings
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "127.0.0.1"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))

    # Logging and Offline Cache
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    log_file_path: Path = Field(default_factory=lambda: BASE_DIR / os.getenv("LOG_FILE_PATH", "logs/wmi_monitor.log"))
    offline_cache_dir: Path = Field(default_factory=lambda: BASE_DIR / os.getenv("OFFLINE_CACHE_DIR", "data/snapshots"))

    @property
    def is_remote_wmi(self) -> bool:
        """Determines whether the target WMI host is a remote computer."""
        host = (self.wmi_host or "").strip().lower()
        return bool(host and host not in ("localhost", "127.0.0.1", ".", ""))

    def ensure_directories(self) -> None:
        """Ensures that required log and data cache directories exist."""
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.offline_cache_dir.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = AppSettings()
settings.ensure_directories()
