from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from database import get_db
from models import Server, Metric
from schemas import MetricSummary

router = APIRouter(prefix="/metrics", tags=["Compare"])

@router.get("/compare", summary="Compare metrics across multiple servers")
def compare_servers(
    ids: str = Query(..., description="Comma-separated server IDs. Example: 1,2,3"),
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Return aggregated metric summaries for multiple servers side by side.
    Useful for identifying which server is under the most stress.

    - **ids**: comma-separated list of server IDs (e.g. 1,2,3)
    - **hours**: time window to aggregate (1-168 hours)
    """
    # Parse and validate the IDs
    try:
        server_ids = [int(i.strip()) for i in ids.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use comma-separated integers: ?ids=1,2,3"
        )

    if len(server_ids) > 10:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10 servers can be compared at once."
        )

    since = datetime.utcnow() - timedelta(hours=hours)
    results = []

    for server_id in server_ids:
        server = db.query(Server).filter(Server.id == server_id).first()
        
        if not server:
            raise HTTPException(
                status_code=404, 
                detail=f"Server with ID {server_id} not found."
            )

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
            results.append({
                "server_id": server_id,
                "hostname": server.hostname,
                "role": server.role,
                "datacenter_zone": server.datacenter_zone,
                "message": "No metrics in the requested time window."
            })
            continue

        results.append({
            "server_id": server_id,
            "hostname": server.hostname,
            "role": server.role,
            "datacenter_zone": server.datacenter_zone,
            "avg_cpu": round(result.avg_cpu, 2),
            "avg_memory": round(result.avg_memory, 2),
            "avg_disk": round(result.avg_disk, 2),
            "avg_temperature": round(result.avg_temperature, 2),
            "max_cpu": round(result.max_cpu, 2),
            "max_temperature": round(result.max_temperature, 2),
            "sample_count": result.sample_count,
            "hours_analyzed": hours,
        })

    return results