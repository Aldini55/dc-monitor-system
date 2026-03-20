from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from models import ServerStatus, AlertSeverity, AlertStatus


# ─── Server Schemas ───────────────────────────────────────────────────────────

class ServerCreate(BaseModel):
    hostname: str
    ip_address: str
    rack: str
    datacenter_zone: str
    role: str
    status: ServerStatus = ServerStatus.online
    os: str = "Ubuntu 22.04 LTS"
    cpu_cores: int = 8
    ram_gb: int = 32


class ServerUpdate(BaseModel):
    ip_address: Optional[str] = None
    rack: Optional[str] = None
    datacenter_zone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[ServerStatus] = None
    os: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None


class ServerOut(BaseModel):
    id: int
    hostname: str
    ip_address: str
    rack: str
    datacenter_zone: str
    role: str
    status: ServerStatus
    os : str
    cpu_cores: int
    ram_gb: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Metric Schemas ───────────────────────────────────────────────────────────

class MetricCreate(BaseModel):
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=0, le=120)
    network_in: float = Field(..., ge=0)
    network_out: float = Field(..., ge=0)


class MetricOut(BaseModel):
    id: int
    server_id: int
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: float
    network_in: float
    network_out: float
    recorded_at: datetime

    model_config = {"from_attributes": True}


class MetricSummary(BaseModel):
    server_id: int
    hostname: str
    avg_cpu: float
    avg_memory: float
    avg_disk: float
    avg_temperature: float
    max_cpu: float
    max_temperature: float
    sample_count: int


# ─── Alert Schemas ────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    server_id: int
    severity: AlertSeverity
    metric: str
    message: str
    value: float
    threshold: float


class AlertUpdate(BaseModel):
    status: AlertStatus
    resolved_at: Optional[datetime] = None


class AlertOut(BaseModel):
    id: int
    server_id: int
    severity: AlertSeverity
    metric: str
    message: str
    value: float
    threshold: float
    status: AlertStatus
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}