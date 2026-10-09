"""Conexión al broker MQTT. La lógica de validación y persistencia vive en procesador.py."""

import logging
import os
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from app.database.connection import SessionLocal
from app.mqtt.procesador import procesar_mensaje, Resultado

load_dotenv()

BROKER = os.getenv("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC")
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))

logger = logging.getLogger("mqtt")


def configurar_logs() -> None:
    """Escribe los registros en consola y en logs/mqtt.log (sirve de evidencia del taller)."""
    if logger.handlers:
        return
    Path("logs").mkdir(exist_ok=True)
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for manejador in (logging.StreamHandler(), logging.FileHandler("logs/mqtt.log", encoding="utf-8")):
        manejador.setFormatter(formato)
        logger.addHandler(manejador)
    logger.setLevel(logging.INFO)
    logger.propagate = False


configurar_logs()

_mqtt_client_instance: Optional[mqtt.Client] = None


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        logger.error("Error de conexión MQTT: %s", reason_code)
        return
    client.subscribe(TOPIC, qos=1)
    logger.info("Conectado a %s:%s y suscrito a %s", BROKER, PORT, TOPIC)


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    logger.warning("Desconectado del broker MQTT: %s", reason_code)


def on_message(client, userdata, message):
    texto = message.payload.decode("utf-8", errors="replace")
    logger.info("RECIBIDO | tópico=%s | payload=%s", message.topic, texto)
    try:
        with SessionLocal() as db:
            procesar_mensaje(db, message.payload, message.topic)
    except Exception:
        logger.exception("Error procesando mensaje MQTT")


def process_message(payload_raw: bytes | str, topic: str) -> bool:
    """Procesa un payload validando estructura, tipos, negocio y almacenándolo en PostgreSQL."""
    if isinstance(payload_raw, str):
        payload_bytes = payload_raw.encode("utf-8")
    else:
        payload_bytes = payload_raw

    with SessionLocal() as db:
        resultado: Resultado = procesar_mensaje(db, payload_bytes, topic)
        return resultado.aceptado


def crear_cliente() -> mqtt.Client:
    if not BROKER or not TOPIC:
        raise RuntimeError("Faltan MQTT_BROKER o MQTT_TOPIC en el archivo .env")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD or "")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    return client


def start_mqtt_client() -> Optional[mqtt.Client]:
    global _mqtt_client_instance
    if not BROKER or not TOPIC:
        logger.warning("Falta configuración MQTT (MQTT_BROKER o MQTT_TOPIC) en .env")
        return None
    try:
        client = crear_cliente()
        client.connect_async(BROKER, PORT, KEEPALIVE)
        client.loop_start()
        _mqtt_client_instance = client
        return client
    except Exception as e:
        logger.error(f"No fue posible conectar con el broker MQTT: {e}")
        return None


def stop_mqtt_client():
    global _mqtt_client_instance
    if _mqtt_client_instance is not None:
        try:
            logger.info("Deteniendo cliente MQTT...")
            _mqtt_client_instance.disconnect()
            _mqtt_client_instance.loop_stop()
        except Exception as e:
            logger.warning(f"Error deteniendo cliente MQTT: {e}")
        finally:
            _mqtt_client_instance = None


iniciar = start_mqtt_client
detener = stop_mqtt_client

if __name__ == "__main__":
    cliente = crear_cliente()
    cliente.connect(BROKER, PORT, KEEPALIVE)
    try:
        print("Iniciando consumidor MQTT en primer plano... Presione Ctrl+C para salir.")
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\nConsumidor detenido por el usuario.")
