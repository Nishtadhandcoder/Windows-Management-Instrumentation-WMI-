"""
Collector for Windows Operating System metrics and System Availability status.
"""
import time
from typing import Tuple
from datetime import datetime, timezone
from collectors.base_collector import BaseCollector
from models.system_models import OperatingSystemInfo, AvailabilityInfo


class SystemCollector(BaseCollector):
    """Retrieves OS metadata, ComputerSystem details, and reachability status."""

    def collect(self) -> Tuple[OperatingSystemInfo, AvailabilityInfo]:
        """
        Gathers OperatingSystemInfo and AvailabilityInfo via Win32_OperatingSystem and Win32_ComputerSystem.
        """
        start_time = time.perf_counter()
        availability = AvailabilityInfo()

        try:
            # Query Win32_OperatingSystem
            os_records = self.wmi.Win32_OperatingSystem()
            os_item = os_records[0] if os_records else None

            # Query Win32_ComputerSystem
            cs_records = self.wmi.Win32_ComputerSystem()
            cs_item = cs_records[0] if cs_records else None

            response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if not os_item:
                raise ValueError("Win32_OperatingSystem returned no records.")

            local_time_formatted = self.parse_wmi_datetime(getattr(os_item, "LocalDateTime", None))
            if not local_time_formatted:
                local_time_formatted = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

            boot_time_formatted = self.parse_wmi_datetime(getattr(os_item, "LastBootUpTime", None))

            system_info = OperatingSystemInfo(
                local_date_and_time=local_time_formatted,
                windows_directory=getattr(os_item, "WindowsDirectory", r"C:\Windows") or r"C:\Windows",
                computer_name=getattr(os_item, "CSName", None) or (getattr(cs_item, "Name", "UNKNOWN") if cs_item else "UNKNOWN"),
                os_version=getattr(os_item, "Version", "Unknown") or "Unknown",
                serial_number=getattr(os_item, "SerialNumber", "N/A") or "N/A",
                os_name=getattr(os_item, "Caption", "Microsoft Windows") or "Microsoft Windows",
                os_architecture=getattr(os_item, "OSArchitecture", "64-bit") or "64-bit",
                system_type=getattr(cs_item, "SystemType", "x64-based PC") if cs_item else "x64-based PC",
                registered_user=getattr(os_item, "RegisteredUser", "User") or "User",
                boot_device=getattr(os_item, "BootDevice", None),
                last_boot_up_time=boot_time_formatted,
            )

            availability.up_down_status = "UP"
            availability.status = "Online"
            availability.response_time_ms = response_time_ms
            availability.last_probe_time = datetime.now(timezone.utc).isoformat()

            return system_info, availability

        except Exception as exc:
            self.logger.error(f"Failed to collect Operating System details: {exc}")
            availability.up_down_status = "DOWN"
            availability.status = "Offline"
            availability.response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            availability.last_probe_time = datetime.now(timezone.utc).isoformat()

            # Return graceful fallback
            fallback_os = OperatingSystemInfo(
                local_date_and_time=datetime.now().strftime("%d-%m-%Y %I:%M:%S %p"),
                windows_directory=r"C:\Windows",
                computer_name="UNKNOWN",
                os_version="Unavailable",
                serial_number="N/A",
                os_name="Windows (Offline)",
                os_architecture="64-bit",
                system_type="Unknown",
                registered_user="N/A",
            )
            return fallback_os, availability
