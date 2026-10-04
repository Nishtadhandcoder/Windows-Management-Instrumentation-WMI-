"""
Collector for Hardware metrics, CPU utilization, Process information, and System Memory statistics.
"""
from typing import Tuple
from collectors.base_collector import BaseCollector
from models.system_models import ProcessInformation, SystemMemoryInfo


class HardwareCollector(BaseCollector):
    """Gathers Processor load, active process counts, and physical & virtual RAM metrics."""

    def collect(self) -> Tuple[ProcessInformation, SystemMemoryInfo]:
        """
        Queries Win32_OperatingSystem and Win32_Processor to extract CPU and memory utilization.
        """
        try:
            # 1. CPU Usage via Win32_Processor
            processors = self.wmi.Win32_Processor()
            cpu_loads = [p.LoadPercentage for p in processors if getattr(p, "LoadPercentage", None) is not None]
            avg_cpu = round(float(sum(cpu_loads)) / len(cpu_loads), 1) if cpu_loads else 0.0

            # 2. Memory details via Win32_OperatingSystem
            os_records = self.wmi.Win32_OperatingSystem()
            os_item = os_records[0] if os_records else None

            if not os_item:
                raise ValueError("Win32_OperatingSystem returned no records for memory inspection.")

            total_phys_kb = float(getattr(os_item, "TotalVisibleMemorySize", 0) or 0)
            free_phys_kb = float(getattr(os_item, "FreePhysicalMemory", 0) or 0)
            total_virt_kb = float(getattr(os_item, "TotalVirtualMemorySize", 0) or 0)
            free_virt_kb = float(getattr(os_item, "FreeVirtualMemory", 0) or 0)
            num_processes = int(getattr(os_item, "NumberOfProcesses", 0) or 0)

            # Compute Physical Memory metrics
            total_phys_mb = round(total_phys_kb / 1024, 2)
            free_phys_mb = round(free_phys_kb / 1024, 2)
            free_phys_percent = round((free_phys_kb / total_phys_kb * 100), 1) if total_phys_kb > 0 else 0.0
            mem_usage_percent = round(100.0 - free_phys_percent, 1)

            # Compute Virtual Memory metrics
            total_virt_mb = round(total_virt_kb / 1024, 2)
            free_virt_mb = round(free_virt_kb / 1024, 2)
            free_virt_percent = round((free_virt_kb / total_virt_kb * 100), 1) if total_virt_kb > 0 else 0.0

            process_info = ProcessInformation(
                cpu_usage_percent=avg_cpu,
                memory_usage_percent=mem_usage_percent,
                total_processes=num_processes,
            )

            memory_info = SystemMemoryInfo(
                total_physical_memory_mb=total_phys_mb,
                free_physical_memory_mb=free_phys_mb,
                free_physical_memory_percent=free_phys_percent,
                free_physical_memory_kb=free_phys_kb,
                total_virtual_memory_mb=total_virt_mb,
                free_virtual_memory_mb=free_virt_mb,
                free_virtual_memory_percent=free_virt_percent,
                virtual_memory_size_kb=total_virt_kb,
            )

            return process_info, memory_info

        except Exception as exc:
            self.logger.error(f"Failed to collect hardware & memory metrics: {exc}")
            # Safe fallbacks
            fallback_proc = ProcessInformation(cpu_usage_percent=0.0, memory_usage_percent=0.0, total_processes=0)
            fallback_mem = SystemMemoryInfo(
                total_physical_memory_mb=0.0,
                free_physical_memory_mb=0.0,
                free_physical_memory_percent=0.0,
                free_physical_memory_kb=0.0,
                total_virtual_memory_mb=0.0,
                free_virtual_memory_mb=0.0,
                free_virtual_memory_percent=0.0,
                virtual_memory_size_kb=0.0,
            )
            return fallback_proc, fallback_mem
