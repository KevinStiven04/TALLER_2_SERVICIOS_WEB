from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.sensor_magnitud import SensorMagnitudResponse
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sensor_magnitud
from app.models.sensor_magnitud import SensorMagnitud

router = APIRouter(tags=["sensor-magnitudes"])


@router.get("/sensores/{id}/magnitudes", response_model=List[SensorMagnitudResponse])
def get_magnitudes_por_sensor(id: int, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor(db=db, sensor_id=id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor con ID {id} no encontrado"
        )
    return crud_sensor_magnitud.get_magnitudes_by_sensor(db=db, sensor_id=id)


@router.get("/sensor-magnitudes/{id}", response_model=SensorMagnitudResponse)
def get_sensor_magnitud_por_id(id: int, db: Session = Depends(get_db)):
    sensor_magnitud = db.query(SensorMagnitud).filter(SensorMagnitud.id == id).first()
    if not sensor_magnitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SensorMagnitud con ID {id} no encontrada"
        )
    return sensor_magnitud
