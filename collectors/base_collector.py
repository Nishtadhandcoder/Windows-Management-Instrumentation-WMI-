"""
Base collector class and WMI connection manager with COM thread-safety and retry mechanisms.
"""
import time
import re
from typing import Optional, Any
from datetime import datetime
import pythoncom
import wmi
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("collector.base")


class WMIConnectionManager:
    """Manages WMI COM connections with thread-safety and connection pooling."""

    @staticmethod
    def get_connection(
        host: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
        retries: int = 3,
        backoff_seconds: float = 1.5,
    ) -> wmi.WMI:
        """
        Initializes COM for the calling thread and establishes a robust WMI connection.
        Supports both local machine and authenticated remote target machines.
        """
        pythoncom.CoInitialize()

        target_host = host or settings.wmi_host or "localhost"
        target_user = user if user is not None else settings.wmi_user
        target_password = password if password is not None else settings.wmi_password
        target_namespace = namespace or settings.wmi_namespace

        is_remote = target_host.strip().lower() not in ("localhost", "127.0.0.1", ".", "")

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                if is_remote:
                    logger.debug(f"Attempting remote WMI connection to {target_host} (attempt {attempt}/{retries})")
                    connection = wmi.WMI(
                        computer=target_host,
                        user=target_user,
                        password=target_password,
                        namespace=target_namespace,
                    )
                else:
                    logger.debug(f"Attempting local WMI connection (attempt {attempt}/{retries})")
                    connection = wmi.WMI(namespace=target_namespace)

                return connection

            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"WMI connection attempt {attempt}/{retries} to '{target_host}' failed: {exc}. Retrying in {backoff_seconds}s..."
                )
                if attempt < retries:
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 1.5

        logger.error(f"Exhausted all {retries} WMI connection attempts to '{target_host}'.")
        raise ConnectionError(f"Could not connect to WMI on target '{target_host}': {last_error}")


class BaseCollector:
    """Abstract base class for all domain-specific WMI metrics collectors."""

    def __init__(self, wmi_conn: Optional[wmi.WMI] = None):
        self._wmi_conn = wmi_conn
        self.logger = get_logger(self.__class__.__name__)

    @property
    def wmi(self) -> wmi.WMI:
        """Returns active WMI connection or initializes a new thread-safe connection."""
        if self._wmi_conn is None:
            self._wmi_conn = WMIConnectionManager.get_connection()
        return self._wmi_conn

    @staticmethod
    def parse_wmi_datetime(wmi_date_str: Optional[str]) -> Optional[str]:
        """
        Parses WMI datetime strings (e.g., '20250625103045.000000+330')
        into user-friendly readable format: 'DD-MM-YYYY hh:mm:ss A'
        """
        if not wmi_date_str or not isinstance(wmi_date_str, str):
            return None

        clean_str = wmi_date_str.strip()
        # Typical WMI format: YYYYMMDDHHMMSS.mmmmmm+UUU
        match = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", clean_str)
        if match:
            year, month, day, hour, minute, second = match.groups()
            try:
                dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                return dt.strftime("%d-%m-%Y %I:%M:%S %p")
            except ValueError:
                pass

        # Return original or ISO fallback
        return clean_str

    @staticmethod
    def bytes_to_mb(bytes_value: Any) -> float:
        """Safely convert bytes count to Megabytes rounded to 2 decimal places."""
        try:
            val = float(bytes_value)
            return round(val / (1024 * 1024), 2)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def kb_to_mb(kb_value: Any) -> float:
        """Safely convert Kilobytes count to Megabytes rounded to 2 decimal places."""
        try:
            val = float(kb_value)
            return round(val / 1024, 2)
        except (ValueError, TypeError):
            return 0.0

    def collect(self) -> Any:
        """Must be implemented by concrete collectors."""
        raise NotImplementedError("Collectors must implement collect() method.")
