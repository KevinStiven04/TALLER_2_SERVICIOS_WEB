from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo
from pydantic import PlainSerializer

ZONA_COLOMBIA = ZoneInfo("America/Bogota")
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def a_hora_colombia(valor: datetime) -> str:
    """Convierte un datetime con zona horaria a texto legible en hora local de Colombia."""
    if valor.tzinfo is None:
        # Si es naive, asumimos UTC
        from datetime import timezone
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(ZONA_COLOMBIA).strftime(FORMATO_FECHA)


# Tipo reutilizable para Pydantic: convierte a hora local de Colombia en formato legible
FechaColombia = Annotated[datetime, PlainSerializer(a_hora_colombia, return_type=str)]
