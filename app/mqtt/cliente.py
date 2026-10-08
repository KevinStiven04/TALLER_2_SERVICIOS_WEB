import json
import os
import paho.mqtt.client as mqtt
from pydantic import ValidationError
from datetime import datetime, timezone
from dotenv import load_dotenv

from app.database.connection import SessionLocal
from app.schemas.medicion import MQTTPayload
from app.crud.sensor import get_sensor_by_codigo
from app.crud.sensor_magnitud import get_magnitud_by_sensor_and_name
from app.crud.medicion import create_medicion

load_dotenv()

BROKER = os.getenv("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC")
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))


def process_message(payload_str: str, topic: str):
    """Procesa el mensaje, lo valida y lo almacena si es correcto."""
    db = SessionLocal()
    try:
        # 1. Validar estructura JSON y esquema Pydantic
        try:
            data = json.loads(payload_str)
            mqtt_data = MQTTPayload(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[RECHAZADO] Payload inválido en {topic}: {e}")
            return

        # 2. Validar existencia del sensor usando su 'codigo' (ej. AQ-001)
        sensor = get_sensor_by_codigo(db, mqtt_data.sensor_id)
        if not sensor or not sensor.activo:
            print(f"[RECHAZADO] Sensor no existe o inactivo: {mqtt_data.sensor_id}")
            return

        # 3. Validar magnitudes y unidades en bloque (todo o nada)
        magnitudes_validas = []
        for mag_name, mag_data in mqtt_data.measurements.items():
            db_mag = get_magnitud_by_sensor_and_name(db, sensor.id, mag_name)
            if not db_mag:
                print(f"[RECHAZADO] Magnitud desconocida: {mag_name}")
                return
            if db_mag.unidad != mag_data.unit:
                print(
                    f"[RECHAZADO] Unidad incorrecta para {mag_name}. Esperada: {db_mag.unidad}, Recibida: {mag_data.unit}")
                return
            if not (db_mag.valor_minimo <= mag_data.value <= db_mag.valor_maximo):
                print(f"[RECHAZADO] Valor fuera de rango para {mag_name}: {mag_data.value}")
                return
            magnitudes_validas.append((db_mag.id, mag_data.value))

        # 4. Asegurar que el timestamp recibido se guarde como UTC
        # Si el timestamp recibido no tiene zona horaria (naive), asumimos que viene en UTC
        ts = mqtt_data.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # 5. Insertar mediciones
        for mag_id, valor in magnitudes_validas:
            create_medicion(db, mag_id, valor, ts)

        print(f"[GUARDADO] {len(magnitudes_validas)} mediciones guardadas para el sensor {sensor.codigo}")

    finally:
        db.close()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"Conectado a MQTT Broker: {BROKER}:{PORT}")
        client.subscribe(TOPIC)
        print(f"Suscrito a: {TOPIC}")
    else:
        print(f"Error de conexión: {reason_code}")


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode("utf-8")
    print(f"\n[{datetime.now().isoformat()}] Mensaje recibido en {msg.topic}")
    process_message(payload_str, msg.topic)


def start_mqtt_client():
    if not BROKER or not TOPIC:
        print("Falta configuración MQTT en .env")
        return

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD or "")

    client.on_connect = on_connect
    client.on_message = on_message

    print("Iniciando cliente MQTT...")
    client.connect(BROKER, PORT, KEEPALIVE)
    client.loop_start()  # Usamos loop_start para que no bloquee FastAPI