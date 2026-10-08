from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SensorBase(BaseModel):
    codigo: str
    nombre: str
    categoria: str
    ubicacion: str
    activo: bool = True


class SensorResponse(SensorBase):
    id: int
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)
