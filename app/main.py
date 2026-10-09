from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.mqtt.cliente import start_mqtt_client
from app.api.sensor import router as sensor_router
from app.api.sensor_magnitud import router as sensor_magnitud_router
from app.api.medicion import router as medicion_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: Arrancar el cliente MQTT al iniciar la API
    start_mqtt_client()
    yield
    # Fin / Shutdown (si es necesario)


app = FastAPI(
    title="IoT Sensors API",
    description="API REST y receptor MQTT para mediciones de sensores IoT",
    version="1.0.0",
    lifespan=lifespan
)

# Incluir routers de la API
app.include_router(sensor_router)
app.include_router(sensor_magnitud_router)
app.include_router(medicion_router)
