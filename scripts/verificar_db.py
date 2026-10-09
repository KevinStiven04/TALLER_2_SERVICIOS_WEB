"""Comprueba la conexión a PostgreSQL y muestra el sensor asignado."""

import os

from sqlalchemy import func, select

from app.database.connection import SessionLocal
from app.models import Medicion, Sensor, SensorMagnitud

codigo = os.getenv("MQTT_TOPIC", "").split("/")[2]

with SessionLocal() as db:
    print("Sensores:", db.scalar(select(func.count()).select_from(Sensor)))
    print("Magnitudes:", db.scalar(select(func.count()).select_from(SensorMagnitud)))
    print("Mediciones:", db.scalar(select(func.count()).select_from(Medicion)))

    sensor = db.scalars(select(Sensor).where(Sensor.codigo == codigo)).first()
    if sensor is None:
        print(f"No se encontró el sensor '{codigo}'. Revisa MQTT_TOPIC en .env")
    else:
        print(f"\nSensor {sensor.codigo} (id={sensor.id}, activo={sensor.activo}): {sensor.nombre}")
        for m in sensor.magnitudes:
            print(f"  - {m.magnitud} [{m.unidad}] rango {m.valor_minimo} a {m.valor_maximo}")
