"""
Unit tests for Pydantic data models and serialization integrity.
"""
import unittest
from datetime import datetime, timezone
from models.system_models import (
    AvailabilityInfo,
    InstalledSoftwareItem,
    OperatingSystemInfo,
    NetworkConfigurationItem,
    ConfiguredServiceItem,
    DiskDetailItem,
    UserInfoItem,
    ProcessInformation,
    SystemMemoryInfo,
    CompleteSystemSnapshot,
)


class TestSystemModels(unittest.TestCase):
    """Tests schema validation and BSON document conversion."""

    def test_availability_model(self):
        item = AvailabilityInfo(up_down_status="UP", status="Online", response_time_ms=12.5)
        self.assertEqual(item.up_down_status, "UP")
        self.assertEqual(item.status, "Online")
        self.assertAlmostEqual(item.response_time_ms, 12.5)

    def test_operating_system_model(self):
        os_info = OperatingSystemInfo(
            local_date_and_time="25-06-2025 10:30:45 AM",
            windows_directory=r"C:\Windows",
            computer_name="DESKTOP-7F3G9K2",
            os_version="10.0.22631",
            serial_number="00330-80000-00000-AA123",
            os_name="Microsoft Windows 11 Pro",
            os_architecture="64-bit",
            system_type="x64-based PC",
            registered_user="User",
        )
        self.assertEqual(os_info.computer_name, "DESKTOP-7F3G9K2")
        self.assertEqual(os_info.os_architecture, "64-bit")

    def test_complete_snapshot_serialization(self):
        snapshot = CompleteSystemSnapshot(
            machine_name="TEST-PC",
            target_host="localhost",
            collection_duration_seconds=1.2,
            availability=AvailabilityInfo(),
            os_info=OperatingSystemInfo(
                local_date_and_time="25-06-2025 10:30:45 AM",
                windows_directory=r"C:\Windows",
                computer_name="TEST-PC",
                os_version="10.0",
                serial_number="12345",
                os_name="Windows 11",
                os_architecture="64-bit",
            ),
            disk_details=[
                DiskDetailItem(
                    disk_id="0",
                    volume_name="OS",
                    disk_size_mb=512000.0,
                    free_disk_space_mb=256000.0,
                    disk_used_space_percent=50.0,
                    file_system="NTFS",
                )
            ],
            system_memory=SystemMemoryInfo(
                total_physical_memory_mb=16384.0,
                free_physical_memory_mb=8192.0,
                free_physical_memory_percent=50.0,
                free_physical_memory_kb=8388608.0,
                total_virtual_memory_mb=20480.0,
                free_virtual_memory_mb=10240.0,
                free_virtual_memory_percent=50.0,
                virtual_memory_size_kb=20971520.0,
            ),
        )

        doc = snapshot.to_mongo_doc()
        self.assertIn("_id", doc)
        self.assertEqual(doc["_id"], snapshot.snapshot_id)
        self.assertEqual(doc["machine_name"], "TEST-PC")
        self.assertEqual(len(doc["disk_details"]), 1)


if __name__ == "__main__":
    unittest.main()
