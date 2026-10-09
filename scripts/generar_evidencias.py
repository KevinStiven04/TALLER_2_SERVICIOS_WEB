"""Genera evidencias/evidencias.md con las 18 pruebas de la Actividad 6.

Antes de ejecutarlo:
  1. Recolecta datos al menos 20 minutos (debe existir logs/mqtt.log).
  2. Deja la API encendida en otra terminal:  uvicorn app.main:app

Uso: python -m scripts.generar_evidencias
"""

import json
import logging
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.database.connection import SessionLocal
from app.models import Medicion, Sensor, SensorMagnitud
from app.mqtt.procesador import procesar_mensaje
from app.schemas.fechas import ZONA_COLOMBIA, a_hora_colombia
from scripts.probar_validaciones import CODIGO, TOPICO, construir_casos

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
LOG = Path("logs/mqtt.log")
CARPETA = Path("evidencias")
SALIDA = CARPETA / "evidencias.md"

# Los casos locales no deben mezclarse con el registro real del consumidor.
logging.getLogger("mqtt").addHandler(logging.NullHandler())
logging.getLogger("mqtt").propagate = False


# ---------------------------------------------------------------- utilidades

def http_get(ruta: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(API_URL + ruta, timeout=15) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")
    except urllib.error.URLError as error:
        raise SystemExit(
            f"No se pudo conectar con la API en {API_URL}.\n"
            f"Enciéndela en otra terminal con: uvicorn app.main:app\nDetalle: {error.reason}"
        )


def resumir(cuerpo: str, maximo: int = 3) -> str:
    """JSON legible; las listas largas se recortan a los primeros elementos."""
    try:
        datos = json.loads(cuerpo)
    except json.JSONDecodeError:
        return cuerpo
    nota = ""
    if isinstance(datos, list) and len(datos) > maximo:
        nota = f"\n... {len(datos)} elementos en total; se muestran los primeros {maximo}"
        datos = datos[:maximo]
    return json.dumps(datos, indent=2, ensure_ascii=False) + nota


def bloque(texto: str, lenguaje: str = "text") -> str:
    return f"```{lenguaje}\n{texto}\n```"


def prueba(numero, titulo, entrada, resultado, codigo_http, registro, implementacion, explicacion) -> str:
    return "\n".join([
        f"## Prueba {numero}: {titulo}",
        "",
        f"- **Datos de entrada:** {entrada}",
        f"- **Código HTTP:** {codigo_http}",
        f"- **Registro almacenado o rechazado:** {registro}",
        f"- **Archivo y función:** {implementacion}",
        f"- **Explicación:** {explicacion}",
        "",
        "**Resultado obtenido:**",
        "",
        resultado,
        "",
    ])


def prueba_http(numero, titulo, rutas, esperado, implementacion, explicacion, estados) -> str:
    partes, codigos = [], []
    for ruta in rutas:
        codigo, cuerpo = http_get(ruta)
        codigos.append(codigo)
        partes.append(bloque(f"GET {ruta}\nHTTP {codigo}\n\n{resumir(cuerpo)}"))
    correcto = all(codigo == esperado for codigo in codigos)
    estados[numero] = "OK" if correcto else f"REVISAR (se esperaba {esperado})"
    return prueba(
        numero, titulo,
        entrada="; ".join(f"`GET {ruta}`" for ruta in rutas),
        resultado="\n\n".join(partes),
        codigo_http=", ".join(str(codigo) for codigo in codigos),
        registro="no aplica, es una consulta",
        implementacion=implementacion,
        explicacion=explicacion,
    )


def arbol(raiz: Path, prefijo: str = "") -> list[str]:
    hijos = sorted(
        (h for h in raiz.iterdir() if h.name != "__pycache__"),
        key=lambda h: (h.is_file(), h.name),
    )
    lineas = []
    for indice, hijo in enumerate(hijos):
        ultimo = indice == len(hijos) - 1
        lineas.append(f"{prefijo}{'└── ' if ultimo else '├── '}{hijo.name}{'/' if hijo.is_dir() else ''}")
        if hijo.is_dir():
            lineas += arbol(hijo, prefijo + ("    " if ultimo else "│   "))
    return lineas


def iso_local(fecha: datetime) -> str:
    """Fecha en hora de Colombia y formato ISO, como la reciben los filtros."""
    return fecha.astimezone(ZONA_COLOMBIA).strftime("%Y-%m-%dT%H:%M:%S")


# ------------------------------------------------------------------ registro

lineas_log = LOG.read_text(encoding="utf-8").splitlines() if LOG.exists() else []


def mensajes_reales(patron: str) -> list[tuple[str, str]]:
    """Pares (línea RECIBIDO, línea de resultado) de mensajes que llegaron por MQTT."""
    pares = []
    for anterior, actual in zip(lineas_log, lineas_log[1:]):
        if "RECIBIDO |" in anterior and re.search(patron, actual):
            pares.append((anterior, actual))
    return pares


RECHAZOS = [
    (3, "Sensor inexistente", r"RECHAZADO negocio \| .*sensor inexistente", "sensor_inexistente",
     "`app/mqtt/procesador.py` · `validar_negocio`; `app/crud/sensor.py` · `obtener_sensor_por_codigo`",
     "El `sensor_id` del payload se busca en `sensores.codigo`. Como no existe, el mensaje se descarta "
     "antes de revisar las magnitudes."),
    (4, "Unidad incorrecta", r"RECHAZADO negocio \| .*unidad incorrecta", "unidad_incorrecta",
     "`app/mqtt/procesador.py` · `validar_negocio`",
     "La unidad recibida se compara con `sensor_magnitudes.unidad` de esa magnitud. Al no coincidir, "
     "se rechaza el payload completo."),
    (5, "Tipo de dato incorrecto", r"RECHAZADO estructura \| .*Input should be a valid (number|string|dictionary)",
     "tipo_incorrecto",
     "`app/schemas/medicion.py` · `LecturaIn` y `PayloadIn`; `app/mqtt/procesador.py` · `validar_estructura`",
     "Los schemas usan `strict=True`, así que Pydantic no convierte textos en números. El mensaje se "
     "rechaza sin consultar la base."),
    (6, "Magnitud incorrecta", r"RECHAZADO negocio \| .*magnitud no configurada", "magnitud_incorrecta",
     "`app/mqtt/procesador.py` · `validar_negocio`; `app/crud/sensor_magnitud.py` · `obtener_por_sensor_y_magnitud`",
     "Se busca la pareja sensor y magnitud en `sensor_magnitudes`. Si no existe, el sensor no mide esa "
     "magnitud y el payload se rechaza."),
    (7, "Timestamp inválido", r"RECHAZADO estructura \| .*timestamp: ", "timestamp_invalido",
     "`app/schemas/medicion.py` · `PayloadIn.timestamp`; `app/mqtt/procesador.py` · `validar_estructura`",
     "El campo es `AwareDatetime`: exige una fecha ISO 8601 válida y con zona horaria."),
]

FECHA_CASOS_LOCALES = datetime(2000, 1, 1, tzinfo=timezone.utc)


def main() -> None:
    CARPETA.mkdir(exist_ok=True)
    secciones: list[str] = []
    estados: dict[int, str] = {}

    with SessionLocal() as db:
        sensor = db.scalars(select(Sensor).where(Sensor.codigo == CODIGO)).first()
        if sensor is None:
            raise SystemExit(f"No existe el sensor '{CODIGO}'. Revisa MQTT_TOPIC en .env")

        del_sensor = (
            select(Medicion).join(Medicion.sensor_magnitud).where(SensorMagnitud.sensor_id == sensor.id)
        )
        total, primera, ultima = db.execute(
            select(func.count(Medicion.id), func.min(Medicion.timestamp_utc), func.max(Medicion.timestamp_utc))
            .join(Medicion.sensor_magnitud)
            .where(SensorMagnitud.sensor_id == sensor.id)
        ).one()
        if not total:
            raise SystemExit("El sensor aún no tiene mediciones. Recolecta datos antes de generar evidencias.")
        minutos = (ultima - primera).total_seconds() / 60
        magnitudes = sensor.magnitudes
        magnitud = magnitudes[0].magnitud
        magnitud_url = urllib.parse.quote(magnitud)
        medicion_reciente = db.scalars(del_sensor.order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc())).first()

        # ------------------------------------------------- 1. Recepción MQTT
        recibidos = [linea for linea in lineas_log if "RECIBIDO |" in linea]
        conexion = [linea for linea in lineas_log if "Conectado a" in linea][:1]
        estados[1] = "OK" if recibidos else "REVISAR (no hay logs/mqtt.log)"
        secciones.append(prueba(
            1, "Recepción MQTT",
            entrada=f"suscripción al tópico `{TOPICO}`",
            resultado=bloque("\n".join(conexion + recibidos[:3]) or "Sin registros: ejecuta el consumidor primero."),
            codigo_http="no aplica (MQTT)",
            registro=f"{len(recibidos)} mensajes recibidos según `logs/mqtt.log`",
            implementacion="`app/mqtt/client.py` · `on_connect` y `on_message`",
            explicacion="El cliente se suscribe en `on_connect` y cada mensaje llega a `on_message`, "
                        "que lo registra y lo entrega al procesador.",
        ))

        # ------------------------------------------------ 2. Medición válida
        almacenados = mensajes_reales(r"ALMACENADO \|")
        if almacenados:
            recibido, guardado = almacenados[0]
            ids = [int(x) for x in re.findall(r"\d+", guardado.split("ids=")[-1])]
            entrada = "payload recibido por MQTT (primera línea del resultado)"
            texto = [recibido, guardado, ""]
        else:
            ids = [medicion_reciente.id]
            entrada = "medición más reciente del sensor (no se encontró la línea ALMACENADO en el log)"
            texto = []
        filas = db.scalars(select(Medicion).where(Medicion.id.in_(ids)).order_by(Medicion.id)).all()
        texto.append("Filas en la tabla mediciones:")
        texto += [
            f"  id={f.id} sensor_magnitud_id={f.sensor_magnitud_id} ({f.magnitud}) valor={f.valor} "
            f"timestamp_utc={f.timestamp_utc.astimezone(timezone.utc).isoformat()}"
            for f in filas
        ]
        estados[2] = "OK" if filas else "REVISAR"
        secciones.append(prueba(
            2, "Medición válida", entrada, bloque("\n".join(texto)),
            codigo_http="no aplica (MQTT)",
            registro=f"almacenado: {len(filas)} fila(s), una por magnitud, con el mismo `timestamp_utc`",
            implementacion="`app/mqtt/procesador.py` · `procesar_mensaje`; `app/crud/medicion.py` · `crear_mediciones`",
            explicacion="El payload superó la validación de estructura y las reglas de negocio, y todas "
                        "sus magnitudes se guardaron en una sola transacción.",
        ))

        # ------------------------------------------- 3 a 7. Mensajes rechazados
        casos = construir_casos(db)
        for numero, titulo, patron, caso, implementacion, explicacion in RECHAZOS:
            reales = mensajes_reales(patron)
            if reales:
                recibido, rechazo = reales[0]
                origen = "mensaje publicado por el servicio MQTT en el tópico asignado"
                texto = f"{recibido}\n{rechazo}"
                registro = "rechazado: después del mensaje no hay línea `ALMACENADO` en el registro"
                estados[numero] = "OK"
            else:
                crudo = casos[caso].replace(b"2026-10-07T16:25:30Z", b"2000-01-01T00:00:00Z")
                resultado = procesar_mensaje(db, crudo, TOPICO)
                guardadas = db.scalar(
                    select(func.count(Medicion.id)).join(Medicion.sensor_magnitud)
                    .where(SensorMagnitud.sensor_id == sensor.id, Medicion.timestamp_utc == FECHA_CASOS_LOCALES)
                )
                origen = ("payload de prueba entregado directamente a `procesar_mensaje` "
                          "(el servicio no publicó este caso durante la recolección)")
                texto = (f"payload={crudo.decode()}\naceptado={resultado.aceptado}\n"
                         f"motivos={resultado.motivos}\nfilas guardadas con ese timestamp={guardadas}")
                registro = "rechazado: `aceptado=False` y ninguna fila guardada"
                estados[numero] = "OK (caso local)" if not resultado.aceptado and not guardadas else "REVISAR"
            secciones.append(prueba(
                numero, titulo, origen, bloque(texto),
                codigo_http="no aplica (MQTT)", registro=registro,
                implementacion=implementacion, explicacion=explicacion,
            ))

        # ------------------------------------------------- 8 a 16. Consultas HTTP
        sid = sensor.id
        mitad = primera + (ultima - primera) / 2
        rango = f"desde={iso_local(primera)}&hasta={iso_local(mitad)}"
        invertido = f"desde={iso_local(ultima)}&hasta={iso_local(primera)}"

        secciones.append(prueba_http(
            8, "Consulta por ID existente", [f"/sensores/{sid}", f"/mediciones/{medicion_reciente.id}"], 200,
            "`app/api/sensor.py` · `obtener_sensor`; `app/api/medicion.py` · `obtener_medicion`",
            "La ruta busca por clave primaria en la capa CRUD y devuelve el recurso con el schema de salida.",
            estados))
        secciones.append(prueba_http(
            9, "Consulta por ID inexistente", ["/sensores/999999", "/mediciones/999999999"], 404,
            "`app/api/sensor.py` · `obtener_sensor`; `app/api/medicion.py` · `obtener_medicion`",
            "Cuando el CRUD devuelve `None`, la ruta lanza `HTTPException(404)` con un mensaje claro.",
            estados))
        secciones.append(prueba_http(
            10, "Consulta histórica", [f"/sensores/{sid}/mediciones"], 200,
            "`app/api/medicion.py` · `listar_mediciones_del_sensor`; `app/crud/medicion.py` · `listar_por_sensor`",
            "Devuelve las mediciones del sensor, de la más reciente a la más antigua, con la hora de Colombia.",
            estados))
        secciones.append(prueba_http(
            11, "Consulta por rango de fechas", [f"/sensores/{sid}/mediciones?{rango}"], 200,
            "`app/api/medicion.py` · `a_utc`; `app/crud/medicion.py` · `listar_por_sensor`",
            "Las fechas sin zona se interpretan como hora de Colombia, se convierten a UTC y se filtran "
            "con `timestamp_utc >= desde` y `timestamp_utc <= hasta`.",
            estados))
        secciones.append(prueba_http(
            12, "Rango desde > hasta", [f"/sensores/{sid}/mediciones?{invertido}"], 400,
            "`app/api/medicion.py` · `listar_mediciones_del_sensor`",
            "La ruta compara ambas fechas y responde 400 antes de consultar la base.",
            estados))
        secciones.append(prueba_http(
            13, "Validación HTTP incorrecta",
            ["/sensores/abc", f"/sensores/{sid}/mediciones?limit=0", f"/sensores/{sid}/mediciones?desde=ayer"], 422,
            "`app/api/sensor.py` · tipo `IdEntero`; `app/api/medicion.py` · parámetros `limit` y `desde`",
            "FastAPI valida los tipos y rangos declarados y responde 422 sin ejecutar la función de la ruta.",
            estados))

        codigo14, cuerpo14 = http_get(f"/sensores/{sid}/ultima-medicion")
        coincide = codigo14 == 200 and json.loads(cuerpo14).get("id") == medicion_reciente.id
        secciones.append(prueba_http(
            14, "Última medición", [f"/sensores/{sid}/ultima-medicion"], 200,
            "`app/api/medicion.py` · `obtener_ultima_medicion`; `app/crud/medicion.py` · `ultima_por_sensor`",
            f"Ordena por `timestamp_utc` descendente y toma una fila. La consulta directa a la base da como "
            f"más reciente la medición id={medicion_reciente.id} ({a_hora_colombia(medicion_reciente.timestamp_utc)}); "
            f"{'coincide con la respuesta' if coincide else 'llegaron mediciones nuevas entre ambas consultas'}.",
            estados))
        secciones.append(prueba_http(
            15, "Últimas N mediciones", [f"/sensores/{sid}/mediciones?limit=5"], 200,
            "`app/api/medicion.py` · parámetro `limit`; `app/crud/medicion.py` · `listar_por_sensor`",
            "`limit=5` devuelve como máximo las cinco mediciones más recientes.",
            estados))
        secciones.append(prueba_http(
            16, "Filtro por magnitud",
            [f"/sensores/{sid}/mediciones?magnitud={magnitud_url}",
             f"/sensores/{sid}/mediciones?magnitud={magnitud_url}&{rango}&limit=5"], 200,
            "`app/api/medicion.py` · `validar_sensor_y_magnitud`; `app/crud/medicion.py` · `listar_por_sensor`",
            "Cada filtro se agrega a la consulta solo si llegó, por eso se pueden combinar.",
            estados))

        # ------------------------------------------------ 17. Claves foráneas
        enlazadas = db.execute(
            select(Medicion.id, Medicion.sensor_magnitud_id, SensorMagnitud.magnitud,
                   SensorMagnitud.sensor_id, Sensor.codigo)
            .join(Medicion.sensor_magnitud).join(SensorMagnitud.sensor)
            .where(Sensor.id == sid).order_by(Medicion.id.desc()).limit(3)
        ).all()
        texto = ["mediciones.id | sensor_magnitud_id (FK) | magnitud | sensor_id (FK) | sensores.codigo"]
        texto += [" | ".join(str(valor) for valor in fila) for fila in enlazadas]
        codigo17, cuerpo17 = http_get(f"/sensores/{sid}/magnitudes")
        estados[17] = "OK" if enlazadas and codigo17 == 200 else "REVISAR"
        secciones.append(prueba(
            17, "Claves foráneas",
            entrada=f"JOIN de las tres tablas mediante ORM y `GET /sensores/{sid}/magnitudes`",
            resultado=bloque("\n".join(texto)) + "\n\n"
                      + bloque(f"GET /sensores/{sid}/magnitudes\nHTTP {codigo17}\n\n{resumir(cuerpo17)}"),
            codigo_http=str(codigo17),
            registro="cada medición referencia una fila de `sensor_magnitudes`, y esta una de `sensores`",
            implementacion="`app/models/sensor_magnitud.py` · `sensor_id` y `relationship`; "
                           "`app/models/medicion.py` · `sensor_magnitud_id` y `relationship`",
            explicacion="Las dos `ForeignKey` reproducen las de `data-model.md` "
                        "(`ON UPDATE CASCADE ON DELETE RESTRICT`) y los `relationship` permiten navegar "
                        "de la medición a su magnitud y a su sensor.",
        ))

    # ------------------------------------- 18. Separación de responsabilidades
    estados[18] = "OK"
    secciones.append(prueba(
        18, "Separación de responsabilidades",
        entrada="estructura de la carpeta `app/`",
        resultado=bloque("app/\n" + "\n".join(arbol(Path("app")))),
        codigo_http="no aplica",
        registro="no aplica",
        implementacion="toda la carpeta `app/`",
        explicacion="Cada tabla tiene un archivo en `schemas/`, `models/`, `crud/` y `api/`. Las rutas y el "
                    "consumidor MQTT no ejecutan consultas: llaman a `crud/`, que es la única capa que usa el ORM.",
    ))

    # ------------------------------------------------------------ documento
    if LOG.exists():
        shutil.copyfile(LOG, CARPETA / "mqtt_log.txt")

    encabezado = [
        "# Evidencias de funcionamiento - Taller 2",
        "",
        f"- **Generado:** {a_hora_colombia(datetime.now(timezone.utc))} (hora de Colombia)",
        f"- **Sensor:** `{CODIGO}` (id {sid})",
        f"- **Tópico:** `{TOPICO}`",
        f"- **Datos recolectados:** {total} mediciones entre {a_hora_colombia(primera)} y "
        f"{a_hora_colombia(ultima)} ({minutos:.1f} minutos)",
        "- **Registro completo del consumidor:** `evidencias/mqtt_log.txt`",
        "",
    ]
    if minutos < 20:
        encabezado += [f"> ATENCIÓN: solo hay {minutos:.1f} minutos de datos. El taller exige al menos 20.", ""]
    encabezado += ["| # | Estado |", "| --- | --- |"]
    encabezado += [f"| {numero} | {estados[numero]} |" for numero in sorted(estados)]
    encabezado.append("")

    SALIDA.write_text("\n".join(encabezado + secciones), encoding="utf-8")
    print(f"Evidencias generadas en {SALIDA}")
    for numero in sorted(estados):
        print(f"  Prueba {numero:>2}: {estados[numero]}")


if __name__ == "__main__":
    main()
