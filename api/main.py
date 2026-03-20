from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth import require_api_key
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models
from routers import servers, metrics, alerts, compare


def seed_database(db: Session):
    if db.query(models.Server).count() > 0:
        return

    sample_servers = [
        models.Server(hostname="web-01",       ip_address="10.0.1.10", rack="A1",
                    datacenter_zone="Zone-1", role="web",
                    os="Ubuntu 22.04 LTS", cpu_cores=8, ram_gb=32,
                    status=models.ServerStatus.online),
        models.Server(hostname="web-02",       ip_address="10.0.1.11", rack="A1",
                    datacenter_zone="Zone-1", role="web",
                    os="Ubuntu 22.04 LTS", cpu_cores=8, ram_gb=32,
                    status=models.ServerStatus.online),
        models.Server(hostname="db-primary",   ip_address="10.0.2.10", rack="B1",
                    datacenter_zone="Zone-1", role="database",
                    os="Ubuntu 22.04 LTS", cpu_cores=16, ram_gb=128,
                    status=models.ServerStatus.online),
        models.Server(hostname="db-replica",   ip_address="10.0.2.11", rack="B2",
                    datacenter_zone="Zone-1", role="database",
                    os="Ubuntu 22.04 LTS", cpu_cores=16, ram_gb=128,
                    status=models.ServerStatus.online),
        models.Server(hostname="storage-01",   ip_address="10.0.3.10", rack="C1",
                    datacenter_zone="Zone-2", role="storage",
                    os="Ubuntu 22.04 LTS", cpu_cores=4, ram_gb=16,
                    status=models.ServerStatus.online),
        models.Server(hostname="cache-01",     ip_address="10.0.4.10", rack="D1",
                    datacenter_zone="Zone-2", role="cache",
                    os="Ubuntu 22.04 LTS", cpu_cores=8, ram_gb=64,
                    status=models.ServerStatus.maintenance),
        models.Server(hostname="backup-01", ip_address="10.0.5.10", rack="E1",
                  datacenter_zone="Zone-2", role="backup",
                  cpu_cores=4, ram_gb=16,
                  status=models.ServerStatus.online),
        models.Server(hostname="monitor-01", ip_address="10.0.6.10", rack="F1",
                  datacenter_zone="Zone-3", role="monitoring",
                  cpu_cores=8, ram_gb=32,
                  status=models.ServerStatus.online),
        models.Server(hostname="loadbalancer-01", ip_address="10.0.7.10", rack="G1",
                  datacenter_zone="Zone-3", role="loadbalancer",
                  cpu_cores=8, ram_gb=16,
                  status=models.ServerStatus.online),
    ]
    db.add_all(sample_servers)
    db.commit()
    print("Database seeded with sample servers.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="DC Monitor API",
    description=(
        "A REST API for monitoring Data Center infrastructure health. "
        "Track servers, ingest real-time metrics, and manage alerts."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(servers.router, dependencies=[Depends(require_api_key)])
app.include_router(metrics.router, dependencies=[Depends(require_api_key)])
app.include_router(alerts.router, dependencies=[Depends(require_api_key)])
app.include_router(compare.router, dependencies=[Depends(require_api_key)])

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "DC Monitor API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
