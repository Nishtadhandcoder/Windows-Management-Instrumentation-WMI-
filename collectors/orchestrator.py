"""
Orchestrator coordinating all domain-specific WMI collectors into a unified system snapshot.
"""
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from collectors.base_collector import WMIConnectionManager
from collectors.system_collector import SystemCollector
from collectors.hardware_collector import HardwareCollector
from collectors.disk_collector import DiskCollector
from collectors.network_collector import NetworkCollector
from collectors.service_collector import ServiceCollector
from collectors.software_collector import SoftwareCollector
from collectors.user_collector import UserCollector
from models.system_models import CompleteSystemSnapshot
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("collector.orchestrator")


class CollectorOrchestrator:
    """Coordinates execution across all WMI metric collectors and builds a CompleteSystemSnapshot."""

    def __init__(
        self,
        host: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or settings.wmi_host or "localhost"
        self.user = user if user is not None else settings.wmi_user
        self.password = password if password is not None else settings.wmi_password

    def collect_all(self) -> CompleteSystemSnapshot:
        """
        Executes all domain collectors in a thread-safe sequence and aggregates results
        into a validated CompleteSystemSnapshot.
        """
        start_time = time.perf_counter()
        logger.info(f"Starting comprehensive WMI system metrics collection for target '{self.host}'...")

        # Initialize shared thread-safe WMI COM connection
        wmi_conn = WMIConnectionManager.get_connection(
            host=self.host,
            user=self.user,
            password=self.password,
        )

        # Instantiate modular collectors
        system_col = SystemCollector(wmi_conn)
        hardware_col = HardwareCollector(wmi_conn)
        disk_col = DiskCollector(wmi_conn)
        network_col = NetworkCollector(wmi_conn)
        service_col = ServiceCollector(wmi_conn)
        software_col = SoftwareCollector(wmi_conn)
        user_col = UserCollector(wmi_conn)

        # 1. Operating System and Availability
        logger.debug("Collecting Operating System & Availability metrics...")
        os_info, availability = system_col.collect()

        # 2. Hardware, Process & System Memory
        logger.debug("Collecting Hardware, CPU, and Memory metrics...")
        process_info, system_memory = hardware_col.collect()

        # 3. Logical Disks
        logger.debug("Collecting Disk capacity and filesystem details...")
        disk_details = disk_col.collect()

        # 4. Network Configuration
        logger.debug("Collecting Network interface configurations...")
        network_config = network_col.collect()

        # 5. Configured Services
        logger.debug("Collecting Windows Services details...")
        configured_services = service_col.collect()

        # 6. Installed Software
        logger.debug("Collecting Installed Software applications...")
        installed_software = software_col.collect()

        # 7. User Accounts
        logger.debug("Collecting User Accounts and security groups...")
        user_info = user_col.collect()

        elapsed_seconds = round(time.perf_counter() - start_time, 2)
        logger.info(
            f"Successfully collected all system metrics in {elapsed_seconds}s. "
            f"Target: {os_info.computer_name}, Services: {len(configured_services)}, Software: {len(installed_software)}"
        )

        snapshot = CompleteSystemSnapshot(
            machine_name=os_info.computer_name,
            target_host=self.host,
            collection_duration_seconds=elapsed_seconds,
            availability=availability,
            os_info=os_info,
            user_info=user_info,
            network_config=network_config,
            disk_details=disk_details,
            configured_services=configured_services,
            installed_software=installed_software,
            process_info=process_info,
            system_memory=system_memory,
            metadata={
                "wmi_namespace": settings.wmi_namespace,
                "is_remote": settings.is_remote_wmi,
                "collector_version": "1.0.0",
            },
        )

        return snapshot

    @staticmethod
    def save_to_json(snapshot: CompleteSystemSnapshot, destination_path: Path) -> Path:
        """Saves a system snapshot locally in JSON format."""
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with open(destination_path, "w", encoding="utf-8") as f:
            f.write(snapshot.model_dump_json(indent=2))
        logger.info(f"Snapshot cached to JSON file: {destination_path}")
        return destination_path


# Backward compatibility alias
MetricsOrchestrator = CollectorOrchestrator

