from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.sensor import SensorResponse
from app.crud import sensor as crud_sensor

router = APIRouter(tags=["sensores"])


@router.get("/sensores", response_model=List[SensorResponse])
def get_sensores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_sensor.get_sensores(db=db, skip=skip, limit=limit)


@router.get("/sensores/por-codigo/{codigo}", response_model=SensorResponse)
def get_sensor_por_codigo(codigo: str, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor_by_codigo(db=db, codigo=codigo)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor con código '{codigo}' no encontrado"
        )
    return sensor


@router.get("/sensores/{id}", response_model=SensorResponse)
def get_sensor_por_id(id: int, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor(db=db, sensor_id=id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor con ID {id} no encontrado"
        )
    return sensor
