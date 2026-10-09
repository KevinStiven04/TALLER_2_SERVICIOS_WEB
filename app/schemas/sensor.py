from pydantic import BaseModel, ConfigDict
from app.schemas.fechas import FechaColombia


class SensorBase(BaseModel):
    codigo: str
    nombre: str
    categoria: str
    ubicacion: str
    activo: bool = True


class SensorResponse(SensorBase):
    id: int
    fecha_registro: FechaColombia

    model_config = ConfigDict(from_attributes=True)
