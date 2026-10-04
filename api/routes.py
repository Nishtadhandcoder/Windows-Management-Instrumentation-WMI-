"""
FastAPI REST API routes for WMI system data querying, live collection, and health checks.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from database.repository import snapshot_repository
from collectors.orchestrator import CollectorOrchestrator
from scheduler.runner import scheduler_service
from models.system_models import CompleteSystemSnapshot
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("api.routes")
router = APIRouter(prefix="/api", tags=["WMI System Monitoring"])


class CollectRequest(BaseModel):
    """Optional payload to trigger collection on a specific machine."""
    host: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None


@router.get("/health", summary="System Health and Database Connectivity")
def get_health() -> Dict[str, Any]:
    """Returns database connection status, storage counts, scheduler state, and configuration."""
    health_data = snapshot_repository.get_health_status()
    scheduler_data = scheduler_service.get_status()

    return {
        "status": "healthy" if health_data["mongodb"]["connected"] else "degraded_offline_fallback",
        "target_machine": settings.wmi_host,
        "is_remote": settings.is_remote_wmi,
        "database": health_data["mongodb"],
        "storage": health_data["storage"],
        "scheduler": scheduler_data,
    }


@router.get("/snapshots/latest", response_model=CompleteSystemSnapshot, summary="Get Latest System Snapshot")
def get_latest_snapshot(
    machine_name: Optional[str] = Query(None, description="Optional target computer name")
) -> CompleteSystemSnapshot:
    """Retrieves the most recent system metrics snapshot."""
    snapshot = snapshot_repository.get_latest_snapshot(machine_name=machine_name)
    if not snapshot:
        # If no snapshot exists yet, trigger an immediate one
        logger.info("No prior snapshot found in database/cache. Triggering initial collection...")
        orchestrator = CollectorOrchestrator()
        snapshot = orchestrator.collect_all()
        snapshot_repository.save_snapshot(snapshot)

    return snapshot


@router.get("/snapshots/history", response_model=List[CompleteSystemSnapshot], summary="Get Snapshot History")
def get_snapshot_history(
    machine_name: Optional[str] = Query(None, description="Optional target computer name"),
    limit: int = Query(20, ge=1, le=100, description="Maximum historical snapshots to return"),
) -> List[CompleteSystemSnapshot]:
    """Retrieves historical system snapshots for trend analysis and audit logs."""
    history = snapshot_repository.get_snapshot_history(machine_name=machine_name, limit=limit)
    return history


@router.post("/collect", response_model=CompleteSystemSnapshot, summary="Trigger Live WMI Data Collection")
def trigger_live_collection(
    request: Optional[CollectRequest] = None
) -> CompleteSystemSnapshot:
    """
    Triggers an immediate WMI probe against the local or remote target Windows host,
    persists the results to MongoDB and local cache, and returns the snapshot.
    """
    target_host = request.host if request and request.host else None
    target_user = request.user if request and request.user else None
    target_password = request.password if request and request.password else None

    logger.info(f"API request received to collect system metrics (host: {target_host or 'default'}).")

    try:
        orchestrator = CollectorOrchestrator(
            host=target_host,
            user=target_user,
            password=target_password,
        )
        snapshot = orchestrator.collect_all()
        snapshot_repository.save_snapshot(snapshot)
        return snapshot
    except Exception as exc:
        logger.error(f"Live collection failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"WMI collection failed: {str(exc)}")


@router.get("/machines", response_model=List[str], summary="List Monitored Machines")
def list_machines() -> List[str]:
    """Returns a list of all distinct machine names discovered in the database/cache."""
    return snapshot_repository.get_all_machines()


@router.get("/scheduler", summary="Get Scheduler Status")
def get_scheduler_status() -> Dict[str, Any]:
    """Returns current scheduler state, interval, next run time, and last error."""
    return scheduler_service.get_status()


@router.post("/scheduler/toggle", summary="Toggle Scheduler Running State")
def toggle_scheduler(enable: bool = Query(..., description="True to start, False to stop")) -> Dict[str, Any]:
    """Starts or stops the background periodic collection daemon."""
    if enable:
        started = scheduler_service.start()
        return {"action": "start", "success": started, "status": scheduler_service.get_status()}
    else:
        scheduler_service.stop()
        return {"action": "stop", "success": True, "status": scheduler_service.get_status()}
