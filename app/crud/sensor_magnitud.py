from sqlalchemy.orm import Session
from app.models.sensor_magnitud import SensorMagnitud

def get_magnitudes_by_sensor(db: Session, sensor_id: int):
    return db.query(SensorMagnitud).filter(SensorMagnitud.sensor_id == sensor_id).all()

def get_magnitud_by_sensor_and_name(db: Session, sensor_id: int, magnitud: str):
    return db.query(SensorMagnitud).filter(
        SensorMagnitud.sensor_id == sensor_id,
        SensorMagnitud.magnitud == magnitud
    ).first()