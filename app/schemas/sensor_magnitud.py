from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class SensorMagnitudBase(BaseModel):
    magnitud: str
    unidad: str
    valor_minimo: Decimal
    valor_maximo: Decimal


class SensorMagnitudResponse(SensorMagnitudBase):
    id: int
    sensor_id: int

    model_config = ConfigDict(from_attributes=True)
