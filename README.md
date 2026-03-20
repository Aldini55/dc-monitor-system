# Data Center Monitoring System 

Este proyecto es un Sistema de monitoreo para infraestructura de centros de datos basado en microservicios
diseñado para la detección temprana de anomalías y alertas automatizadas.

## Arquitectura
Este proyecto demuestra mis conocimientos en desarrollo Backend y DevOps

- **Backend:** Python 3.10+ con **FastAPI** .
- **Base de Datos:** **PostgreSQL** para persistencia de métricas históricas.
- **Caching & Real-time:** **Redis** para el manejo de estados rápidos de los servidores.
- **Containerización:** **Docker & Docker Compose** para orquestar 4 microservicios.
- **Notificaciones:** Integración con **Telegram Bot API** para alertas críticas.
- **Frontend:** Dashboard interactivo con **Tailwind CSS**, filtros dinámicos y **Modo Oscuro**.

## Extensiones adicioanles
Para mi proyecto implementé tres capas avanzadas de lógica:

1. **Standard Thresholds (NOM):** Ajuste de umbrales basado en la normativa mexicana **NOM-001-SEDE** y estándares **ASHRAE** (Límite crítico de temperatura a 27°C para eficiencia energética).
2. **Interactive UX:** Implementación de persistencia de tema (Dark Mode), filtrado de servidores por rol (Web/DB/Storage) y contadores de alertas dinámicos.
3. **System Health Analytics:** Algoritmo que calcula el % de salud global del Data Center en tiempo real basado en la severidad de las alertas abiertas.

## Cómo ejecutarlo
Requisitos: Docker & Docker Compose instalados.

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/TU_USUARIO/dc-monitor-system.git](https://github.com/TU_USUARIO/dc-monitor-system.git)
