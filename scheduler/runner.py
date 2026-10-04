"""
Periodic background task runner and scheduler for automated WMI data collection.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import pythoncom
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config.settings import settings
from config.logging_config import get_logger
from collectors.orchestrator import CollectorOrchestrator
from database.repository import snapshot_repository
from models.system_models import CompleteSystemSnapshot

logger = get_logger("scheduler.runner")


class SchedulerService:
    """Manages periodic execution of WMI data collection using APScheduler."""

    def __init__(self, interval_seconds: Optional[int] = None):
        self.interval_seconds = interval_seconds or settings.collection_interval_seconds
        self.scheduler = BackgroundScheduler(daemon=True)
        self.job_id = "periodic_wmi_collection_job"
        self._last_snapshot: Optional[CompleteSystemSnapshot] = None
        self._last_run_time: Optional[str] = None
        self._last_error: Optional[str] = None
        self._is_collecting: bool = False

    def _execute_collection_job(self) -> Optional[CompleteSystemSnapshot]:
        """
        Target function executed periodically by APScheduler.
        Safely manages Windows COM runtime per background worker thread.
        """
        if self._is_collecting:
            logger.warning("Previous collection job is still in progress. Skipping overlapping interval.")
            return None

        self._is_collecting = True
        pythoncom.CoInitialize()
        try:
            logger.info("Executing scheduled periodic WMI system metrics collection...")
            orchestrator = CollectorOrchestrator()
            snapshot = orchestrator.collect_all()

            # Persist to database & cache
            snap_id = snapshot_repository.save_snapshot(snapshot)

            self._last_snapshot = snapshot
            self._last_run_time = datetime.now(timezone.utc).isoformat()
            self._last_error = None
            logger.info(
                f"Scheduled collection job completed successfully (ID: {snap_id}, Machine: {snapshot.machine_name})."
            )
            return snapshot

        except Exception as exc:
            self._last_error = f"Scheduled collection job encountered an error: {exc}"
            logger.error(self._last_error, exc_info=True)
            return None

        finally:
            pythoncom.CoUninitialize()
            self._is_collecting = False

    def start(self) -> bool:
        """Starts the periodic background scheduler daemon."""
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled in settings (SCHEDULER_ENABLED=false).")
            return False

        if self.scheduler.running:
            logger.warning("Scheduler daemon is already running.")
            return True

        try:
            self.scheduler.add_job(
                func=self._execute_collection_job,
                trigger=IntervalTrigger(seconds=self.interval_seconds),
                id=self.job_id,
                name="Periodic Windows WMI System Metrics Collection",
                replace_existing=True,
                max_instances=1,
            )
            self.scheduler.start()
            logger.info(f"Scheduler daemon started. Interval: {self.interval_seconds}s.")
            return True
        except Exception as exc:
            logger.error(f"Failed to start scheduler daemon: {exc}")
            return False

    def stop(self) -> None:
        """Stops the periodic scheduler daemon gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler daemon stopped.")

    def trigger_now(self) -> Optional[CompleteSystemSnapshot]:
        """Triggers an immediate collection run on-demand (bypassing the timer)."""
        logger.info("Triggering on-demand immediate WMI metrics collection...")
        return self._execute_collection_job()

    def get_status(self) -> Dict[str, Any]:
        """Returns the operational status, interval, next run time, and last execution info."""
        job = self.scheduler.get_job(self.job_id) if self.scheduler.running else None
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None

        return {
            "running": self.scheduler.running,
            "interval_seconds": self.interval_seconds,
            "job_id": self.job_id,
            "next_run_time": next_run,
            "last_run_time": self._last_run_time,
            "is_currently_collecting": self._is_collecting,
            "last_error": self._last_error,
            "has_latest_snapshot": self._last_snapshot is not None,
        }


# Global singleton scheduler service
scheduler_service = SchedulerService()
