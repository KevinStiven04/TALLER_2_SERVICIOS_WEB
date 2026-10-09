from decimal import Decimal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from app.schemas.fechas import FechaColombia


class MeasurementValue(BaseModel):
    model_config = ConfigDict(strict=True)

    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=20)


class MQTTPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    sensor_id: str = Field(min_length=1, max_length=20)
    timestamp: AwareDatetime
    measurements: dict[str, MeasurementValue] = Field(min_length=1)


class MedicionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_magnitud_id: int
    magnitud: str
    unidad: str
    valor: Decimal
    timestamp_colombia: FechaColombia = Field(validation_alias="timestamp_utc")
    fecha_recepcion: FechaColombia
