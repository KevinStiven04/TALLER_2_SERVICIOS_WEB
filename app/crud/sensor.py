from sqlalchemy.orm import Session
from app.models.sensor import Sensor


def get_sensor(db: Session, sensor_id: int):
    return db.query(Sensor).filter(Sensor.id == sensor_id).first()


def get_sensor_by_codigo(db: Session, codigo: str):
    return db.query(Sensor).filter(Sensor.codigo == codigo).first()


def get_sensores(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Sensor).offset(skip).limit(limit).all()


# Aliases para compatibilidad con scripts
obtener_sensor = get_sensor
obtener_sensor_por_codigo = get_sensor_by_codigo
listar_sensores = get_sensores
