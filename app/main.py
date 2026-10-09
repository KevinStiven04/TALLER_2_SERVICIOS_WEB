from contextlib import asynccontextmanager
import os
from fastapi import FastAPI

from app.mqtt.client import start_mqtt_client, stop_mqtt_client
from app.api.sensor import router as sensor_router
from app.api.sensor_magnitud import router as sensor_magnitud_router
from app.api.medicion import router as medicion_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: Arrancar el cliente MQTT al iniciar la API si está habilitado
    mqtt_enabled = os.getenv("MQTT_ENABLED", "true").lower() in ("true", "1", "yes")
    if mqtt_enabled:
        start_mqtt_client()
    yield
    # Fin / Shutdown limpio del consumidor MQTT
    if mqtt_enabled:
        stop_mqtt_client()


app = FastAPI(
    title="IoT Sensors API",
    description="API REST y receptor MQTT para adquisición, validación y consulta de datos de sensores IoT",
    version="1.0.0",
    lifespan=lifespan
)

# Incluir routers de la API
app.include_router(sensor_router)
app.include_router(sensor_magnitud_router)
app.include_router(medicion_router)
