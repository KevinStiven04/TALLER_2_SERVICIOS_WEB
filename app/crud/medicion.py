from typing import Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.medicion import Medicion
from app.models.sensor_magnitud import SensorMagnitud


def get_medicion_by_id(db: Session, medicion_id: int) -> Optional[Medicion]:
    return db.query(Medicion).options(
        joinedload(Medicion.sensor_magnitud)
    ).filter(Medicion.id == medicion_id).first()


def existe_medicion(db: Session, sensor_magnitud_id: int, timestamp_utc: datetime) -> bool:
    return db.query(Medicion.id).filter(
        Medicion.sensor_magnitud_id == sensor_magnitud_id,
        Medicion.timestamp_utc == timestamp_utc
    ).first() is not None


def create_medicion(db: Session, sensor_magnitud_id: int, valor: float | Decimal, timestamp_utc: datetime) -> Medicion:
    db_medicion = Medicion(
        sensor_magnitud_id=sensor_magnitud_id,
        valor=valor,
        timestamp_utc=timestamp_utc
    )
    db.add(db_medicion)
    db.commit()
    db.refresh(db_medicion)
    return db_medicion


def create_mediciones_batch(
    db: Session,
    lecturas: list[tuple[int, float | Decimal]],
    timestamp_utc: datetime
) -> list[Medicion]:
    """Inserta todas las mediciones de un payload en una sola transacción atómica."""
    mediciones = [
        Medicion(
            sensor_magnitud_id=sm_id,
            valor=valor,
            timestamp_utc=timestamp_utc
        )
        for sm_id, valor in lecturas
    ]
    db.add_all(mediciones)
    db.commit()
    for m in mediciones:
        db.refresh(m)
    return mediciones


def get_mediciones_by_sensor(
    db: Session,
    sensor_id: int,
    magnitud: Optional[str] = None,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    limit: int = 100
) -> list[Medicion]:
    query = (
        db.query(Medicion)
        .join(Medicion.sensor_magnitud)
        .options(joinedload(Medicion.sensor_magnitud))
        .filter(SensorMagnitud.sensor_id == sensor_id)
    )

    if magnitud:
        query = query.filter(SensorMagnitud.magnitud == magnitud)
    if desde:
        query = query.filter(Medicion.timestamp_utc >= desde)
    if hasta:
        query = query.filter(Medicion.timestamp_utc <= hasta)

    return query.order_by(desc(Medicion.timestamp_utc), desc(Medicion.id)).limit(limit).all()


def get_ultima_medicion(db: Session, sensor_id: int, magnitud: Optional[str] = None) -> Optional[Medicion]:
    query = (
        db.query(Medicion)
        .join(Medicion.sensor_magnitud)
        .options(joinedload(Medicion.sensor_magnitud))
        .filter(SensorMagnitud.sensor_id == sensor_id)
    )
    if magnitud:
        query = query.filter(SensorMagnitud.magnitud == magnitud)

    return query.order_by(desc(Medicion.timestamp_utc), desc(Medicion.id)).first()


# Aliases para compatibilidad con scripts
obtener_medicion = get_medicion_by_id
listar_por_sensor = get_mediciones_by_sensor
ultima_por_sensor = get_ultima_medicion
crear_mediciones = create_mediciones_batch
