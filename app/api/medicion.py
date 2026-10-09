from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.medicion import MedicionResponse
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sensor_magnitud
from app.crud import medicion as crud_medicion

router = APIRouter(tags=["mediciones"])

COLOMBIA_TZ = ZoneInfo("America/Bogota")


def normalizar_a_utc(fecha: Optional[datetime]) -> Optional[datetime]:
    """Si la fecha no tiene zona horaria, se asume hora local de Colombia y se convierte a UTC."""
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=COLOMBIA_TZ)
    return fecha.astimezone(timezone.utc)


def validar_sensor_y_magnitud(db: Session, sensor_id: int, magnitud: Optional[str] = None):
    sensor = crud_sensor.get_sensor(db=db, sensor_id=sensor_id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor con ID {sensor_id} no encontrado"
        )
    if magnitud is not None:
        sm = crud_sensor_magnitud.get_magnitud_by_sensor_and_name(db=db, sensor_id=sensor_id, magnitud=magnitud)
        if not sm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El sensor {sensor_id} no tiene configurada la magnitud '{magnitud}'"
            )


@router.get("/mediciones/{id}", response_model=MedicionResponse)
def get_medicion_por_id(id: int, db: Session = Depends(get_db)):
    medicion = crud_medicion.get_medicion_by_id(db=db, medicion_id=id)
    if not medicion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medición con ID {id} no encontrada"
        )
    return medicion


@router.get("/sensores/{id}/mediciones", response_model=List[MedicionResponse])
def get_mediciones_por_sensor(
    id: int,
    magnitud: Optional[str] = Query(None, description="Filtrar por nombre de magnitud"),
    desde: Optional[datetime] = Query(None, description="Fecha y hora de inicio"),
    hasta: Optional[datetime] = Query(None, description="Fecha y hora de fin"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados a retornar"),
    db: Session = Depends(get_db)
):
    validar_sensor_y_magnitud(db=db, sensor_id=id, magnitud=magnitud)

    desde_utc = normalizar_a_utc(desde)
    hasta_utc = normalizar_a_utc(hasta)

    if desde_utc is not None and hasta_utc is not None and desde_utc > hasta_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'desde' no puede ser mayor que 'hasta'"
        )

    return crud_medicion.get_mediciones_by_sensor(
        db=db,
        sensor_id=id,
        magnitud=magnitud,
        desde=desde_utc,
        hasta=hasta_utc,
        limit=limit
    )


@router.get("/sensores/{id}/ultima-medicion", response_model=MedicionResponse)
def get_ultima_medicion_sensor(
    id: int,
    magnitud: Optional[str] = Query(None, description="Filtrar por nombre de magnitud"),
    db: Session = Depends(get_db)
):
    validar_sensor_y_magnitud(db=db, sensor_id=id, magnitud=magnitud)

    ultima = crud_medicion.get_ultima_medicion(db=db, sensor_id=id, magnitud=magnitud)
    if not ultima:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron mediciones para el sensor con ID {id}"
        )

    return ultima
