import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuración de la URL de la base de datos (prioriza variables de entorno de Docker)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dcmonitor:dcmonitor@db:5432/dcmonitor"
)
engine = create_engine(DATABASE_URL)

# Configuración de la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para los modelos
Base = declarative_base()

def get_db():
    """
    Dependency que provee una sesión de base de datos a los endpoints.
    Asegura que la conexión se cierre después de cada petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()