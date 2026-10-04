# Windows Management Instrumentation (WMI) Enterprise System Monitor

An enterprise-grade Python application that connects to Windows machines via **Windows Management Instrumentation (WMI)**, extracts comprehensive hardware, OS, network, and process telemetry, and stores the collected data in **MongoDB** for long-term audit and reporting.

Includes a **FastAPI REST API**, a **background scheduler**, and an **interactive Web Dashboard** mirroring the native Windows Fluent UI design.

---

## 📌 Architecture Overview

```mermaid
graph TD
    subgraph Target Windows Machine
        OS[Win32_OperatingSystem]
        CPU[Win32_Processor]
        Disk[Win32_LogicalDisk]
        Net[Win32_NetworkAdapterConfiguration]
        Svc[Win32_Service]
        Soft[Windows Registry & Packages]
        User[Win32_UserAccount / Groups]
    end

    subgraph Data Collection Engine
        BaseCol[BaseCollector (COM Thread-Safe)]
        Orch[CollectorOrchestrator]
        BaseCol --> OS
        BaseCol --> CPU
        BaseCol --> Disk
        BaseCol --> Net
        BaseCol --> Svc
        BaseCol --> Soft
        BaseCol --> User
        OS & CPU & Disk & Net & Svc & Soft & User --> Orch
    end

    subgraph Persistence Layer
        Model[Pydantic CompleteSystemSnapshot]
        Repo[SystemSnapshotRepository]
        MongoDB[(MongoDB Database)]
        Cache[Resilient Local JSON Cache]
        
        Orch --> Model
        Model --> Repo
        Repo -->|Primary Storage| MongoDB
        Repo -->|Offline Fallback| Cache
    end

    subgraph Interfaces & Automation
        API[FastAPI REST API]
        UI[Enterprise Web Dashboard]
        CLI[Unified CLI main.py]
        Sched[APScheduler Background Runner]

        Sched -->|Periodic Trigger| Orch
        CLI -->|On-Demand Probe| Orch
        API -->|Query State| Repo
        API -->|Trigger Probe| Orch
        UI <-->|Live Telemetry / Refresh| API
    end
```

---

## 📋 Data Domains Collected

The application audits **all 8 requested domains** with precision:

| Domain | Metrics & Fields Collected |
| :--- | :--- |
| **Availability** | System UP/Down Status, Reachability Status (`Online`/`Offline`), Probe Latency (ms) |
| **Installed Software** | Software Name, Installation Date, Publisher/Vendor, Version (Registry + OS packages) |
| **Operating System** | Local Date & Time, Windows Directory (`C:\Windows`), Computer Name, OS Version, Serial Number, OS Name, Architecture (`64-bit`/`32-bit`), System Type, Registered User |
| **User Information** | Username, Full Name, Username Character Length, Account Status, Local Account flag (`Yes`/`No`), Security Group Memberships (`Administrators`, `Users`), Account Disabled flag |
| **Network Configuration** | Network Interface Caption, Description, IPv4 Address, IPv4 Subnet Mask, Default Gateway, Domain/Workgroup, MAC Address, DHCP Server, DHCP Enabled Status |
| **Disk Details** | Disk ID/Drive Letter, Volume Label, Total Disk Size (MB), Free Disk Space (MB), Used Space (%), File System (`NTFS`/`FAT32`) |
| **Process Information** | CPU Usage (%), System Memory Usage (%), Total Active Processes count |
| **System Memory** | Total Physical Memory (MB), Free Physical Memory (MB & %), Free Physical Memory (KB), Total Virtual Memory (MB), Free Virtual Memory (MB & %), Virtual Memory Size (KB) |
| **Configured Services** | Service Name, Display Name, Service Status (`Running`/`Stopped`), Executable Binary Path, Startup Mode (`Auto`/`Manual`/`Disabled`) |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Operating System**: Windows 10/11 or Windows Server (local or remote)
- **Python**: Python 3.9+ (Fully validated on Python 3.14)
- **MongoDB**: Optional local or cloud cluster (includes zero-crash offline local disk fallback)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/Nishtadhandcoder/Windows-Management-Instrumentation-WMI-.git
cd Windows-Management-Instrumentation-WMI-

# Install required dependencies
python -m pip install -r requirements.txt
```

### 3. Configuration (`.env`)
Configure your target machine, credentials, MongoDB URI, and scheduler interval:
```ini
# Target machine ('localhost' for current machine, or remote hostname/IP)
WMI_HOST=localhost
WMI_USER=
WMI_PASSWORD=
WMI_NAMESPACE=root\cimv2

# MongoDB Database Connection
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=wmi_system_monitor
MONGO_COLLECTION_NAME=system_snapshots
MONGO_TIMEOUT_MS=5000

# Scheduler & API Settings
COLLECTION_INTERVAL_SECONDS=60
SCHEDULER_ENABLED=true
API_HOST=127.0.0.1
API_PORT=8000
```

---

## 🖥️ Command-Line Interface (CLI) Usage

The application includes a unified CLI (`main.py`):

### 1. Launch Interactive Dashboard & REST API
```powershell
python main.py serve --port 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your web browser.

### 2. Execute On-Demand WMI Collection
```powershell
python main.py collect
```
*Supports optional remote target flags: `--host 192.168.1.100 --user Admin --password Pass --output snapshot.json`*

### 3. Run Periodic Scheduler in Background
```powershell
python main.py schedule --interval 60
```

### 4. Check Health & MongoDB Diagnostics
```powershell
python main.py status
```

### 5. Export Latest Snapshot to File
```powershell
python main.py export -o export_latest.json
```

---

## 🌐 REST API Endpoints

FastAPI documentation is automatically available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

| HTTP Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive Fluent Web Dashboard |
| `GET` | `/api/snapshots/latest` | Retrieves the latest system snapshot from MongoDB or cache |
| `GET` | `/api/snapshots/history` | Returns historical snapshot list (`limit=50`, `machine_name=...`) |
| `POST` | `/api/collect` | Triggers an immediate live WMI collection run and updates MongoDB |
| `GET` | `/api/health` | Telemetry health check (MongoDB connectivity, cache counts, scheduler) |
| `GET` | `/api/machines` | Returns distinct monitored machine hostnames |
| `GET` | `/api/scheduler` | Inspects scheduler running state and next scheduled probe time |
| `POST` | `/api/scheduler/toggle` | Enables (`enable=true`) or disables (`enable=false`) background collection |

---

## 🗄️ MongoDB Schema & Resilient Offline Fallback

Snapshots are stored in MongoDB as structured BSON documents under the `system_snapshots` collection.

### Document Indexing
The repository automatically provisions optimal compound indexes upon connection:
- `timestamp: -1`
- `machine_name: 1, timestamp: -1`
- `availability.status: 1`

### Operational Resilience Mode
If MongoDB is temporarily unavailable or starting up:
1. The application **will not crash**.
2. It logs a warning and engages **operational resilience mode**.
3. All snapshots are written locally to `data/snapshots/{machine_name}_{timestamp}.json`.
4. API endpoints seamlessly serve from the local disk cache until MongoDB reconnects.

---

## 🧪 Automated Test Suite

Run the complete unit and integration test suite:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Verified test coverage:
- `test_availability_model`: Validates availability and latency calculation.
- `test_operating_system_model`: Validates 32/64-bit architecture and OS strings.
- `test_complete_snapshot_serialization`: Validates MongoDB BSON serialization.
- `test_wmi_connection`: Validates COM thread initialization.
- `test_system_collector`: Probes local Win32_OperatingSystem.
- `test_hardware_collector`: Probes processor load and RAM calculation.
- `test_disk_collector`: Validates partition sizes and NTFS filesystems.
- `test_network_collector`: Audits IPv4, subnet mask, and MAC address.
- `test_service_collector`: Audits 300+ Windows services.
- `test_software_collector`: Audits registry packages and publisher data.
- `test_user_collector`: Audits local accounts and group memberships.

---

## 💼 Company Presentation Talking Points

When presenting this application in your company or interview, highlight these key design achievements:

1. **Enterprise Modularity**: Clean separation of concerns between Collectors, Database Persistence, Models, Scheduler, REST API, and Frontend.
2. **COM Multi-Threading Safety**: Unlike naive WMI scripts that crash with `CoInitialize` errors in multi-threaded servers, this solution handles COM thread initialization cleanly on every background worker.
3. **High-Performance Software Enumeration**: Leverages Windows Registry inspection instead of slow `Win32_Product` WMI queries, resulting in sub-second software discovery without triggering MSI re-installation warnings.
4. **Resilience & Fault-Tolerance**: Zero downtime architecture with local file snapshot mirroring if MongoDB is offline.
5. **Faithful UI Implementation**: Delivered an interface matching the exact Windows Machine Details design layout, complete with live progress bars, status pills, and interactive filtering.
