from sqlalchemy import Column, Integer, BigInteger, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Medicion(Base):
    __tablename__ = "mediciones"

    # BigSerial para la PK
    id = Column(BigInteger, primary_key=True)
    sensor_magnitud_id = Column(Integer, ForeignKey("sensor_magnitudes.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    valor = Column(Numeric(12, 4), nullable=False)
    # Índice B-tree para consultas históricas y de rangos
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    fecha_recepcion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sensor_magnitud = relationship("SensorMagnitud", back_populates="mediciones")