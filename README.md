# Dino Runner – Proyecto Final (Pygame + HTML/CSS)

Corredor infinito estilo "dinosaurio de Chrome". Al terminar cada partida se piden las
iniciales, se guarda el resultado en `ranking.txt` y se genera/abre `ranking.html`.

## Ejecutar

```
pip install -r requirements.txt
python juego.py
```

Controles: **ESPACIO / ↑** saltar · **flechas + ENTER** iniciales · **F12** captura · **ESC** salir.

## Archivos

| Archivo | Qué hace |
|---|---|
| `juego.py` | Juego en Pygame: game loop, física, obstáculos, puntaje, pantallas y sonidos |
| `datos.py` | Guarda y lee las partidas de `ranking.txt` |
| `generar_ranking.py` | Ordena las partidas y genera `ranking.html` (top 10) |
| `estilos.css` | Estética arcade del ranking |
| `ranking.txt` | Una línea por partida: `INICIALES;PUNTAJE;FECHA` |
| `informe/informe.html` | Documento explicativo (imprimir a PDF desde el navegador) |
