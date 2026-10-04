"""
Unified Command-Line Interface (CLI) for Windows Management Instrumentation (WMI) System Monitor.
Provides subcommands to collect metrics, run the API/dashboard, execute the scheduler, and inspect health.
"""
import sys
import argparse
import json
import time
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger
from collectors.orchestrator import CollectorOrchestrator
from database.repository import snapshot_repository
from scheduler.runner import scheduler_service

logger = get_logger("cli.main")


def print_banner():
    banner = r"""
========================================================================
   __          ____  __ _____   _____           _                     
   \ \        / /  \/  |_   _| / ____|         | |                    
    \ \  /\  / /| \  / | | |  | (___  _   _ ___| |_ ___ _ __ ___      
     \ \/  \/ / | |\/| | | |   \___ \| | | / __| __/ _ \ '_ ` _ \     
      \  /\  /  | |  | |_| |_  ____) | |_| \__ \ ||  __/ | | | | |    
       \/  \/   |_|  |_|_____||_____/ \__, |___/\__\___|_| |_| |_|    
                                       __/ |                          
                                      |___/   WMI Enterprise Monitor  
========================================================================
"""
    print(banner)


def cmd_collect(args):
    """Executes on-demand WMI data collection from the terminal."""
    print(f"\n[*] Connecting to target host: '{args.host or settings.wmi_host}'...")
    orchestrator = CollectorOrchestrator(
        host=args.host,
        user=args.user,
        password=args.password,
    )

    start_time = time.perf_counter()
    snapshot = orchestrator.collect_all()
    duration = round(time.perf_counter() - start_time, 2)

    # Store snapshot in database & cache
    snap_id = snapshot_repository.save_snapshot(snapshot)

    # Print Formatted Results
    print("\n" + "=" * 70)
    print(f"  SYSTEM SNAPSHOT SUMMARY (ID: {snap_id})")
    print("=" * 70)
    print(f"  Machine Name      : {snapshot.machine_name}")
    print(f"  Availability      : {snapshot.availability.up_down_status} ({snapshot.availability.status})")
    print(f"  Operating System  : {snapshot.os_info.os_name} ({snapshot.os_info.os_architecture})")
    print(f"  OS Version Build  : {snapshot.os_info.os_version}")
    print(f"  Local Date & Time : {snapshot.os_info.local_date_and_time}")
    print(f"  CPU Usage         : {snapshot.process_info.cpu_usage_percent}%")
    print(f"  Memory Usage      : {snapshot.process_info.memory_usage_percent}% ({round(snapshot.system_memory.free_physical_memory_mb)} MB Free)")
    print(f"  Total Physical RAM: {round(snapshot.system_memory.total_physical_memory_mb)} MB")
    print(f"  Active Processes  : {snapshot.process_info.total_processes}")
    print(f"  Disks Detected    : {len(snapshot.disk_details)}")
    for d in snapshot.disk_details:
        print(f"    - Drive {d.disk_id} ({d.volume_name}): {d.disk_size_mb} MB ({d.disk_used_space_percent}% used, {d.file_system})")
    print(f"  Network Interfaces: {len(snapshot.network_config)}")
    for n in snapshot.network_config:
        if n.is_active:
            print(f"    - {n.network_interface}: IP={n.ipv4_address}, MAC={n.mac_address}, Gateway={n.ipv4_default_gateway}")
    print(f"  Services Audited  : {len(snapshot.configured_services)}")
    print(f"  Installed Apps    : {len(snapshot.installed_software)}")
    print(f"  User Accounts     : {len(snapshot.user_info)}")
    for u in snapshot.user_info:
        print(f"    - {u.username} ({u.full_name}): Groups={', '.join(u.user_groups)}, Disabled={u.account_disabled_status}")
    print(f"  Elapsed Time      : {duration} seconds")
    print("=" * 70)

    if args.output:
        out_path = Path(args.output)
        CollectorOrchestrator.save_to_json(snapshot, out_path)
        print(f"\n[+] Full snapshot exported to JSON file: {out_path.resolve()}")


def cmd_serve(args):
    """Starts the FastAPI web server and interactive enterprise dashboard."""
    import uvicorn

    host = args.host or settings.api_host
    port = args.port or settings.api_port

    print(f"\n[+] Launching WMI System Monitor Web Server...")
    print(f"[+] Web Dashboard URL : http://{host}:{port}/")
    print(f"[+] REST API Docs     : http://{host}:{port}/docs")
    print(f"[+] Press Ctrl+C to terminate the server.\n")

    uvicorn.run("api.app:app", host=host, port=port, reload=args.reload)


def cmd_schedule(args):
    """Runs the periodic collection daemon in the console."""
    interval = args.interval or settings.collection_interval_seconds
    scheduler_service.interval_seconds = interval

    print(f"\n[+] Starting periodic WMI collection scheduler (Interval: {interval} seconds)...")
    print(f"[+] Target Host : {settings.wmi_host}")
    print(f"[+] Database    : {settings.mongo_uri} (DB: {settings.mongo_db_name})")
    print(f"[+] Press Ctrl+C to stop scheduler.\n")

    scheduler_service.start()

    # Trigger first run immediately
    scheduler_service.trigger_now()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping scheduler daemon...")
        scheduler_service.stop()
        print("[+] Scheduler terminated safely.")


def cmd_status(args):
    """Inspects MongoDB connectivity, storage telemetry, and latest snapshot status."""
    print("\n[*] Inspecting System Health and Storage State...")
    health = snapshot_repository.get_health_status()
    latest = snapshot_repository.get_latest_snapshot()

    print("\n" + "=" * 65)
    print("  HEALTH & TELEMETRY DIAGNOSTICS")
    print("=" * 65)
    print(f"  Target Machine       : {settings.wmi_host} ({'Remote' if settings.is_remote_wmi else 'Local'})")
    print(f"  MongoDB Connection   : {'Connected' if health['mongodb']['connected'] else 'Offline Fallback'}")
    print(f"  MongoDB URI          : {health['mongodb']['uri']}")
    print(f"  Database / Collection: {health['mongodb']['database']} / {health['mongodb']['collection']}")
    if health['mongodb']['error']:
        print(f"  MongoDB Note         : {health['mongodb']['error']}")
    print(f"  Stored in MongoDB    : {health['storage']['mongodb_documents']} documents")
    print(f"  Local Cache Files    : {health['storage']['local_cache_files']} snapshots")
    print(f"  Local Cache Dir      : {health['storage']['cache_directory']}")

    if latest:
        print("\n  LATEST MONITORED SNAPSHOT:")
        print(f"    - Computer Hostname: {latest.machine_name}")
        print(f"    - Probe Timestamp  : {latest.timestamp}")
        print(f"    - System Status    : {latest.availability.status} ({latest.availability.up_down_status})")
        print(f"    - Operating System : {latest.os_info.os_name}")
    else:
        print("\n  No previous snapshots recorded yet. Run 'collect' to capture first state.")
    print("=" * 65 + "\n")


def cmd_export(args):
    """Exports the latest snapshot to a JSON file."""
    latest = snapshot_repository.get_latest_snapshot(machine_name=args.machine)
    if not latest:
        print("\n[-] Error: No snapshot found to export. Run 'collect' first.")
        sys.exit(1)

    out_file = Path(args.output or f"snapshot_{latest.machine_name}_{int(time.time())}.json")
    CollectorOrchestrator.save_to_json(latest, out_file)
    print(f"\n[+] Snapshot exported to: {out_file.resolve()}\n")


def main():
    """Main CLI entrypoint parser."""
    print_banner()

    parser = argparse.ArgumentParser(
        prog="wmi-monitor",
        description="Enterprise Windows Management Instrumentation (WMI) Telemetry & MongoDB Persistence Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Operational Subcommands")

    # 1. Collect
    p_collect = subparsers.add_parser("collect", help="Execute on-demand WMI system data collection")
    p_collect.add_argument("--host", help="Target Windows hostname or IP address (default: localhost)")
    p_collect.add_argument("--user", help="Administrative username (for remote targets)")
    p_collect.add_argument("--password", help="Administrative password (for remote targets)")
    p_collect.add_argument("-o", "--output", help="Optional path to export collected snapshot JSON")
    p_collect.set_defaults(func=cmd_collect)

    # 2. Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI web server and interactive dashboard")
    p_serve.add_argument("--host", default=settings.api_host, help=f"Binding host (default: {settings.api_host})")
    p_serve.add_argument("-p", "--port", type=int, default=settings.api_port, help=f"Binding port (default: {settings.api_port})")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    p_serve.set_defaults(func=cmd_serve)

    # 3. Schedule
    p_schedule = subparsers.add_parser("schedule", help="Run the periodic background collection daemon")
    p_schedule.add_argument("-i", "--interval", type=int, help=f"Interval in seconds (default: {settings.collection_interval_seconds}s)")
    p_schedule.set_defaults(func=cmd_schedule)

    # 4. Status
    p_status = subparsers.add_parser("status", help="Display health diagnostics and storage state")
    p_status.set_defaults(func=cmd_status)

    # 5. Export
    p_export = subparsers.add_parser("export", help="Export latest snapshot to JSON file")
    p_export.add_argument("-o", "--output", help="Output JSON filename")
    p_export.add_argument("-m", "--machine", help="Target machine filter")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
