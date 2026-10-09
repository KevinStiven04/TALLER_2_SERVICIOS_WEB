"""Valida un mensaje MQTT y, si supera todas las reglas, guarda sus mediciones."""

import logging
from dataclasses import dataclass, field
from datetime import timezone
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud import medicion as crud_medicion
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sensor_magnitud
from app.schemas.medicion import MQTTPayload

logger = logging.getLogger("mqtt")


@dataclass
class Resultado:
    aceptado: bool
    motivos: list[str] = field(default_factory=list)
    ids: list[int] = field(default_factory=list)


def codigo_desde_topico(topico: str) -> str | None:
    """iot/sensors/TEST-001/data -> TEST-001"""
    partes = topico.strip().split("/")
    if len(partes) == 4 and partes[0] == "iot" and partes[1] == "sensors" and partes[3] == "data":
        return partes[2]
    return None


def validar_estructura(crudo: bytes) -> tuple[MQTTPayload | None, list[str]]:
    """Paso 1 (Pydantic): JSON bien formado, campos obligatorios, tipos y timestamp."""
    try:
        return MQTTPayload.model_validate_json(crudo), []
    except (UnicodeDecodeError, ValueError) as error:
        if isinstance(error, ValidationError):
            motivos = [
                f"{'.'.join(str(parte) for parte in e['loc']) or 'payload'}: {e['msg']}"
                for e in error.errors()
            ]
            return None, motivos
        return None, [f"JSON mal formado o codificación inválida: {error}"]


def validar_negocio(
    db: Session, payload: MQTTPayload, topico: str
) -> tuple[list[tuple[int, Decimal]], list[str]]:
    """Paso 2 (ORM): sensor, estado activo, magnitud, correspondencia de unidad y rango."""
    sensor = crud_sensor.get_sensor_by_codigo(db, payload.sensor_id)
    if sensor is None:
        return [], [f"sensor inexistente: '{payload.sensor_id}'"]
    if not sensor.activo:
        return [], [f"sensor inactivo: '{payload.sensor_id}'"]

    sensor_esperado = codigo_desde_topico(topico)
    if sensor_esperado and payload.sensor_id != sensor_esperado:
        return [], [f"el sensor '{payload.sensor_id}' no corresponde al tópico '{topico}'"]

    lecturas: list[tuple[int, Decimal]] = []
    motivos: list[str] = []
    for magnitud, lectura in payload.measurements.items():
        config = crud_sensor_magnitud.get_magnitud_by_sensor_and_name(db, sensor.id, magnitud)
        if config is None:
            motivos.append(f"magnitud no configurada para el sensor: '{magnitud}'")
            continue
        if lectura.unit != config.unidad:
            motivos.append(
                f"unidad incorrecta en '{magnitud}': llegó '{lectura.unit}', se esperaba '{config.unidad}'"
            )
            continue
        valor = Decimal(str(lectura.value))
        if not (config.valor_minimo <= valor <= config.valor_maximo):
            motivos.append(
                f"valor fuera de rango en '{magnitud}': {valor} "
                f"(permitido {config.valor_minimo} a {config.valor_maximo})"
            )
            continue
        lecturas.append((config.id, valor))
    return lecturas, motivos


def procesar_mensaje(db: Session, crudo: bytes, topico: str) -> Resultado:
    """Punto de entrada: decide si el mensaje se almacena atómicamente o se rechaza."""
    texto = crudo.decode("utf-8", errors="replace")

    payload, motivos = validar_estructura(crudo)
    if payload is None:
        logger.warning("[RECHAZADO] estructura | %s | payload=%s", "; ".join(motivos), texto)
        return Resultado(False, motivos)

    lecturas, motivos = validar_negocio(db, payload, topico)
    if motivos:  # regla de todo o nada: si una magnitud es inválida se descarta todo el payload
        logger.warning("[RECHAZADO] negocio | %s | payload=%s", "; ".join(motivos), texto)
        return Resultado(False, motivos)

    # Normalizar timestamp a UTC conservando la referencia
    timestamp_utc = payload.timestamp.astimezone(timezone.utc)
    if any(crud_medicion.existe_medicion(db, sm_id, timestamp_utc) for sm_id, _ in lecturas):
        logger.info("[OMITIDO] duplicado | sensor=%s ts=%s", payload.sensor_id, timestamp_utc.isoformat())
        return Resultado(False, ["medición ya almacenada previamente (duplicado)"])

    mediciones = crud_medicion.create_mediciones_batch(db, lecturas, timestamp_utc)
    ids = [m.id for m in mediciones]
    logger.info(
        "[GUARDADO] sensor=%s ts=%s mediciones=%d ids=%s",
        payload.sensor_id, timestamp_utc.isoformat(), len(ids), ids,
    )
    return Resultado(True, ids=ids)
