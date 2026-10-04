"""
Collector for Storage Disks, Partition Capacities, Free Space, and File Systems.
"""
from typing import List
from collectors.base_collector import BaseCollector
from models.system_models import DiskDetailItem


class DiskCollector(BaseCollector):
    """Gathers storage disk capacity, utilization percentages, and filesystem formats."""

    def collect(self) -> List[DiskDetailItem]:
        """
        Queries Win32_LogicalDisk to retrieve local storage partitions.
        DriveType: 3 = Local Fixed Disk, 2 = Removable, 4 = Network Drive, 5 = Compact Disc.
        """
        disks: List[DiskDetailItem] = []

        try:
            # Query fixed logical disks with valid capacity
            logical_disks = self.wmi.Win32_LogicalDisk(DriveType=3)

            # If no fixed disks found (unlikely), query all disks
            if not logical_disks:
                logical_disks = self.wmi.Win32_LogicalDisk()

            for idx, disk in enumerate(logical_disks):
                raw_size = getattr(disk, "Size", None)
                if not raw_size:
                    continue

                size_bytes = float(raw_size)
                free_bytes = float(getattr(disk, "FreeSpace", 0) or 0)
                used_bytes = max(0.0, size_bytes - free_bytes)

                size_mb = self.bytes_to_mb(size_bytes)
                free_mb = self.bytes_to_mb(free_bytes)
                used_percent = round((used_bytes / size_bytes * 100), 1) if size_bytes > 0 else 0.0

                device_id = getattr(disk, "DeviceID", str(idx))
                # Normalize DiskID to integer string (like '0' in sample) or drive letter
                disk_id = str(idx) if getattr(disk, "Index", None) is None else str(disk.Index)

                item = DiskDetailItem(
                    disk_id=disk_id,
                    volume_name=getattr(disk, "VolumeName", None) or device_id,
                    disk_size_mb=size_mb,
                    free_disk_space_mb=free_mb,
                    disk_used_space_percent=used_percent,
                    file_system=getattr(disk, "FileSystem", "NTFS") or "NTFS",
                )
                disks.append(item)

        except Exception as exc:
            self.logger.error(f"Failed to collect disk details: {exc}")

        # If no disks could be enumerated, provide fallback
        if not disks:
            disks.append(
                DiskDetailItem(
                    disk_id="0",
                    volume_name="Local Disk",
                    disk_size_mb=0.0,
                    free_disk_space_mb=0.0,
                    disk_used_space_percent=0.0,
                    file_system="NTFS",
                )
            )

        return disks
