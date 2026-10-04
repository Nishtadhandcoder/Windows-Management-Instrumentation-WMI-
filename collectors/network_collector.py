"""
Collector for Network Interfaces, IPv4 Configuration, Subnet Masks, Gateways, DHCP, and MAC Addresses.
"""
import re
from typing import List, Optional
from collectors.base_collector import BaseCollector
from models.system_models import NetworkConfigurationItem


class NetworkCollector(BaseCollector):
    """Gathers network adapter configurations for all active network interfaces."""

    def _extract_ipv4(self, ip_list: Optional[List[str]]) -> Optional[str]:
        """Extracts the first valid IPv4 address from a list of IP addresses."""
        if not ip_list:
            return None
        ipv4_regex = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        for ip in ip_list:
            if ip and ipv4_regex.match(ip.strip()) and not ip.startswith("127."):
                return ip.strip()
        return None

    def collect(self) -> List[NetworkConfigurationItem]:
        """
        Queries Win32_NetworkAdapterConfiguration for active network interfaces (IPEnabled=True).
        """
        interfaces: List[NetworkConfigurationItem] = []

        try:
            # Query domain name from Win32_ComputerSystem as reliable fallback
            system_domain = "WORKGROUP"
            try:
                cs_records = self.wmi.Win32_ComputerSystem()
                if cs_records and getattr(cs_records[0], "Domain", None):
                    system_domain = cs_records[0].Domain
            except Exception:
                pass

            # Query adapter configurations where IP is enabled
            adapters = self.wmi.Win32_NetworkAdapterConfiguration(IPEnabled=True)

            # If no IP enabled adapters found, fallback to all adapters
            if not adapters:
                adapters = self.wmi.Win32_NetworkAdapterConfiguration()

            for adapter in adapters:
                description = getattr(adapter, "Description", "") or ""
                caption = getattr(adapter, "Caption", "") or description

                # Clean up caption (often has bracket prefix like '[00000001] Intel...')
                clean_name = re.sub(r"^\[\d+\]\s*", "", caption).strip() or description

                raw_ips = getattr(adapter, "IPAddress", None) or []
                raw_subnets = getattr(adapter, "IPSubnet", None) or []
                raw_gateways = getattr(adapter, "DefaultIPGateway", None) or []

                ipv4 = self._extract_ipv4(raw_ips)
                subnet = raw_subnets[0] if raw_subnets else None
                gateway = raw_gateways[0] if raw_gateways else None

                dhcp_enabled = bool(getattr(adapter, "DHCPEnabled", False))
                dhcp_server = getattr(adapter, "DHCPServer", None)
                mac_address = getattr(adapter, "MACAddress", None)
                adapter_domain = getattr(adapter, "DNSDomain", None) or system_domain

                # Format MAC address with hyphens if present
                if mac_address and ":" in mac_address:
                    mac_address = mac_address.replace(":", "-")

                item = NetworkConfigurationItem(
                    network_interface=clean_name,
                    network_interface_description=description,
                    ipv4_address=ipv4,
                    ipv4_subnet_mask=subnet,
                    domain=adapter_domain,
                    mac_address=mac_address,
                    dhcp_server=dhcp_server,
                    ipv4_default_gateway=gateway,
                    dhcp_enabled_status="Yes" if dhcp_enabled else "No",
                    is_active=bool(ipv4),
                )
                interfaces.append(item)

        except Exception as exc:
            self.logger.error(f"Failed to collect network configuration: {exc}")

        # Fallback if list is empty
        if not interfaces:
            interfaces.append(
                NetworkConfigurationItem(
                    network_interface="Ethernet",
                    network_interface_description="Local Area Connection",
                    ipv4_address="127.0.0.1",
                    ipv4_subnet_mask="255.255.255.0",
                    domain="WORKGROUP",
                    dhcp_enabled_status="No",
                    is_active=False,
                )
            )

        return interfaces
