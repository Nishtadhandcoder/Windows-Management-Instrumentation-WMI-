"""
Pydantic data models for WMI system data collection and MongoDB storage.
"""
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

__all__ = [
    "AvailabilityInfo",
    "InstalledSoftwareItem",
    "OperatingSystemInfo",
    "NetworkConfigurationItem",
    "ConfiguredServiceItem",
    "DiskDetailItem",
    "UserInfoItem",
    "ProcessInformation",
    "SystemMemoryInfo",
    "CompleteSystemSnapshot",
]
