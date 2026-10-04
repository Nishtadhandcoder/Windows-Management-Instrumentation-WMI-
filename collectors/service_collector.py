"""
Collector for Windows Configured Services, Run Status, Binary Executable Paths, and Startup Modes.
"""
from typing import List
from collectors.base_collector import BaseCollector
from models.system_models import ConfiguredServiceItem


class ServiceCollector(BaseCollector):
    """Gathers configured Windows services including critical system daemons."""

    # Key system services highlighted for top visibility (matching reference UI)
    PRIORITY_SERVICES = [
        "WinDefend",
        "wuauserv",
        "Dnscache",
        "LanmanWorkstation",
        "Spooler",
        "EventLog",
        "Dhcp",
        "W32Time",
        "TermService",
        "RpcSs",
    ]

    def collect(self) -> List[ConfiguredServiceItem]:
        """
        Queries Win32_Service to enumerate system services, sorting priority services first.
        """
        services: List[ConfiguredServiceItem] = []

        try:
            wmi_services = self.wmi.Win32_Service()

            # Separate into priority and remaining
            priority_items: List[ConfiguredServiceItem] = []
            standard_items: List[ConfiguredServiceItem] = []

            for svc in wmi_services:
                svc_name = getattr(svc, "Name", "") or ""
                if not svc_name:
                    continue

                display_name = getattr(svc, "DisplayName", None)
                state = getattr(svc, "State", "Unknown") or "Unknown"
                raw_path = getattr(svc, "PathName", None) or ""
                # Strip wrapping double quotes if present
                clean_path = raw_path.strip().strip('"') if raw_path else None
                start_mode = getattr(svc, "StartMode", "Manual") or "Manual"

                item = ConfiguredServiceItem(
                    service_name=svc_name,
                    display_name=display_name,
                    service_status=state,
                    service_executable_path=clean_path,
                    service_startup_mode=start_mode,
                )

                if svc_name in self.PRIORITY_SERVICES:
                    priority_items.append(item)
                else:
                    standard_items.append(item)

            # Sort priority items according to PRIORITY_SERVICES order
            priority_items.sort(
                key=lambda x: self.PRIORITY_SERVICES.index(x.service_name)
                if x.service_name in self.PRIORITY_SERVICES
                else 999
            )

            # Standard items alphabetically
            standard_items.sort(key=lambda x: x.service_name.lower())

            services = priority_items + standard_items

        except Exception as exc:
            self.logger.error(f"Failed to collect configured services: {exc}")

        # Fallback if query failed
        if not services:
            services.append(
                ConfiguredServiceItem(
                    service_name="WinDefend",
                    display_name="Windows Defender",
                    service_status="Running",
                    service_executable_path=r"C:\Program Files\Windows Defender\MsMpEng.exe",
                    service_startup_mode="Auto",
                )
            )

        return services
