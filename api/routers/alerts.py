from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import Alert, AlertStatus, AlertSeverity
from schemas import AlertCreate, AlertUpdate, AlertOut

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=List[AlertOut], summary="List all alerts")
def list_alerts(
    severity: AlertSeverity = None,
    status: AlertStatus = None,
    server_id: int = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Return alerts. Optionally filter by severity, status, server_id.
    Supports pagination with offset and limit.
    """
    query = db.query(Alert)

    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    if server_id:
        query = query.filter(Alert.server_id == server_id)

    total = query.count()
    alerts = (
        query
        .order_by(Alert.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return alerts


@router.get("/summary/open", summary="Count of open alerts by severity")
def open_alerts_summary(db: Session = Depends(get_db)):
    results = {}
    for sev in AlertSeverity:
        count = (
            db.query(Alert)
            .filter(Alert.status == AlertStatus.open, Alert.severity == sev)
            .count()
        )
        results[sev.value] = count
    results["total"] = sum(results.values())
    return results


@router.get("/{alert_id}", response_model=AlertOut, summary="Get alert by ID")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


@router.patch("/{alert_id}", response_model=AlertOut,
              summary="Acknowledge or resolve an alert")
def update_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    alert.status = payload.status
    if payload.status == AlertStatus.resolved:
        alert.resolved_at = payload.resolved_at or datetime.utcnow()

    db.commit()
    db.refresh(alert)
    return alert