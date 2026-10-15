"""
generar_ranking.py - Lee ranking.txt, ordena las partidas y arma ranking.html.

Se puede usar de dos formas:
  * Desde juego.py, llamando a generar_ranking(abrir=True) al terminar cada partida.
  * Solo, desde la terminal:  python generar_ranking.py
"""

import webbrowser
from datetime import datetime
from html import escape

from datos import CARPETA_PROYECTO, leer_partidas

ARCHIVO_HTML = CARPETA_PROYECTO / "ranking.html"
CANTIDAD_TOP = 10

# Colores de cada fila del top 10, como en los rankings de las recreativas.
COLORES_FILAS = [
    "oro", "plata", "bronce", "cian", "verde",
    "rosa", "amarillo", "naranja", "violeta", "blanco",
]


def ordenar_por_puntaje(partidas):
    """
    Ordena las partidas de mayor a menor puntaje usando ordenamiento por
    inserción. Si dos partidas empatan, queda primero la que se jugó antes
    (el algoritmo es estable porque solo mueve elementos estrictamente menores).
    Devuelve una lista nueva y no modifica la original.
    """
    ordenadas = list(partidas)
    for i in range(1, len(ordenadas)):
        actual = ordenadas[i]
        j = i - 1
        while j >= 0 and ordenadas[j]["puntaje"] < actual["puntaje"]:
            ordenadas[j + 1] = ordenadas[j]
            j -= 1
        ordenadas[j + 1] = actual
    return ordenadas


def texto_posicion(numero):
    """Convierte 1 -> '1ST', 2 -> '2ND', 3 -> '3RD', 4 -> '4TH' (estilo arcade)."""
    if numero == 1:
        return "1ST"
    if numero == 2:
        return "2ND"
    if numero == 3:
        return "3RD"
    return f"{numero}TH"


def armar_filas(top):
    """Arma las filas <tr> de la tabla del ranking."""
    filas = []
    for i, partida in enumerate(top):
        clase = COLORES_FILAS[i % len(COLORES_FILAS)]
        filas.append(
            f'        <tr class="{clase}">\n'
            f'          <td class="pos">{texto_posicion(i + 1)}</td>\n'
            f'          <td class="puntaje">{partida["puntaje"]:06d}</td>\n'
            f'          <td class="nombre">{escape(partida["iniciales"])}</td>\n'
            f'          <td class="fecha">{escape(partida["fecha"])}</td>\n'
            f'        </tr>'
        )

    # Si hay menos de 10 partidas, se completan las filas vacías con guiones.
    for i in range(len(top), CANTIDAD_TOP):
        filas.append(
            f'        <tr class="vacia">\n'
            f'          <td class="pos">{texto_posicion(i + 1)}</td>\n'
            f'          <td class="puntaje">------</td>\n'
            f'          <td class="nombre">---</td>\n'
            f'          <td class="fecha">----------</td>\n'
            f'        </tr>'
        )
    return "\n".join(filas)


def armar_html(top, total_partidas):
    """Devuelve el contenido completo de ranking.html como texto."""
    actualizado = datetime.now().strftime("%d/%m/%Y %H:%M")
    if top:
        record = f'{top[0]["puntaje"]:06d}'
        campeon = escape(top[0]["iniciales"])
    else:
        record = "000000"
        campeon = "---"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ranking - Dino Runner</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="estilos.css">
</head>
<body>
  <main class="pantalla">
    <header>
      <p class="hi-score">HI-SCORE <span>{record}</span> {campeon}</p>
      <h1>DINO RUNNER</h1>
      <h2>BEST 10 PLAYERS</h2>
    </header>

    <table class="ranking">
      <thead>
        <tr>
          <th>RANK</th>
          <th>SCORE</th>
          <th>NAME</th>
          <th class="fecha">FECHA</th>
        </tr>
      </thead>
      <tbody>
{armar_filas(top)}
      </tbody>
    </table>

    <footer>
      <p class="parpadeo">INSERT COIN</p>
      <p class="info">PARTIDAS JUGADAS: {total_partidas} &middot; ACTUALIZADO: {actualizado}</p>
    </footer>
  </main>
</body>
</html>
"""


def generar_ranking(abrir=False):
    """
    Lee todas las partidas, toma el top 10 y escribe ranking.html.
    Si abrir es True, abre la página en el navegador predeterminado.
    Devuelve la ruta del archivo generado.
    """
    partidas = leer_partidas()
    top = ordenar_por_puntaje(partidas)[:CANTIDAD_TOP]

    with open(ARCHIVO_HTML, "w", encoding="utf-8") as f:
        f.write(armar_html(top, len(partidas)))

    if abrir:
        webbrowser.open(ARCHIVO_HTML.as_uri())
    return ARCHIVO_HTML


if __name__ == "__main__":
    ruta = generar_ranking(abrir=True)
    print(f"Ranking generado en: {ruta}")
