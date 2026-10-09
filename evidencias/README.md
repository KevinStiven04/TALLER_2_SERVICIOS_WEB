# Evidencias

Esta carpeta se llena con datos reales del sensor asignado:

1. Recolecten datos al menos 20 minutos con la API y el consumidor encendidos (paso 4 de `LEEME_PRIMERO.md`).
2. Con la API todavía encendida, en otra terminal: `python -m scripts.generar_evidencias`

El script crea:

- `evidencias.md`: las 18 pruebas de la Actividad 6, cada una con datos de entrada, resultado, código HTTP, registro almacenado o rechazado, archivo y función, y explicación.
- `mqtt_log.txt`: copia del registro completo del consumidor MQTT.

Pueden agregar aquí capturas de pantalla de `/docs`, de la consola o de la base de datos.
