"""Entrega payloads inválidos al procesador, sin pasar por el broker.

Sirve para demostrar los rechazos (pruebas 3 a 7) cuando el servicio del docente
no publicó alguno de esos casos. Ningún caso escribe en la base: todos se rechazan.

Uso: python -m scripts.probar_validaciones
"""

import json
import logging
import os

from sqlalchemy.orm import Session

from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sensor_magnitud
from app.database.connection import SessionLocal
from app.mqtt.procesador import procesar_mensaje

TOPICO = os.getenv("MQTT_TOPIC", "")
CODIGO = TOPICO.split("/")[2] if TOPICO.count("/") == 3 else ""


def construir_casos(db: Session) -> dict[str, bytes]:
    """Arma los payloads inválidos a partir de la configuración real del sensor."""
    sensor = crud_sensor.obtener_sensor_por_codigo(db, CODIGO)
    if sensor is None:
        raise SystemExit(f"No existe el sensor '{CODIGO}'. Revisa MQTT_TOPIC en .env")
    config = crud_sensor_magnitud.listar_por_sensor(db, sensor.id)[0]
    magnitud, unidad = config.magnitud, config.unidad
    valido = float((config.valor_minimo + config.valor_maximo) / 2)
    fuera = float(config.valor_maximo) + 1000

    def payload(**cambios) -> bytes:
        base = {
            "sensor_id": CODIGO,
            "timestamp": "2026-10-07T16:25:30Z",
            "measurements": {magnitud: {"value": valido, "unit": unidad}},
        }
        base.update(cambios)
        return json.dumps(base).encode()

    return {
        "sensor_inexistente": payload(sensor_id="NO-EXISTE-999"),
        "unidad_incorrecta": payload(measurements={magnitud: {"value": valido, "unit": "XYZ"}}),
        "tipo_incorrecto": payload(measurements={magnitud: {"value": str(valido), "unit": unidad}}),
        "magnitud_incorrecta": payload(measurements={"magnitud_falsa": {"value": 1.0, "unit": "x"}}),
        "timestamp_invalido": payload(timestamp="2026-13-45T99:99:99Z"),
        "fuera_de_rango": payload(measurements={magnitud: {"value": fuera, "unit": unidad}}),
        "json_mal_formado": b'{"sensor_id": ',
    }


if __name__ == "__main__":
    # Estos casos locales no se escriben en logs/mqtt.log, que queda solo con mensajes reales.
    logging.getLogger("mqtt").addHandler(logging.NullHandler())
    with SessionLocal() as db:
        for nombre, crudo in construir_casos(db).items():
            resultado = procesar_mensaje(db, crudo, TOPICO)
            estado = "ALMACENADO (revisar!)" if resultado.aceptado else "rechazado"
            print(f"{nombre}: {estado} -> {resultado.motivos}\n")
