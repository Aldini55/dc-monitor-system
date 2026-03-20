from models import Server, Alert
from schemas import ServerCreate, ServerUpdate, ServerOut, AlertOut
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Server
from schemas import ServerCreate, ServerUpdate, ServerOut

router = APIRouter(prefix="/servers", tags=["Servers"])

@router.get("/", response_model=List[ServerOut], summary="List all servers")
def list_servers(
    zone: str = None,
    role: str = None,
    status: str = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Return all registered servers. Optionally filter by zone, role, status.
    Supports pagination with offset and limit.
    """
    query = db.query(Server)

    if zone:
        query = query.filter(Server.datacenter_zone == zone)
    if role:
        query = query.filter(Server.role == role)
    if status:
        query = query.filter(Server.status == status)

    total = query.count()
    servers = query.order_by(Server.id).offset(offset).limit(limit).all()
    
    return servers


@router.post("/", response_model=ServerOut, status_code=status.HTTP_201_CREATED,
             summary="Register a new server")
def create_server(payload: ServerCreate, db: Session = Depends(get_db)):
    existing = db.query(Server).filter(Server.hostname == payload.hostname).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Server with hostname '{payload.hostname}' already exists."
        )
    server = Server(**payload.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@router.get("/{server_id}", response_model=ServerOut, summary="Get server by ID")
def get_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")
    return server


@router.patch("/{server_id}", response_model=ServerOut, summary="Update server fields")
def update_server(server_id: int, payload: ServerUpdate, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(server, field, value)
    db.commit()
    db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Deregister a server")
def delete_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")
    db.delete(server)
    db.commit()
    
@router.get("/{server_id}/alerts", response_model=List[AlertOut],
            summary="Get alert history for a server")
def get_server_alerts(
    server_id: int,
    severity: str = None,
    status: str = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Return the full alert history for a specific server.
    Optionally filter by severity and/or status.
    Supports pagination with offset and limit.
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    query = db.query(Alert).filter(Alert.server_id == server_id)

    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)

    total = query.count()
    alerts = (
        query
        .order_by(Alert.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return alerts