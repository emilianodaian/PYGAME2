"""
datos.py - Guardado y lectura de las partidas en ranking.txt.

Cada línea de ranking.txt representa una partida con el formato:
    INICIALES;PUNTAJE;FECHA
Por ejemplo:
    ABC;1234;2026-10-15 18:30

El archivo se abre en modo "a" (append) para que cada partida nueva se
agregue al final y nunca se pierdan las anteriores.
"""

from datetime import datetime
from pathlib import Path

# Carpeta donde está este archivo: así los datos se guardan siempre junto
# al proyecto, sin importar desde qué carpeta se ejecute el juego.
CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_RANKING = CARPETA_PROYECTO / "ranking.txt"
SEPARADOR = ";"


def guardar_resultado(iniciales, puntaje, archivo=ARCHIVO_RANKING):
    """Agrega una partida al final de ranking.txt (no sobreescribe)."""
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    linea = f"{iniciales.upper()}{SEPARADOR}{int(puntaje)}{SEPARADOR}{fecha}\n"
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(linea)


def leer_partidas(archivo=ARCHIVO_RANKING):
    """
    Lee ranking.txt y devuelve una lista de diccionarios:
        [{"iniciales": "ABC", "puntaje": 1234, "fecha": "2026-10-15 18:30"}, ...]
    Las líneas vacías o mal formadas se ignoran para que un error en el
    archivo no rompa el juego.
    """
    partidas = []
    if not archivo.exists():
        return partidas

    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea == "":
                continue

            campos = linea.split(SEPARADOR)
            if len(campos) != 3:
                continue

            iniciales, puntaje, fecha = campos
            if not puntaje.isdigit():
                continue

            partidas.append({
                "iniciales": iniciales.upper()[:3],
                "puntaje": int(puntaje),
                "fecha": fecha,
            })
    return partidas


def obtener_record(archivo=ARCHIVO_RANKING):
    """Devuelve el puntaje más alto guardado (0 si todavía no hay partidas)."""
    record = 0
    for partida in leer_partidas(archivo):
        if partida["puntaje"] > record:
            record = partida["puntaje"]
    return record
