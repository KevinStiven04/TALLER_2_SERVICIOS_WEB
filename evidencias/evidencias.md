# Evidencias de funcionamiento - Taller 2

- **Generado:** 2026-10-08 20:00:57 (hora de Colombia)
- **Sensor:** `AQ-001` (id 1)
- **Tópico:** `iot/sensors/AQ-001/data`
- **Datos recolectados:** 1207 mediciones entre 2026-10-07 11:25:30 y 2026-10-08 20:00:52 (1955.4 minutos)
- **Registro completo del consumidor:** `evidencias/mqtt_log.txt`

| # | Estado |
| --- | --- |
| 1 | OK |
| 2 | OK |
| 3 | OK (caso local) |
| 4 | OK (caso local) |
| 5 | OK (caso local) |
| 6 | OK (caso local) |
| 7 | OK (caso local) |
| 8 | OK |
| 9 | OK |
| 10 | OK |
| 11 | OK |
| 12 | OK |
| 13 | OK |
| 14 | OK |
| 15 | OK |
| 16 | OK |
| 17 | OK |
| 18 | OK |

## Prueba 1: Recepción MQTT

- **Datos de entrada:** suscripción al tópico `iot/sensors/AQ-001/data`
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** 132 mensajes recibidos según `logs/mqtt.log`
- **Archivo y función:** `app/mqtt/client.py` · `on_connect` y `on_message`
- **Explicación:** El cliente se suscribe en `on_connect` y cada mensaje llega a `on_message`, que lo registra y lo entrega al procesador.

**Resultado obtenido:**

```text
2026-10-08 19:44:36,292 [INFO] mqtt: Conectado a MQTT Broker: emqx.coriotlab.co:1883
2026-10-08 19:50:13,441 [INFO] mqtt: RECIBIDO | tópico=iot/sensors/AQ-001/data | payload={"sensor_id": "AQ-001", "timestamp": "2026-10-09T00:50:12Z", "measurements": {"temperature": {"value": 20.56, "unit": "C"}, "humidity": {"value": 56.02, "unit": "%"}, "co2": {"value": 439.07, "unit": "ppm"}}}
2026-10-08 19:50:18,442 [INFO] mqtt: RECIBIDO | tópico=iot/sensors/AQ-001/data | payload={"sensor_id": "AQ-001", "timestamp": "2026-10-09T00:50:17Z", "measurements": {"temperature": {"value": 21.21, "unit": "C"}, "humidity": {"value": 75.18, "unit": "%"}, "co2": {"value": 798.33, "unit": "ppm"}}}
2026-10-08 19:50:23,441 [INFO] mqtt: RECIBIDO | tópico=iot/sensors/AQ-001/data | payload={"sensor_id": "AQ-001", "timestamp": "2026-10-09T00:50:22Z", "measurements": {"temperature": {"value": 22.11, "unit": "C"}, "humidity": {"value": 69.28, "unit": "%"}, "co2": {"value": 1414.8, "unit": "ppm"}}}
```

## Prueba 2: Medición válida

- **Datos de entrada:** medición más reciente del sensor (no se encontró la línea ALMACENADO en el log)
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** almacenado: 1 fila(s), una por magnitud, con el mismo `timestamp_utc`
- **Archivo y función:** `app/mqtt/procesador.py` · `procesar_mensaje`; `app/crud/medicion.py` · `crear_mediciones`
- **Explicación:** El payload superó la validación de estructura y las reglas de negocio, y todas sus magnitudes se guardaron en una sola transacción.

**Resultado obtenido:**

```text
Filas en la tabla mediciones:
  id=1508 sensor_magnitud_id=1 (co2) valor=510.6400 timestamp_utc=2026-10-09T01:00:52+00:00
```

## Prueba 3: Sensor inexistente

- **Datos de entrada:** payload de prueba entregado directamente a `procesar_mensaje` (el servicio no publicó este caso durante la recolección)
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** rechazado: `aceptado=False` y ninguna fila guardada
- **Archivo y función:** `app/mqtt/procesador.py` · `validar_negocio`; `app/crud/sensor.py` · `obtener_sensor_por_codigo`
- **Explicación:** El `sensor_id` del payload se busca en `sensores.codigo`. Como no existe, el mensaje se descarta antes de revisar las magnitudes.

**Resultado obtenido:**

```text
payload={"sensor_id": "NO-EXISTE-999", "timestamp": "2000-01-01T00:00:00Z", "measurements": {"co2": {"value": 2650.0, "unit": "ppm"}}}
aceptado=False
motivos=["sensor inexistente: 'NO-EXISTE-999'"]
filas guardadas con ese timestamp=0
```

## Prueba 4: Unidad incorrecta

- **Datos de entrada:** payload de prueba entregado directamente a `procesar_mensaje` (el servicio no publicó este caso durante la recolección)
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** rechazado: `aceptado=False` y ninguna fila guardada
- **Archivo y función:** `app/mqtt/procesador.py` · `validar_negocio`
- **Explicación:** La unidad recibida se compara con `sensor_magnitudes.unidad` de esa magnitud. Al no coincidir, se rechaza el payload completo.

**Resultado obtenido:**

```text
payload={"sensor_id": "AQ-001", "timestamp": "2000-01-01T00:00:00Z", "measurements": {"co2": {"value": 2650.0, "unit": "XYZ"}}}
aceptado=False
motivos=["unidad incorrecta en 'co2': llegó 'XYZ', se esperaba 'ppm'"]
filas guardadas con ese timestamp=0
```

## Prueba 5: Tipo de dato incorrecto

- **Datos de entrada:** payload de prueba entregado directamente a `procesar_mensaje` (el servicio no publicó este caso durante la recolección)
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** rechazado: `aceptado=False` y ninguna fila guardada
- **Archivo y función:** `app/schemas/medicion.py` · `LecturaIn` y `PayloadIn`; `app/mqtt/procesador.py` · `validar_estructura`
- **Explicación:** Los schemas usan `strict=True`, así que Pydantic no convierte textos en números. El mensaje se rechaza sin consultar la base.

**Resultado obtenido:**

```text
payload={"sensor_id": "AQ-001", "timestamp": "2000-01-01T00:00:00Z", "measurements": {"co2": {"value": "2650.0", "unit": "ppm"}}}
aceptado=False
motivos=['measurements.co2.value: Input should be a valid number']
filas guardadas con ese timestamp=0
```

## Prueba 6: Magnitud incorrecta

- **Datos de entrada:** payload de prueba entregado directamente a `procesar_mensaje` (el servicio no publicó este caso durante la recolección)
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** rechazado: `aceptado=False` y ninguna fila guardada
- **Archivo y función:** `app/mqtt/procesador.py` · `validar_negocio`; `app/crud/sensor_magnitud.py` · `obtener_por_sensor_y_magnitud`
- **Explicación:** Se busca la pareja sensor y magnitud en `sensor_magnitudes`. Si no existe, el sensor no mide esa magnitud y el payload se rechaza.

**Resultado obtenido:**

```text
payload={"sensor_id": "AQ-001", "timestamp": "2000-01-01T00:00:00Z", "measurements": {"magnitud_falsa": {"value": 1.0, "unit": "x"}}}
aceptado=False
motivos=["magnitud no configurada para el sensor: 'magnitud_falsa'"]
filas guardadas con ese timestamp=0
```

## Prueba 7: Timestamp inválido

- **Datos de entrada:** payload de prueba entregado directamente a `procesar_mensaje` (el servicio no publicó este caso durante la recolección)
- **Código HTTP:** no aplica (MQTT)
- **Registro almacenado o rechazado:** rechazado: `aceptado=False` y ninguna fila guardada
- **Archivo y función:** `app/schemas/medicion.py` · `PayloadIn.timestamp`; `app/mqtt/procesador.py` · `validar_estructura`
- **Explicación:** El campo es `AwareDatetime`: exige una fecha ISO 8601 válida y con zona horaria.

**Resultado obtenido:**

```text
payload={"sensor_id": "AQ-001", "timestamp": "2026-13-45T99:99:99Z", "measurements": {"co2": {"value": 2650.0, "unit": "ppm"}}}
aceptado=False
motivos=['timestamp: Input should be a valid datetime, month value is outside expected range of 1-12']
filas guardadas con ese timestamp=0
```

## Prueba 8: Consulta por ID existente

- **Datos de entrada:** `GET /sensores/1`; `GET /mediciones/1508`
- **Código HTTP:** 200, 200
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/sensor.py` · `obtener_sensor`; `app/api/medicion.py` · `obtener_medicion`
- **Explicación:** La ruta busca por clave primaria en la capa CRUD y devuelve el recurso con el schema de salida.

**Resultado obtenido:**

```text
GET /sensores/1
HTTP 200

{
  "codigo": "AQ-001",
  "nombre": "Calidad de aire interior",
  "categoria": "AIRE",
  "ubicacion": "Biblioteca - sala de lectura",
  "activo": true,
  "id": 1,
  "fecha_registro": "2026-10-07 11:42:11"
}
```

```text
GET /mediciones/1508
HTTP 200

{
  "id": 1508,
  "sensor_magnitud_id": 1,
  "magnitud": "co2",
  "unidad": "ppm",
  "valor": "510.6400",
  "timestamp_colombia": "2026-10-08 20:00:52",
  "fecha_recepcion": "2026-10-08 20:00:52"
}
```

## Prueba 9: Consulta por ID inexistente

- **Datos de entrada:** `GET /sensores/999999`; `GET /mediciones/999999999`
- **Código HTTP:** 404, 404
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/sensor.py` · `obtener_sensor`; `app/api/medicion.py` · `obtener_medicion`
- **Explicación:** Cuando el CRUD devuelve `None`, la ruta lanza `HTTPException(404)` con un mensaje claro.

**Resultado obtenido:**

```text
GET /sensores/999999
HTTP 404

{
  "detail": "Sensor con ID 999999 no encontrado"
}
```

```text
GET /mediciones/999999999
HTTP 404

{
  "detail": "Medición con ID 999999999 no encontrada"
}
```

## Prueba 10: Consulta histórica

- **Datos de entrada:** `GET /sensores/1/mediciones`
- **Código HTTP:** 200
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/medicion.py` · `listar_mediciones_del_sensor`; `app/crud/medicion.py` · `listar_por_sensor`
- **Explicación:** Devuelve las mediciones del sensor, de la más reciente a la más antigua, con la hora de Colombia.

**Resultado obtenido:**

```text
GET /sensores/1/mediciones
HTTP 200

[
  {
    "id": 1508,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "510.6400",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  },
  {
    "id": 1507,
    "sensor_magnitud_id": 2,
    "magnitud": "humidity",
    "unidad": "%",
    "valor": "38.1200",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  },
  {
    "id": 1506,
    "sensor_magnitud_id": 3,
    "magnitud": "temperature",
    "unidad": "C",
    "valor": "30.0100",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  }
]
... 100 elementos en total; se muestran los primeros 3
```

## Prueba 11: Consulta por rango de fechas

- **Datos de entrada:** `GET /sensores/1/mediciones?desde=2026-10-07T11:25:30&hasta=2026-10-08T03:43:11`
- **Código HTTP:** 200
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/medicion.py` · `a_utc`; `app/crud/medicion.py` · `listar_por_sensor`
- **Explicación:** Las fechas sin zona se interpretan como hora de Colombia, se convierten a UTC y se filtran con `timestamp_utc >= desde` y `timestamp_utc <= hasta`.

**Resultado obtenido:**

```text
GET /sensores/1/mediciones?desde=2026-10-07T11:25:30&hasta=2026-10-08T03:43:11
HTTP 200

[
  {
    "id": 1001,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "2650.0000",
    "timestamp_colombia": "2026-10-07 11:25:30",
    "fecha_recepcion": "2026-10-08 19:45:07"
  }
]
```

## Prueba 12: Rango desde > hasta

- **Datos de entrada:** `GET /sensores/1/mediciones?desde=2026-10-08T20:00:52&hasta=2026-10-07T11:25:30`
- **Código HTTP:** 400
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/medicion.py` · `listar_mediciones_del_sensor`
- **Explicación:** La ruta compara ambas fechas y responde 400 antes de consultar la base.

**Resultado obtenido:**

```text
GET /sensores/1/mediciones?desde=2026-10-08T20:00:52&hasta=2026-10-07T11:25:30
HTTP 400

{
  "detail": "El parámetro 'desde' no puede ser mayor que 'hasta'"
}
```

## Prueba 13: Validación HTTP incorrecta

- **Datos de entrada:** `GET /sensores/abc`; `GET /sensores/1/mediciones?limit=0`; `GET /sensores/1/mediciones?desde=ayer`
- **Código HTTP:** 422, 422, 422
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/sensor.py` · tipo `IdEntero`; `app/api/medicion.py` · parámetros `limit` y `desde`
- **Explicación:** FastAPI valida los tipos y rangos declarados y responde 422 sin ejecutar la función de la ruta.

**Resultado obtenido:**

```text
GET /sensores/abc
HTTP 422

{
  "detail": [
    {
      "type": "int_parsing",
      "loc": [
        "path",
        "id"
      ],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "abc"
    }
  ]
}
```

```text
GET /sensores/1/mediciones?limit=0
HTTP 422

{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": [
        "query",
        "limit"
      ],
      "msg": "Input should be greater than or equal to 1",
      "input": "0",
      "ctx": {
        "ge": 1
      }
    }
  ]
}
```

```text
GET /sensores/1/mediciones?desde=ayer
HTTP 422

{
  "detail": [
    {
      "type": "datetime_from_date_parsing",
      "loc": [
        "query",
        "desde"
      ],
      "msg": "Input should be a valid datetime or date, input is too short",
      "input": "ayer",
      "ctx": {
        "error": "input is too short"
      }
    }
  ]
}
```

## Prueba 14: Última medición

- **Datos de entrada:** `GET /sensores/1/ultima-medicion`
- **Código HTTP:** 200
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/medicion.py` · `obtener_ultima_medicion`; `app/crud/medicion.py` · `ultima_por_sensor`
- **Explicación:** Ordena por `timestamp_utc` descendente y toma una fila. La consulta directa a la base da como más reciente la medición id=1508 (2026-10-08 20:00:52); coincide con la respuesta.

**Resultado obtenido:**

```text
GET /sensores/1/ultima-medicion
HTTP 200

{
  "id": 1508,
  "sensor_magnitud_id": 1,
  "magnitud": "co2",
  "unidad": "ppm",
  "valor": "510.6400",
  "timestamp_colombia": "2026-10-08 20:00:52",
  "fecha_recepcion": "2026-10-08 20:00:52"
}
```

## Prueba 15: Últimas N mediciones

- **Datos de entrada:** `GET /sensores/1/mediciones?limit=5`
- **Código HTTP:** 200
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/medicion.py` · parámetro `limit`; `app/crud/medicion.py` · `listar_por_sensor`
- **Explicación:** `limit=5` devuelve como máximo las cinco mediciones más recientes.

**Resultado obtenido:**

```text
GET /sensores/1/mediciones?limit=5
HTTP 200

[
  {
    "id": 1508,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "510.6400",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  },
  {
    "id": 1507,
    "sensor_magnitud_id": 2,
    "magnitud": "humidity",
    "unidad": "%",
    "valor": "38.1200",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  },
  {
    "id": 1506,
    "sensor_magnitud_id": 3,
    "magnitud": "temperature",
    "unidad": "C",
    "valor": "30.0100",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  }
]
... 5 elementos en total; se muestran los primeros 3
```

## Prueba 16: Filtro por magnitud

- **Datos de entrada:** `GET /sensores/1/mediciones?magnitud=co2`; `GET /sensores/1/mediciones?magnitud=co2&desde=2026-10-07T11:25:30&hasta=2026-10-08T03:43:11&limit=5`
- **Código HTTP:** 200, 200
- **Registro almacenado o rechazado:** no aplica, es una consulta
- **Archivo y función:** `app/api/medicion.py` · `validar_sensor_y_magnitud`; `app/crud/medicion.py` · `listar_por_sensor`
- **Explicación:** Cada filtro se agrega a la consulta solo si llegó, por eso se pueden combinar.

**Resultado obtenido:**

```text
GET /sensores/1/mediciones?magnitud=co2
HTTP 200

[
  {
    "id": 1508,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "510.6400",
    "timestamp_colombia": "2026-10-08 20:00:52",
    "fecha_recepcion": "2026-10-08 20:00:52"
  },
  {
    "id": 1505,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "529.5900",
    "timestamp_colombia": "2026-10-08 20:00:47",
    "fecha_recepcion": "2026-10-08 20:00:47"
  },
  {
    "id": 1502,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "698.1400",
    "timestamp_colombia": "2026-10-08 20:00:42",
    "fecha_recepcion": "2026-10-08 20:00:42"
  }
]
... 100 elementos en total; se muestran los primeros 3
```

```text
GET /sensores/1/mediciones?magnitud=co2&desde=2026-10-07T11:25:30&hasta=2026-10-08T03:43:11&limit=5
HTTP 200

[
  {
    "id": 1001,
    "sensor_magnitud_id": 1,
    "magnitud": "co2",
    "unidad": "ppm",
    "valor": "2650.0000",
    "timestamp_colombia": "2026-10-07 11:25:30",
    "fecha_recepcion": "2026-10-08 19:45:07"
  }
]
```

## Prueba 17: Claves foráneas

- **Datos de entrada:** JOIN de las tres tablas mediante ORM y `GET /sensores/1/magnitudes`
- **Código HTTP:** 200
- **Registro almacenado o rechazado:** cada medición referencia una fila de `sensor_magnitudes`, y esta una de `sensores`
- **Archivo y función:** `app/models/sensor_magnitud.py` · `sensor_id` y `relationship`; `app/models/medicion.py` · `sensor_magnitud_id` y `relationship`
- **Explicación:** Las dos `ForeignKey` reproducen las de `data-model.md` (`ON UPDATE CASCADE ON DELETE RESTRICT`) y los `relationship` permiten navegar de la medición a su magnitud y a su sensor.

**Resultado obtenido:**

```text
mediciones.id | sensor_magnitud_id (FK) | magnitud | sensor_id (FK) | sensores.codigo
1508 | 1 | co2 | 1 | AQ-001
1507 | 2 | humidity | 1 | AQ-001
1506 | 3 | temperature | 1 | AQ-001
```

```text
GET /sensores/1/magnitudes
HTTP 200

[
  {
    "magnitud": "co2",
    "unidad": "ppm",
    "valor_minimo": "300.0000",
    "valor_maximo": "5000.0000",
    "id": 1,
    "sensor_id": 1
  },
  {
    "magnitud": "humidity",
    "unidad": "%",
    "valor_minimo": "0.0000",
    "valor_maximo": "100.0000",
    "id": 2,
    "sensor_id": 1
  },
  {
    "magnitud": "temperature",
    "unidad": "C",
    "valor_minimo": "10.0000",
    "valor_maximo": "45.0000",
    "id": 3,
    "sensor_id": 1
  }
]
```

## Prueba 18: Separación de responsabilidades

- **Datos de entrada:** estructura de la carpeta `app/`
- **Código HTTP:** no aplica
- **Registro almacenado o rechazado:** no aplica
- **Archivo y función:** toda la carpeta `app/`
- **Explicación:** Cada tabla tiene un archivo en `schemas/`, `models/`, `crud/` y `api/`. Las rutas y el consumidor MQTT no ejecutan consultas: llaman a `crud/`, que es la única capa que usa el ORM.

**Resultado obtenido:**

```text
app/
├── api/
│   ├── __init__.py
│   ├── medicion.py
│   ├── sensor.py
│   └── sensor_magnitud.py
├── crud/
│   ├── __init__.py
│   ├── medicion.py
│   ├── sensor.py
│   └── sensor_magnitud.py
├── database/
│   └── connection.py
├── models/
│   ├── __init__.py
│   ├── medicion.py
│   ├── sensor.py
│   └── sensor_magnitud.py
├── mqtt/
│   ├── __init__.py
│   ├── client.py
│   └── procesador.py
├── schemas/
│   ├── __init__.py
│   ├── fechas.py
│   ├── medicion.py
│   ├── sensor.py
│   └── sensor_magnitud.py
└── main.py
```
