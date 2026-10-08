from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.medicion import MedicionResponse
from app.crud import sensor as crud_sensor
from app.crud import medicion as crud_medicion
from app.models.medicion import Medicion

router = APIRouter(tags=["mediciones"])

COLOMBIA_TZ = ZoneInfo("America/Bogota")


def convertir_a_colombia(medicion: Medicion) -> MedicionResponse:
    ts = medicion.timestamp_utc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    ts_colombia = ts.astimezone(COLOMBIA_TZ)

    fecha_rec = medicion.fecha_recepcion
    if fecha_rec and fecha_rec.tzinfo is None:
        fecha_rec = fecha_rec.replace(tzinfo=timezone.utc)
    fecha_rec_colombia = fecha_rec.astimezone(COLOMBIA_TZ) if fecha_rec else fecha_rec

    return MedicionResponse(
        id=medicion.id,
        sensor_magnitud_id=medicion.sensor_magnitud_id,
        valor=medicion.valor,
        timestamp_utc=ts_colombia,
        fecha_recepcion=fecha_rec_colombia
    )


@router.get("/mediciones/{id}", response_model=MedicionResponse)
def get_medicion_por_id(id: int, db: Session = Depends(get_db)):
    medicion = db.query(Medicion).filter(Medicion.id == id).first()
    if not medicion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medición con ID {id} no encontrada"
        )
    return convertir_a_colombia(medicion)


@router.get("/sensores/{id}/mediciones", response_model=List[MedicionResponse])
def get_mediciones_por_sensor(
    id: int,
    magnitud: Optional[str] = Query(None, description="Filtrar por nombre de magnitud"),
    desde: Optional[datetime] = Query(None, description="Fecha y hora de inicio"),
    hasta: Optional[datetime] = Query(None, description="Fecha y hora de fin"),
    limit: int = Query(100, ge=1, description="Límite de resultados a retornar"),
    db: Session = Depends(get_db)
):
    sensor = crud_sensor.get_sensor(db=db, sensor_id=id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor con ID {id} no encontrado"
        )

    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'desde' no puede ser mayor que 'hasta'"
        )

    mediciones = crud_medicion.get_mediciones_by_sensor(
        db=db,
        sensor_id=id,
        magnitud=magnitud,
        desde=desde,
        hasta=hasta,
        limit=limit
    )

    return [convertir_a_colombia(m) for m in mediciones]


@router.get("/sensores/{id}/ultima-medicion", response_model=MedicionResponse)
def get_ultima_medicion_sensor(id: int, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor(db=db, sensor_id=id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor con ID {id} no encontrado"
        )

    ultima = crud_medicion.get_ultima_medicion(db=db, sensor_id=id)
    if not ultima:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron mediciones para el sensor con ID {id}"
        )

    return convertir_a_colombia(ultima)
