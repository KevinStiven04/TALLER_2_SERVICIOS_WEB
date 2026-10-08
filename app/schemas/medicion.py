from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class MeasurementValue(BaseModel):
    value: float
    unit: str


class MQTTPayload(BaseModel):
    sensor_id: str
    timestamp: datetime
    measurements: dict[str, MeasurementValue]


class MedicionResponse(BaseModel):
    id: int
    sensor_magnitud_id: int
    valor: Decimal
    timestamp_utc: datetime
    fecha_recepcion: datetime

    model_config = ConfigDict(from_attributes=True)
