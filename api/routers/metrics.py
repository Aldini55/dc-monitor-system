import telegram
import os
import json
import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
from database import get_db
from models import Server, Metric, Alert, AlertSeverity, AlertStatus
from datetime import datetime, timedelta
from schemas import MetricCreate, MetricOut, MetricSummary

cache = redis.from_url(os.environ.get("REDIS_URL","redis://redis:6379"))

router = APIRouter(prefix="/servers/{server_id}/metrics", tags=["Metrics"])

# Extension 1: Mexican Standard Thresholds (NOM / ASHRAE)
THRESHOLDS = {
    "cpu_usage":    {"warning": 70.0, "critical": 90.0},
    "memory_usage": {"warning": 75.0, "critical": 92.0},
    "disk_usage":   {"warning": 25.0, "critical": 27.0},
    "temperature":  {"warning": 35.0, "critical": 20.0},
}


def _auto_generate_alerts(db: Session, server: Server, metric: Metric):
    checks = {
        "cpu_usage": metric.cpu_usage,
        "memory_usage": metric.memory_usage,
        "disk_usage": metric.disk_usage,
        "temperature": metric.temperature,
    }

    for metric_name, value in checks.items():
        limits = THRESHOLDS[metric_name]
        severity = None
        threshold = None

        if value >= limits["critical"]:
            severity = AlertSeverity.critical
            threshold = limits["critical"]
        elif value >= limits["warning"]:
            severity = AlertSeverity.warning
            threshold = limits["warning"]

        if severity:
            existing = (
                db.query(Alert)
                .filter(
                    Alert.server_id == server.id,
                    Alert.metric == metric_name,
                    Alert.status == AlertStatus.open,
                )
                .first()
            )
            if not existing:
                alert = Alert(
                    server_id=server.id,
                    severity=severity,
                    metric=metric_name,
                    message=(
                        f"{server.hostname}: {metric_name.replace('_', ' ').title()} "
                        f"is {value:.1f} (threshold: {threshold})"
                    ),
                    value=value,
                    threshold=threshold,
                )
                db.add(alert)
                # Send Telegram notification for critical alerts only
                if severity == AlertSeverity.critical:
                    telegram.send_alert(
                        severity=severity.value,
                        hostname=server.hostname,
                        metric=metric_name,
                        value=value,
                        threshold=threshold,
                    )
            
        else:
            # El valor volvió a la normalidad — resolver cualquier alerta abierta
            open_alert = (
                db.query(Alert)
                .filter(
                    Alert.server_id == server.id,
                    Alert.metric == metric_name,
                    Alert.status == AlertStatus.open,
                )
                .first()
            )
            
            if open_alert:
                open_alert.status = AlertStatus.resolved
                open_alert.resolved_at = datetime.utcnow()
                print(
                    f"[auto-resolve] {server.hostname}: {metric_name} "
                    f"back to normal ({value:.1f}). Alert #{open_alert.id} resolved."
                )


@router.post("/", response_model=MetricOut, status_code=201,
             summary="Record a new metric snapshot")
def record_metric(
    server_id: int,
    payload: MetricCreate,
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    metric = Metric(server_id=server_id, **payload.model_dump())
    db.add(metric)
    db.flush()

    _auto_generate_alerts(db, server, metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/", response_model=List[MetricOut], summary="List metrics for a server")
def list_metrics(
    server_id: int,
    hours: int = Query(default=1, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Return recent metric snapshots for a server.
    - **hours**: how many hours back to look (1-168)
    - **limit**: max number of records per page
    - **offset**: number of records to skip
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    since = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = (
        db.query(Metric)
        .filter(
            Metric.server_id == server_id,
            Metric.recorded_at >= since
        )
        .order_by(Metric.recorded_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return metrics

@router.get("/latest", response_model=MetricOut, summary="Get latest metric snapshot")
def latest_metric(server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    metric = (
        db.query(Metric)
        .filter(Metric.server_id == server_id)
        .order_by(Metric.recorded_at.desc())
        .first()
    )
    if not metric:
        raise HTTPException(status_code=404, detail="No metrics recorded yet.")
    return metric


@router.get("/summary", response_model=MetricSummary, summary="Aggregated stats")
def metric_summary(
    server_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Return averaged and peak metrics for the specified time window.
    Results are cached in Redis for 60 seconds to reduce database load.
    """
    cache_key = f"summary:{server_id}:{hours}"

    # Intentar retornar el resultado desde caché primero
    try:
        cached = cache.get(cache_key)
        if cached:
            return MetricSummary(**json.loads(cached))
    except Exception:
        pass  # Si Redis no está disponible, seguimos con la base de datos

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    since = datetime.utcnow() - timedelta(hours=hours)

    result = (
        db.query(
            func.avg(Metric.cpu_usage).label("avg_cpu"),
            func.avg(Metric.memory_usage).label("avg_memory"),
            func.avg(Metric.disk_usage).label("avg_disk"),
            func.avg(Metric.temperature).label("avg_temperature"),
            func.max(Metric.cpu_usage).label("max_cpu"),
            func.max(Metric.temperature).label("max_temperature"),
            func.count(Metric.id).label("sample_count"),
        )
        .filter(Metric.server_id == server_id, Metric.recorded_at >= since)
        .first()
    )

    if not result or result.sample_count == 0:
        raise HTTPException(status_code=404, detail="No metrics in the requested window.")

    summary = MetricSummary(
        server_id=server_id,
        hostname=server.hostname,
        avg_cpu=round(result.avg_cpu, 2),
        avg_memory=round(result.avg_memory, 2),
        avg_disk=round(result.avg_disk, 2),
        avg_temperature=round(result.avg_temperature, 2),
        max_cpu=round(result.max_cpu, 2),
        max_temperature=round(result.max_temperature, 2),
        sample_count=result.sample_count,
    )

    # Guardar en caché por 60 segundos
    try:
        cache.setex(cache_key, 60, json.dumps(summary.model_dump()))
    except Exception:
        pass  # Si Redis falla, continuamos sin caché

    return summary