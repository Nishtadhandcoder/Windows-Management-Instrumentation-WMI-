"""
Integration tests for WMI metric collectors and orchestrator.
"""
import unittest
from collectors.base_collector import BaseCollector, WMIConnectionManager
from collectors.system_collector import SystemCollector
from collectors.hardware_collector import HardwareCollector
from collectors.disk_collector import DiskCollector
from collectors.network_collector import NetworkCollector
from collectors.service_collector import ServiceCollector
from collectors.software_collector import SoftwareCollector
from collectors.user_collector import UserCollector
from collectors.orchestrator import CollectorOrchestrator


class TestWMICollectors(unittest.TestCase):
    """Verifies that collectors execute against local Windows WMI service."""

    @classmethod
    def setUpClass(cls):
        cls.wmi_conn = WMIConnectionManager.get_connection()

    def test_wmi_connection(self):
        self.assertIsNotNone(self.wmi_conn)

    def test_system_collector(self):
        col = SystemCollector(self.wmi_conn)
        os_info, avail = col.collect()
        self.assertTrue(len(os_info.computer_name) > 0)
        self.assertEqual(avail.status, "Online")

    def test_hardware_collector(self):
        col = HardwareCollector(self.wmi_conn)
        proc, mem = col.collect()
        self.assertTrue(mem.total_physical_memory_mb > 0)
        self.assertTrue(proc.total_processes > 0)

    def test_disk_collector(self):
        col = DiskCollector(self.wmi_conn)
        disks = col.collect()
        self.assertTrue(len(disks) > 0)
        self.assertTrue(disks[0].disk_size_mb > 0)

    def test_network_collector(self):
        col = NetworkCollector(self.wmi_conn)
        nets = col.collect()
        self.assertTrue(len(nets) > 0)

    def test_service_collector(self):
        col = ServiceCollector(self.wmi_conn)
        services = col.collect()
        self.assertTrue(len(services) > 0)

    def test_software_collector(self):
        col = SoftwareCollector(self.wmi_conn)
        apps = col.collect()
        self.assertTrue(len(apps) > 0)

    def test_user_collector(self):
        col = UserCollector(self.wmi_conn)
        users = col.collect()
        self.assertTrue(len(users) > 0)


if __name__ == "__main__":
    unittest.main()
