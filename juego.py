"""
juego.py - Corredor infinito estilo "dinosaurio de Chrome" hecho con Pygame.

Controles:
    ESPACIO / FLECHA ARRIBA  -> saltar (si se suelta antes, el salto es más bajo)
    Pantalla de iniciales    -> flechas para elegir letras, ENTER para confirmar
    F12                      -> guardar una captura de pantalla en /capturas
    ESC                      -> salir

Flujo de pantallas (estados):
    "inicio" -> "jugando" -> "choque" -> "iniciales" -> "fin" -> "jugando" ...
"""

import random
import sys
from array import array
from datetime import datetime

import pygame

from datos import CARPETA_PROYECTO, guardar_resultado, leer_partidas, obtener_record
from generar_ranking import generar_ranking, ordenar_por_puntaje

# ----------------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------------
ANCHO = 900
ALTO = 400
FPS = 60
SUELO_Y = 320                 # coordenada y de la línea del suelo

# Física del salto (unidades en píxeles y segundos)
GRAVEDAD = 2600               # aceleración hacia abajo (px/s²)
FUERZA_SALTO = -900           # velocidad inicial del salto (negativa = hacia arriba)
CORTE_SALTO = -350            # velocidad máxima de subida si se suelta la tecla

# Velocidad del juego (dificultad creciente)
VELOCIDAD_INICIAL = 420       # px/s
ACELERACION = 10              # cuánto aumenta la velocidad por cada segundo
VELOCIDAD_MAXIMA = 1100

PUNTOS_POR_PIXEL = 1 / 40     # el puntaje crece con la distancia recorrida
TIEMPO_CHOQUE = 0.8           # segundos que se congela la pantalla al chocar

ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CARPETA_CAPTURAS = CARPETA_PROYECTO / "capturas"

# Colores (R, G, B)
COLOR_FONDO = (83, 77, 125)
COLOR_SUELO = (230, 225, 255)
COLOR_PIEDRITAS = (170, 165, 210)
COLOR_NUBE = (120, 114, 168)
COLOR_DINO = (120, 230, 140)
COLOR_CACTUS = (255, 190, 80)
COLOR_PAJARO = (255, 110, 150)
COLOR_TEXTO = (245, 245, 255)
COLOR_RESALTADO = (255, 225, 77)
COLOR_ROJO = (255, 80, 80)
COLOR_APAGADO = (160, 155, 200)

# ----------------------------------------------------------------------------
# Sprites en "pixel art": cada '#' es un píxel grande del dibujo
# ----------------------------------------------------------------------------
TAMANIO_PIXEL = 3

DINO_CUERPO = [
    "          ######",
    "         ## #####",
    "         ########",
    "         ########",
    "         ####",
    "         #######",
    "#       #####",
    "##    ########",
    "###  ########",
    "############ #",
    " ##########",
    "  ########",
    "   ######",
]
DINO_PIERNAS_1 = [
    "    ##  #",
    "    #   ##",
]
DINO_PIERNAS_2 = [
    "    #   ##",
    "    ##",
]

PAJARO_ALAS_ARRIBA = [
    "     #",
    "     ##",
    "  #  ###",
    " ### ####",
    "##########",
    "   ########",
    "     ####",
]
PAJARO_ALAS_ABAJO = [
    "",
    "",
    "  #",
    " ###",
    "##########",
    "   ########",
    "     ####",
    "     ###",
    "     ##",
]


def crear_sprite(dibujo, color):
    """Convierte una lista de textos con '#' en una Surface de Pygame."""
    columnas = max(len(fila) for fila in dibujo)
    superficie = pygame.Surface(
        (columnas * TAMANIO_PIXEL, len(dibujo) * TAMANIO_PIXEL), pygame.SRCALPHA
    )
    for fila, linea in enumerate(dibujo):
        for columna, caracter in enumerate(linea):
            if caracter == "#":
                rect = (columna * TAMANIO_PIXEL, fila * TAMANIO_PIXEL,
                        TAMANIO_PIXEL, TAMANIO_PIXEL)
                pygame.draw.rect(superficie, color, rect)
    return superficie


def cargar_sprites():
    """Crea todas las imágenes del juego una sola vez, al iniciar."""
    return {
        "dino_1": crear_sprite(DINO_CUERPO + DINO_PIERNAS_1, COLOR_DINO),
        "dino_2": crear_sprite(DINO_CUERPO + DINO_PIERNAS_2, COLOR_DINO),
        "pajaro_1": crear_sprite(PAJARO_ALAS_ARRIBA, COLOR_PAJARO),
        "pajaro_2": crear_sprite(PAJARO_ALAS_ABAJO, COLOR_PAJARO),
    }


# ----------------------------------------------------------------------------
# Sonidos (se generan con código, así no hacen falta archivos .wav)
# ----------------------------------------------------------------------------
def crear_sonido(frecuencia_inicial, frecuencia_final, duracion, volumen=0.25, ruido=False):
    """
    Genera un sonido retro de onda cuadrada que va de una frecuencia a otra.
    Si ruido es True genera ruido blanco (sirve para el choque).
    """
    frecuencia_muestreo, _, canales = pygame.mixer.get_init()
    total_muestras = int(frecuencia_muestreo * duracion)
    amplitud = int(32767 * volumen)
    muestras = array("h")
    fase = 0.0

    for i in range(total_muestras):
        progreso = i / total_muestras
        envolvente = 1 - progreso             # el volumen baja hasta apagarse
        if ruido:
            valor = random.randint(-amplitud, amplitud)
        else:
            frecuencia = frecuencia_inicial + (frecuencia_final - frecuencia_inicial) * progreso
            fase = (fase + frecuencia / frecuencia_muestreo) % 1
            valor = amplitud if fase < 0.5 else -amplitud
        valor = int(valor * envolvente)
        for _ in range(canales):
            muestras.append(valor)

    return pygame.mixer.Sound(buffer=muestras)


def cargar_sonidos():
    """Crea los sonidos del juego. Si no hay placa de audio, el juego sigue sin sonido."""
    if pygame.mixer.get_init() is None:
        return {}
    try:
        return {
            "salto": crear_sonido(350, 750, 0.12),
            "choque": crear_sonido(0, 0, 0.35, volumen=0.3, ruido=True),
            "puntos": crear_sonido(900, 1300, 0.15, volumen=0.15),
            "letra": crear_sonido(600, 600, 0.05, volumen=0.15),
            "confirmar": crear_sonido(500, 1000, 0.25, volumen=0.2),
        }
    except pygame.error:
        return {}


def reproducir(sonidos, nombre):
    """Reproduce un sonido si existe (evita errores cuando no hay audio)."""
    if nombre in sonidos:
        sonidos[nombre].play()


# ----------------------------------------------------------------------------
# Jugador
# ----------------------------------------------------------------------------
def crear_jugador(sprites):
    """Devuelve un diccionario con el estado del dinosaurio."""
    ancho, alto = sprites["dino_1"].get_size()
    return {
        "rect": pygame.Rect(80, SUELO_Y - alto, ancho, alto),
        "y": float(SUELO_Y - alto),  # posición exacta (con decimales) para la física
        "vel_y": 0.0,
        "en_suelo": True,
    }


def saltar(jugador, sonidos):
    """Inicia el salto solo si el dinosaurio está apoyado en el suelo."""
    if jugador["en_suelo"]:
        jugador["vel_y"] = FUERZA_SALTO
        jugador["en_suelo"] = False
        reproducir(sonidos, "salto")


def cortar_salto(jugador):
    """Si se suelta la tecla mientras sube, el salto termina antes (salto corto)."""
    if jugador["vel_y"] < CORTE_SALTO:
        jugador["vel_y"] = CORTE_SALTO

def actualizar_jugador(jugador, dt):
    """
    Aplica la física: la gravedad cambia la velocidad y la velocidad
    cambia la posición. Cuando toca el suelo, se frena.
    """
    if not jugador["en_suelo"]:
        jugador["vel_y"] += GRAVEDAD * dt
        jugador["y"] += jugador["vel_y"] * dt

        piso = SUELO_Y - jugador["rect"].height
        if jugador["y"] >= piso:
            jugador["y"] = piso
            jugador["vel_y"] = 0.0
            jugador["en_suelo"] = True

    jugador["rect"].y = round(jugador["y"])


# ----------------------------------------------------------------------------
# Obstáculos
# ----------------------------------------------------------------------------
def crear_obstaculo(velocidad, sprites):
    """
    Crea un obstáculo al azar en el borde derecho de la pantalla.
    Hay cactus de distinto tamaño y, cuando el juego va rápido, pájaros
    que vuelan a diferentes alturas.
    """
    tipos = ["cactus_chico", "cactus_grande", "cactus_grupo"]
    if velocidad > 550:
        tipos += ["pajaro_bajo", "pajaro_alto"]
    tipo = random.choice(tipos)

    if tipo == "cactus_chico":
        ancho, alto = 22, random.randint(36, 46)
        y = SUELO_Y - alto
    elif tipo == "cactus_grande":
        ancho, alto = 30, random.randint(55, 68)
        y = SUELO_Y - alto
    elif tipo == "cactus_grupo":
        ancho, alto = 66, random.randint(38, 48)
        y = SUELO_Y - alto
    else:
        ancho, alto = sprites["pajaro_1"].get_size()
        if tipo == "pajaro_bajo":
            y = SUELO_Y - alto - 20    # a la altura de la cabeza: hay que saltarlo
        else:
            y = SUELO_Y - alto - 75    # vuela alto: conviene NO saltar

    return {"tipo": tipo, "x": float(ANCHO), "rect": pygame.Rect(ANCHO, y, ancho, alto)}


def distancia_hasta_proximo(velocidad):
    """
    Distancia aleatoria (en px) hasta el siguiente obstáculo. Crece con la
    velocidad para que siempre haya lugar para caer entre dos obstáculos.
    """
    minimo = velocidad * 0.75 + 160
    maximo = velocidad * 1.6 + 380
    return random.uniform(minimo, maximo)


def actualizar_obstaculos(obstaculos, velocidad, dt):
    """Mueve los obstáculos hacia la izquierda y borra los que ya salieron."""
    for obstaculo in obstaculos:
        obstaculo["x"] -= velocidad * dt
        obstaculo["rect"].x = round(obstaculo["x"])
    return [o for o in obstaculos if o["rect"].right > 0]


def hay_colision(jugador, obstaculos):
    """
    Revisa si el dinosaurio toca algún obstáculo. Se usan rectángulos un
    poco más chicos que los dibujos para que el choque sea "justo" y no
    se pierda por un píxel transparente.
    """
    caja_jugador = jugador["rect"].inflate(-14, -10)
    for obstaculo in obstaculos:
        caja_obstaculo = obstaculo["rect"].inflate(-8, -6)
        if caja_jugador.colliderect(caja_obstaculo):
            return True
    return False


# ----------------------------------------------------------------------------
# Escenario decorativo (nubes y piedritas del suelo)
# ----------------------------------------------------------------------------
def crear_escenario():
    nubes = [{"x": random.uniform(0, ANCHO), "y": random.randint(40, 160)} for _ in range(4)]
    piedritas = [{"x": random.uniform(0, ANCHO), "y": random.randint(SUELO_Y + 6, ALTO - 20),
                  "ancho": random.randint(2, 8)} for _ in range(30)]
    return {"nubes": nubes, "piedritas": piedritas}


def actualizar_escenario(escenario, velocidad, dt):
    # Las nubes se mueven más lento que el suelo: da sensación de profundidad.
    for nube in escenario["nubes"]:
        nube["x"] -= velocidad * 0.15 * dt
        if nube["x"] < -100:
            nube["x"] = ANCHO + random.randint(0, 200)
            nube["y"] = random.randint(40, 160)
    for piedrita in escenario["piedritas"]:
        piedrita["x"] -= velocidad * dt
        if piedrita["x"] < -10:
            piedrita["x"] = ANCHO + random.randint(0, 50)


# ----------------------------------------------------------------------------
# Partida
# ----------------------------------------------------------------------------
def nueva_partida(sprites):
    """Devuelve un diccionario con todo lo necesario para una partida nueva."""
    return {
        "jugador": crear_jugador(sprites),
        "obstaculos": [],
        "velocidad": VELOCIDAD_INICIAL,
        "puntaje": 0.0,
        "proximo_obstaculo": 300.0,   # px hasta que aparezca el primero
        "tiempo": 0.0,                 # segundos jugados
    }


def actualizar_partida(partida, escenario, sprites, sonidos, dt):
    """Avanza un fotograma de juego. Devuelve True si el jugador chocó."""
    # Dificultad creciente: la velocidad sube con el tiempo hasta un máximo.
    partida["tiempo"] += dt
    partida["velocidad"] = min(VELOCIDAD_INICIAL + ACELERACION * partida["tiempo"],
                               VELOCIDAD_MAXIMA)
    velocidad = partida["velocidad"]
    distancia = velocidad * dt

    # Puntaje según la distancia recorrida; suena un "bip" cada 100 puntos.
    puntaje_anterior = int(partida["puntaje"])
    partida["puntaje"] += distancia * PUNTOS_POR_PIXEL
    if int(partida["puntaje"]) // 100 > puntaje_anterior // 100:
        reproducir(sonidos, "puntos")

    actualizar_jugador(partida["jugador"], dt)

    # Aparición de obstáculos a intervalos aleatorios.
    partida["proximo_obstaculo"] -= distancia
    if partida["proximo_obstaculo"] <= 0:
        partida["obstaculos"].append(crear_obstaculo(velocidad, sprites))
        partida["proximo_obstaculo"] = distancia_hasta_proximo(velocidad)

    partida["obstaculos"] = actualizar_obstaculos(partida["obstaculos"], velocidad, dt)
    actualizar_escenario(escenario, velocidad, dt)

    return hay_colision(partida["jugador"], partida["obstaculos"])


# ----------------------------------------------------------------------------
# Ingreso de iniciales (estilo recreativa clásica)
# ----------------------------------------------------------------------------
def crear_ingreso_iniciales(ultimas_iniciales):
    """Las letras se guardan como posiciones dentro de ALFABETO."""
    return {"letras": [ALFABETO.index(c) for c in ultimas_iniciales], "posicion": 0}


def manejar_tecla_iniciales(ingreso, evento, sonidos):
    """
    Procesa una tecla en la pantalla de iniciales.
    Devuelve las 3 letras cuando el jugador confirma; si no, devuelve None.
    """
    tecla = evento.key
    pos = ingreso["posicion"]

    if tecla == pygame.K_UP:
        ingreso["letras"][pos] = (ingreso["letras"][pos] + 1) % len(ALFABETO)
        reproducir(sonidos, "letra")
    elif tecla == pygame.K_DOWN:
        ingreso["letras"][pos] = (ingreso["letras"][pos] - 1) % len(ALFABETO)
        reproducir(sonidos, "letra")
    elif tecla in (pygame.K_LEFT, pygame.K_BACKSPACE):
        ingreso["posicion"] = max(0, pos - 1)
    elif tecla == pygame.K_RIGHT:
        ingreso["posicion"] = min(2, pos + 1)
    elif tecla in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        if pos < 2:
            ingreso["posicion"] += 1
        else:
            reproducir(sonidos, "confirmar")
            return "".join(ALFABETO[i] for i in ingreso["letras"])
    elif evento.unicode != "" and evento.unicode.upper() in ALFABETO:
        # También se puede escribir la letra directamente.
        ingreso["letras"][pos] = ALFABETO.index(evento.unicode.upper())
        ingreso["posicion"] = min(2, pos + 1)
        reproducir(sonidos, "letra")
    return None


# ----------------------------------------------------------------------------
# Dibujo
# ----------------------------------------------------------------------------
def dibujar_texto(pantalla, texto, fuente, color, centro_x, y):
    """Dibuja un texto centrado horizontalmente en centro_x."""
    imagen = fuente.render(texto, True, color)
    pantalla.blit(imagen, (centro_x - imagen.get_width() // 2, y))


def dibujar_escenario(pantalla, escenario):
    pantalla.fill(COLOR_FONDO)
    for nube in escenario["nubes"]:
        x, y = round(nube["x"]), nube["y"]
        pygame.draw.rect(pantalla, COLOR_NUBE, (x, y, 70, 14))
        pygame.draw.rect(pantalla, COLOR_NUBE, (x + 15, y - 10, 36, 10))
    pygame.draw.line(pantalla, COLOR_SUELO, (0, SUELO_Y), (ANCHO, SUELO_Y), 2)
    for piedrita in escenario["piedritas"]:
        pygame.draw.rect(pantalla, COLOR_PIEDRITAS,
                         (round(piedrita["x"]), piedrita["y"], piedrita["ancho"], 2))


def dibujar_cactus(pantalla, rect):
    """Dibuja un cactus (tronco + dos brazos) que ocupa el rectángulo dado."""
    tronco = pygame.Rect(0, rect.top, max(8, rect.width // 3), rect.height)
    tronco.centerx = rect.centerx
    brazo = max(4, rect.width // 5)
    pygame.draw.rect(pantalla, COLOR_CACTUS, tronco, border_radius=3)
    # brazo izquierdo
    pygame.draw.rect(pantalla, COLOR_CACTUS, (rect.left, rect.top + rect.height // 4, brazo, rect.height // 3))
    pygame.draw.rect(pantalla, COLOR_CACTUS, (rect.left, rect.top + rect.height // 4 + rect.height // 3 - brazo, tronco.left - rect.left, brazo))
    # brazo derecho
    pygame.draw.rect(pantalla, COLOR_CACTUS, (rect.right - brazo, rect.top + rect.height // 6, brazo, rect.height // 3))
    pygame.draw.rect(pantalla, COLOR_CACTUS, (tronco.right, rect.top + rect.height // 6 + rect.height // 3 - brazo, rect.right - tronco.right, brazo))


def dibujar_obstaculos(pantalla, obstaculos, sprites):
    aleteo = (pygame.time.get_ticks() // 150) % 2   # alterna las alas
    for obstaculo in obstaculos:
        rect = obstaculo["rect"]
        if obstaculo["tipo"] == "cactus_grupo":
            # tres cactus juntos
            ancho = rect.width // 3
            for i in range(3):
                alto = rect.height - (i % 2) * 10
                dibujar_cactus(pantalla, pygame.Rect(rect.left + i * ancho, rect.bottom - alto, ancho, alto))
        elif obstaculo["tipo"].startswith("cactus"):
            dibujar_cactus(pantalla, rect)
        else:
            imagen = sprites["pajaro_1"] if aleteo == 0 else sprites["pajaro_2"]
            pantalla.blit(imagen, rect)


def dibujar_jugador(pantalla, jugador, sprites, corriendo):
    """Alterna entre dos dibujos de piernas para simular que corre."""
    paso = (pygame.time.get_ticks() // 100) % 2
    if corriendo and jugador["en_suelo"] and paso == 1:
        imagen = sprites["dino_2"]
    else:
        imagen = sprites["dino_1"]
    pantalla.blit(imagen, jugador["rect"])


def dibujar_puntajes(pantalla, fuentes, puntaje, record):
    texto = f"HI {record:05d}   {int(puntaje):05d}"
    imagen = fuentes["chica"].render(texto, True, COLOR_TEXTO)
    pantalla.blit(imagen, (ANCHO - imagen.get_width() - 20, 16))


def dibujar_partida(pantalla, partida, escenario, sprites, fuentes, record, corriendo=True):
    dibujar_escenario(pantalla, escenario)
    dibujar_obstaculos(pantalla, partida["obstaculos"], sprites)
    dibujar_jugador(pantalla, partida["jugador"], sprites, corriendo)
    dibujar_puntajes(pantalla, fuentes, partida["puntaje"], max(record, int(partida["puntaje"])))


def oscurecer(pantalla, opacidad=170):
    """Pone una capa semitransparente encima para destacar los menús."""
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    capa.fill((20, 15, 45, opacidad))
    pantalla.blit(capa, (0, 0))


def parpadea():
    """True durante medio segundo, False el otro medio (para textos que titilan)."""
    return (pygame.time.get_ticks() // 500) % 2 == 0


def dibujar_inicio(pantalla, fuentes):
    oscurecer(pantalla, 120)
    dibujar_texto(pantalla, "DINO RUNNER", fuentes["titulo"], COLOR_RESALTADO, ANCHO // 2, 90)
    dibujar_texto(pantalla, "Esquiva los cactus y los pajaros", fuentes["chica"], COLOR_TEXTO, ANCHO // 2, 170)
    dibujar_texto(pantalla, "ESPACIO / FLECHA ARRIBA = saltar", fuentes["chica"], COLOR_APAGADO, ANCHO // 2, 200)
    if parpadea():
        dibujar_texto(pantalla, "PRESIONA ESPACIO PARA EMPEZAR", fuentes["media"], COLOR_TEXTO, ANCHO // 2, 245)


def dibujar_choque(pantalla, fuentes):
    dibujar_texto(pantalla, "GAME OVER", fuentes["titulo"], COLOR_ROJO, ANCHO // 2, 120)


def dibujar_iniciales(pantalla, fuentes, ingreso, puntaje):
    oscurecer(pantalla)
    dibujar_texto(pantalla, "GAME OVER", fuentes["titulo"], COLOR_ROJO, ANCHO // 2, 30)
    dibujar_texto(pantalla, f"PUNTAJE: {int(puntaje):05d}", fuentes["media"], COLOR_TEXTO, ANCHO // 2, 100)
    dibujar_texto(pantalla, "INGRESA TUS INICIALES", fuentes["media"], COLOR_RESALTADO, ANCHO // 2, 140)

    # Las tres letras, con flechas sobre la que se está editando.
    for i, indice in enumerate(ingreso["letras"]):
        x = ANCHO // 2 + (i - 1) * 80
        seleccionada = i == ingreso["posicion"]
        color = COLOR_RESALTADO if seleccionada else COLOR_TEXTO
        dibujar_texto(pantalla, ALFABETO[indice], fuentes["titulo"], color, x, 200)
        if seleccionada:
            dibujar_texto(pantalla, "^", fuentes["media"], COLOR_RESALTADO, x, 180)
            dibujar_texto(pantalla, "v", fuentes["media"], COLOR_RESALTADO, x, 262)
            if parpadea():
                pygame.draw.rect(pantalla, COLOR_RESALTADO, (x - 22, 268, 44, 4))

    dibujar_texto(pantalla, "ARRIBA/ABAJO: letra   IZQ/DER: mover   ENTER: confirmar",
                  fuentes["chica"], COLOR_APAGADO, ANCHO // 2, 320)


def dibujar_fin(pantalla, fuentes, puntaje, iniciales, top):
    oscurecer(pantalla)
    dibujar_texto(pantalla, f"{iniciales}  {int(puntaje):05d}", fuentes["media"], COLOR_TEXTO, ANCHO // 2, 24)
    dibujar_texto(pantalla, "TOP 5", fuentes["media"], COLOR_RESALTADO, ANCHO // 2, 70)
    for i, partida in enumerate(top[:5]):
        linea = f"{i + 1}. {partida['iniciales']}  {partida['puntaje']:05d}"
        dibujar_texto(pantalla, linea, fuentes["media"], COLOR_TEXTO, ANCHO // 2, 110 + i * 34)
    dibujar_texto(pantalla, "Ranking completo abierto en el navegador", fuentes["chica"], COLOR_APAGADO, ANCHO // 2, 290)
    if parpadea():
        dibujar_texto(pantalla, "ESPACIO: jugar de nuevo   ESC: salir", fuentes["chica"], COLOR_RESALTADO, ANCHO // 2, 330)


def guardar_captura(pantalla):
    """Guarda lo que se ve en pantalla como PNG (útil para el informe)."""
    CARPETA_CAPTURAS.mkdir(exist_ok=True)
    nombre = datetime.now().strftime("captura_%Y%m%d_%H%M%S.png")
    pygame.image.save(pantalla, CARPETA_CAPTURAS / nombre)


# ----------------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------------
def terminar_partida(iniciales, puntaje):
    """Guarda el resultado, regenera ranking.html y lo abre en el navegador."""
    guardar_resultado(iniciales, int(puntaje))
    generar_ranking(abrir=True)


def main():
    # Audio mono de 16 bits: es el formato en el que crear_sonido arma las muestras.
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=1)
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Dino Runner")
    reloj = pygame.time.Clock()

    fuentes = {
        "titulo": pygame.font.SysFont("consolas,couriernew,monospace", 56, bold=True),
        "media": pygame.font.SysFont("consolas,couriernew,monospace", 28, bold=True),
        "chica": pygame.font.SysFont("consolas,couriernew,monospace", 20, bold=True),
    }
    sprites = cargar_sprites()
    sonidos = cargar_sonidos()

    escenario = crear_escenario()
    partida = nueva_partida(sprites)
    record = obtener_record()
    estado = "inicio"
    tiempo_choque = 0.0
    ultimas_iniciales = "AAA"
    ingreso = None
    top = []

    # Game loop: se repite FPS veces por segundo hasta que se cierra la ventana.
    ejecutando = True
    while ejecutando:
        # dt = segundos desde el fotograma anterior. Se limita para que, si la
        # ventana se traba un momento, el dinosaurio no "atraviese" obstáculos.
        dt = min(reloj.tick(FPS) / 1000, 0.05)

        # --- 1. Eventos (teclado / ventana) ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False

            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_F12:
                    guardar_captura(pantalla)
                elif evento.key == pygame.K_ESCAPE and estado != "iniciales":
                    ejecutando = False

                elif estado == "inicio" and evento.key in (pygame.K_SPACE, pygame.K_UP):
                    estado = "jugando"
                    saltar(partida["jugador"], sonidos)

                elif estado == "jugando" and evento.key in (pygame.K_SPACE, pygame.K_UP):
                    saltar(partida["jugador"], sonidos)

                elif estado == "iniciales":
                    iniciales = manejar_tecla_iniciales(ingreso, evento, sonidos)
                    if iniciales is not None:
                        ultimas_iniciales = iniciales
                        terminar_partida(iniciales, partida["puntaje"])
                        top = ordenar_por_puntaje(leer_partidas())
                        record = top[0]["puntaje"]
                        estado = "fin"

                elif estado == "fin" and evento.key in (pygame.K_SPACE, pygame.K_RETURN):
                    partida = nueva_partida(sprites)
                    estado = "jugando"

            elif evento.type == pygame.KEYUP and estado == "jugando":
                if evento.key in (pygame.K_SPACE, pygame.K_UP):
                    cortar_salto(partida["jugador"])

        # --- 2. Lógica ---
        if estado == "jugando":
            if actualizar_partida(partida, escenario, sprites, sonidos, dt):
                reproducir(sonidos, "choque")
                estado = "choque"
                tiempo_choque = 0.0
        elif estado == "choque":
            tiempo_choque += dt
            if tiempo_choque >= TIEMPO_CHOQUE:
                ingreso = crear_ingreso_iniciales(ultimas_iniciales)
                estado = "iniciales"
        elif estado == "inicio":
            actualizar_escenario(escenario, VELOCIDAD_INICIAL * 0.3, dt)

        # --- 3. Dibujo ---
        dibujar_partida(pantalla, partida, escenario, sprites, fuentes, record,
                        corriendo=(estado == "jugando"))
        if estado == "inicio":
            dibujar_inicio(pantalla, fuentes)
        elif estado == "choque":
            dibujar_choque(pantalla, fuentes)
        elif estado == "iniciales":
            dibujar_iniciales(pantalla, fuentes, ingreso, partida["puntaje"])
        elif estado == "fin":
            dibujar_fin(pantalla, fuentes, partida["puntaje"], ultimas_iniciales, top)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
