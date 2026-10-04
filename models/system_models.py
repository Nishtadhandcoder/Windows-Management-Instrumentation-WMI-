"""
Data models for Windows Management Instrumentation (WMI) metrics collection.
Validated with Pydantic for high fidelity, structured storage in MongoDB, and API responses.
"""
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, ConfigDict


class AvailabilityInfo(BaseModel):
    """System availability and online reachability status."""
    model_config = ConfigDict(populate_by_name=True)

    up_down_status: str = Field(default="UP", description="System Up/Down Status ('UP' or 'DOWN')")
    status: str = Field(default="Online", description="Online reachability status ('Online' or 'Offline')")
    response_time_ms: Optional[float] = Field(default=None, description="Probe response latency in milliseconds")
    last_probe_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InstalledSoftwareItem(BaseModel):
    """Installed software application entry."""
    model_config = ConfigDict(populate_by_name=True)

    software_name: str = Field(..., description="Software Name")
    installation_date: Optional[str] = Field(default=None, description="Installation Date")
    vendor: Optional[str] = Field(default=None, description="Software Vendor / Publisher")
    version: Optional[str] = Field(default=None, description="Application Version")


class OperatingSystemInfo(BaseModel):
    """Detailed Windows operating system metrics."""
    model_config = ConfigDict(populate_by_name=True)

    local_date_and_time: str = Field(..., description="Local Date and Time on target machine")
    windows_directory: str = Field(..., description="Windows Directory path (e.g. C:\\Windows)")
    computer_name: str = Field(..., description="Computer Name / NetBIOS hostname")
    os_version: str = Field(..., description="OS Version build string")
    serial_number: str = Field(default="N/A", description="Windows Serial Number / Product ID")
    os_name: str = Field(..., description="Operating System Name / Caption")
    os_architecture: str = Field(default="64-bit", description="OS Architecture (32-bit or 64-bit)")
    system_type: Optional[str] = Field(default=None, description="Hardware System Type (e.g. x64-based PC)")
    registered_user: Optional[str] = Field(default=None, description="Registered User")
    boot_device: Optional[str] = Field(default=None, description="Boot Device path")
    last_boot_up_time: Optional[str] = Field(default=None, description="Last system boot timestamp")


class NetworkConfigurationItem(BaseModel):
    """Network adapter and IP configuration details."""
    model_config = ConfigDict(populate_by_name=True)

    network_interface: str = Field(..., description="Network Interface Caption or Name")
    network_interface_description: Optional[str] = Field(default=None, description="Interface Description")
    ipv4_address: Optional[str] = Field(default=None, description="Primary IPv4 Address")
    ipv4_subnet_mask: Optional[str] = Field(default=None, description="IPv4 Subnet Mask")
    domain: Optional[str] = Field(default="WORKGROUP", description="Domain or Workgroup name")
    mac_address: Optional[str] = Field(default=None, description="Physical MAC Address")
    dhcp_server: Optional[str] = Field(default=None, description="DHCP Server IP")
    ipv4_default_gateway: Optional[str] = Field(default=None, description="IPv4 Default Gateway")
    dhcp_enabled_status: str = Field(default="No", description="DHCP Enabled Status ('Yes' or 'No')")
    is_active: bool = Field(default=True, description="Whether the interface has an active IP configuration")


class ConfiguredServiceItem(BaseModel):
    """Windows system service configuration and runtime state."""
    model_config = ConfigDict(populate_by_name=True)

    service_name: str = Field(..., description="Service Name (identifier)")
    display_name: Optional[str] = Field(default=None, description="Service Display Name")
    service_status: str = Field(..., description="Service Status (e.g. Running, Stopped)")
    service_executable_path: Optional[str] = Field(default=None, description="Service Executable Binary Path")
    service_startup_mode: Optional[str] = Field(default=None, description="Service Startup Mode (Auto, Manual, Disabled)")


class DiskDetailItem(BaseModel):
    """Logical disk partition and storage details."""
    model_config = ConfigDict(populate_by_name=True)

    disk_id: str = Field(..., description="Disk ID or Volume Letter (e.g. '0' or 'C:')")
    volume_name: Optional[str] = Field(default=None, description="Volume Label")
    disk_size_mb: float = Field(..., description="Total Disk Size in Megabytes")
    free_disk_space_mb: float = Field(..., description="Free Disk Space in Megabytes")
    disk_used_space_percent: float = Field(..., description="Disk Used Space Percentage (0-100%)")
    file_system: str = Field(default="NTFS", description="File System format (NTFS, FAT32, etc.)")


class UserInfoItem(BaseModel):
    """Local or domain user account information."""
    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(default="", description="Full Name of the user")
    username_length: int = Field(..., description="Username Length in characters")
    account_status: str = Field(default="OK", description="Account Status (e.g. OK, Degraded)")
    local_account: str = Field(default="Yes", description="Local Account ('Yes' or 'No')")
    user_groups: List[str] = Field(default_factory=list, description="Associated user group memberships")
    account_disabled_status: str = Field(default="No", description="Account Disabled Status ('Yes' or 'No')")


class ProcessInformation(BaseModel):
    """Overall CPU and runtime process workload metrics."""
    model_config = ConfigDict(populate_by_name=True)

    cpu_usage_percent: float = Field(default=0.0, description="CPU Usage Percentage (0-100%)")
    memory_usage_percent: float = Field(default=0.0, description="Memory Usage Percentage (0-100%)")
    total_processes: int = Field(default=0, description="Total active processes count")


class SystemMemoryInfo(BaseModel):
    """Physical and virtual system memory statistics."""
    model_config = ConfigDict(populate_by_name=True)

    total_physical_memory_mb: float = Field(..., description="Total Physical RAM in MB")
    free_physical_memory_mb: float = Field(..., description="Free Physical RAM in MB")
    free_physical_memory_percent: float = Field(..., description="Free Physical RAM Percentage")
    free_physical_memory_kb: float = Field(..., description="Free Physical RAM in Kilobytes")
    total_virtual_memory_mb: float = Field(..., description="Total Virtual Memory in MB")
    free_virtual_memory_mb: float = Field(..., description="Free Virtual Memory in MB")
    free_virtual_memory_percent: float = Field(..., description="Free Virtual Memory Percentage")
    virtual_memory_size_kb: float = Field(..., description="Virtual Memory Size in Kilobytes")


class CompleteSystemSnapshot(BaseModel):
    """
    Comprehensive unified system snapshot capturing all 8 domains requested.
    This schema is stored in MongoDB and served via the REST API & Dashboard.
    """
    model_config = ConfigDict(populate_by_name=True)

    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique snapshot identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="UTC timestamp")
    machine_name: str = Field(default="Unknown", description="Target computer hostname")
    target_host: str = Field(default="localhost", description="Target IP or hostname probed")
    collection_duration_seconds: float = Field(default=0.0, description="Elapsed time to collect all metrics")

    # Domain models
    availability: AvailabilityInfo = Field(default_factory=AvailabilityInfo)
    os_info: OperatingSystemInfo
    user_info: List[UserInfoItem] = Field(default_factory=list)
    network_config: List[NetworkConfigurationItem] = Field(default_factory=list)
    disk_details: List[DiskDetailItem] = Field(default_factory=list)
    configured_services: List[ConfiguredServiceItem] = Field(default_factory=list)
    installed_software: List[InstalledSoftwareItem] = Field(default_factory=list)
    process_info: ProcessInformation = Field(default_factory=ProcessInformation)
    system_memory: SystemMemoryInfo

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational metadata and collector telemetry")

    def to_mongo_doc(self) -> Dict[str, Any]:
        """Convert pydantic model to MongoDB compliant BSON dictionary."""
        doc = self.model_dump(by_alias=True)
        # Use snapshot_id as MongoDB _id for primary key indexing
        doc["_id"] = self.snapshot_id
        return doc
