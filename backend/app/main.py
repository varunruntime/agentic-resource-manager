import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import Base, engine, SessionLocal
from app.models.entities import *
from app.api.routes import router, seed_db
from app.agents.monitoring import MonitoringAgent
from app.services.runtime import (
    next_workload_load,
    stop_workload_simulation,
)

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

_telemetry_task: asyncio.Task | None = None


def _capacity_multiplier(metric):
    if metric is None:
        return 1.0
    return float(metric.estimated_cost) / max(0.10 * int(metric.instances), 1e-9)


async def _workload_telemetry_loop():
    """Advance active workload traces and persist shared resource observations."""
    monitor = MonitoringAgent()
    while True:
        db = SessionLocal()
        try:
            active = db.query(Workload).filter(Workload.active.is_(True)).all()
            if active:
                latest = db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
                instances = max(1, int(latest.instances)) if latest else 2
                capacity_multiplier = _capacity_multiplier(latest)
                loads = []

                for workload in active:
                    load = next_workload_load(workload)
                    if load is None:
                        workload.active = False
                        workload.current_load = 0
                        continue
                    workload.current_load = load
                    loads.append(load)

                active_count = len(loads)
                aggregate_load = min(100.0, sum(loads)) if loads else 0.0
                snapshot = monitor.observe_simulated(
                    aggregate_load,
                    instances=instances,
                    active_workloads=active_count,
                    seed=int(datetime.utcnow().timestamp() * 1000) % (2**31 - 1),
                    cpu_capacity_multiplier=capacity_multiplier,
                )
                cpu = float(snapshot["cpu_percent"])
                latency = max(20.0, 45.0 + 1.35 * cpu)
                cost = 0.10 * instances * capacity_multiplier
                energy = 0.18 * instances * capacity_multiplier
                db.add(ResourceMetric(
                    cpu_percent=cpu,
                    memory_percent=float(snapshot["memory_percent"]),
                    disk_percent=float(snapshot["disk_percent"]),
                    network_usage=float(snapshot["network_usage"]),
                    active_workloads=active_count,
                    instances=instances,
                    latency_ms=latency,
                    estimated_cost=cost,
                    estimated_energy=energy,
                ))
                db.commit()
            else:
                # When the final workload is stopped manually, publish one
                # idle sample so dashboards do not retain stale load counts.
                latest = db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
                if latest is not None and int(latest.active_workloads) > 0:
                    instances = max(1, int(latest.instances))
                    capacity_multiplier = _capacity_multiplier(latest)
                    snapshot = monitor.observe_simulated(
                        0,
                        instances=instances,
                        active_workloads=0,
                        seed=int(datetime.utcnow().timestamp() * 1000) % (2**31 - 1),
                        cpu_capacity_multiplier=capacity_multiplier,
                    )
                    db.add(ResourceMetric(
                        cpu_percent=float(snapshot["cpu_percent"]),
                        memory_percent=float(snapshot["memory_percent"]),
                        disk_percent=float(snapshot["disk_percent"]),
                        network_usage=0.0,
                        active_workloads=0,
                        instances=instances,
                        latency_ms=45.0,
                        estimated_cost=0.10 * instances * capacity_multiplier,
                        estimated_energy=0.18 * instances * capacity_multiplier,
                    ))
                    db.commit()
        except asyncio.CancelledError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("Workload telemetry update failed")
        finally:
            db.close()

        await asyncio.sleep(2)


@app.on_event("startup")
async def startup():
    global _telemetry_task
    db = SessionLocal()
    try:
        seed_db(db)
        # Rebuild process-local simulation cursors when the API restarts.
        for workload in db.query(Workload).filter(Workload.active.is_(True)).all():
            from app.services.runtime import start_workload_simulation
            start_workload_simulation(workload)
    finally:
        db.close()
    _telemetry_task = asyncio.create_task(_workload_telemetry_loop())


@app.on_event("shutdown")
async def shutdown():
    global _telemetry_task
    if _telemetry_task is not None:
        _telemetry_task.cancel()
        try:
            await _telemetry_task
        except asyncio.CancelledError:
            pass
        _telemetry_task = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "simulation_mode": settings.simulation_mode,
        "telemetry": "active",
        "reasoning_provider": "rule_based",
    }


@app.websocket("/ws/metrics")
async def metrics_socket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                metric = db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
                if metric:
                    await ws.send_json({
                        "timestamp": metric.timestamp.isoformat(),
                        "cpu_percent": float(metric.cpu_percent),
                        "memory_percent": float(metric.memory_percent),
                        "disk_percent": float(metric.disk_percent),
                        "network_usage": float(metric.network_usage),
                        "active_workloads": int(metric.active_workloads),
                        "instances": int(metric.instances),
                        "latency_ms": float(metric.latency_ms),
                        "estimated_cost": float(metric.estimated_cost),
                        "estimated_energy": float(metric.estimated_energy),
                        "cpu_capacity_multiplier": _capacity_multiplier(metric),
                    })
            finally:
                db.close()
            await asyncio.sleep(2)
    except Exception:
        # A disconnected browser closes the socket; do not affect the telemetry loop.
        return
