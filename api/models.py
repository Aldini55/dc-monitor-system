from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


class ServerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    rack = Column(String, nullable=False)
    datacenter_zone = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(Enum(ServerStatus), default=ServerStatus.online)
    os = Column(String, nullable=False, default="Ubuntu 22.04 LTS")
    cpu_cores = Column(Integer, nullable=False, default=8)
    ram_gb = Column(Integer, nullable=False, default=32)
    created_at = Column(DateTime, server_default=func.now())

    metrics = relationship("Metric", back_populates="server", cascade="all, delete")
    alerts = relationship("Alert", back_populates="server", cascade="all, delete")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    disk_usage = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    network_in = Column(Float, nullable=False)
    network_out = Column(Float, nullable=False)
    recorded_at = Column(DateTime, server_default=func.now(), index=True)

    server = relationship("Server", back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    metric = Column(String, nullable=False)
    message = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.open)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    server = relationship("Server", back_populates="alerts")
