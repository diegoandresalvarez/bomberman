'''
B O M B E R M A N   N E S
Por:
Diego Andrés Alvarez Marín (daalvarez@unal.edu.co)

Juegue la versión original del Bomberman para NES en:
https://www.retrogames.cc/nes-games/bomberman-usa.html

Los sprites se tomaron de:
>>> https://www.spriters-resource.com/nes/bomberman/sheet/7884/
y se recortaron con:
>>> https://ezgif.com/sprite-cutter
teniendo en cuenta que cada uno mide 16x16 pixeles

INSTRUCCIONES:
 * Flechas mueven el bomberman
 * P       pausa
 * ESPACIO pone la bomba
 * ESCAPE  se sale del juego
'''

# %% se cargan las librerías
import copy
import time
import os
import pygame
import numpy as np

# %% se definen las constantes
# constantes básicas del tablero y del juego:
ESC = 2              # escala de multiplicacion de los sprites
VEL = 4*ESC          # velocidad de movimiento de los sprites (pixeles/cuadro)
ALTOFIL = ANCHOCOL = 16*ESC  # dimensiones de una casilla (tile)

# posición superior izquierda del tablero de juego
XTAB = 0
YTAB = 2*ALTOFIL

# se definen las constantes de los movimientos de los personajes
CENTRO, DERECHA, ARRIBA, IZQUIERDA, ABAJO, MURIENDO = range(6)
QUIETO = 0
INERCIA = None

# colores
COLOR_NEGRO  = (  0,   0,   0)
COLOR_BLANCO = (255, 255, 255)
COLOR_CESPED = ( 56, 135,   0)
COLOR_GRIS   = (176, 176, 176)

# %% se definen algunas variables globales y diccionarios
marcador = 0
lista_bombas = []
lista_muro_suaves_en_destruccion = []
lista_globos_agonizantes = []
#lista_explosion = []

dict_globo = {
    'xy'     : (0, 0),
    'filcol' : (0, 0),           # posición actual (fila, columna)
    'dir'    : DERECHA,          # dirección hacia la que avanza
    'vivo'   : True,             # vivo = True/muerto = False
    'caminados_misma_dir' : 0,   # cuadros caminados en la misma dirección
    'tic'    : time.time(),      # para el cronómetro
    'tiempo_entre_cuadros':1/10, # muévase 10 cuadros por segundo
    'idx'    : 0                 # índice de la imagen de la animación actual
}
# secuencia de imágenes con la animación del globo:
globo_imagen = (
             (  "globo_derec_1",                        ), # QUIETO
        tuple( f"globo_derec_{i}" for i in [0, 1, 2, 1] ), # DERECHA
        tuple( f"globo_derec_{i}" for i in [0, 1, 2, 1] ), # ARRIBA
        tuple( f"globo_izqui_{i}" for i in [0, 1, 2, 1] ), # IZQUIERDA
        tuple( f"globo_izqui_{i}" for i in [0, 1, 2, 1] ), # ABAJO
        tuple( f"globo_muere_{i}" for i in range(5)     )  # MURIENDO
)

dict_muro_suave = {
    'filcol'    : (0,0),         # posición actual (fila, columna)
    'destruido' : False,         # el muro ya terminó la secuencia de explosión
    'idx'       : 0,             # índice de la imagen de la animación actual
    'tic'       : time.time(),   # para el cronómetro
    'ultima_img': None,          # imagen y posición asociados al último blit
    'ultima_pos': None,          # de la imagen que se colocó en la pantalla
    'tiempo_entre_cuadros':1/16  # dibuje 16 cuadros por segundo
}
muro_suave_destruccion = ['muro_suave']
muro_suave_destruccion.extend([f"explosion_muro_suave_{i}" for i in range(6)])

dict_bomba = {
    'filcol'     : (0,0),    # posición actual (fila, columna)
    'detonada'   : False,    # bomba ya terminó la secuencia de explosión
    'explotando' : False,    # bomba en secuencia de explosión
    'onda_viaja' : 5*[None], # cuadros en que puede viajar la onda explosiva
    'mecha_tic'  : 0,        # tiempo en el que se activa la bomba
    'tic'    : time.time(),  # para el cronómetro
    'idx'        : -1 ,      # índice de la imagen de la animación actual
    'tiempo_mecha'    : 2,   # segundos que demora en explotar una vez activada
    'poder_explosivo' : 3,   # se cuenta en cuadros a la redonda
    'ultima_img' : None,     # imagen y posición asociados al último blit
    'tiempo_entre_cuadros': 1/8, # dibuje 8 cuadros por segundo
}
# se crean algunas variables estáticas con las animaciones
bomba_secuencia_activada  = tuple(f"bomba_{i}" for i in [0, 1, 2, 1])
bomba_secuencia_onda_explosiva = [0, 1, 2, 3, 2, 1, 0]

bomberman = {
    'xy'     : (XTAB+ANCHOCOL, YTAB+ALTOFIL),
    'filcol' : (1, 1),           # posición actual (fila, columna)
    'vidas'  : 3,                # numero de vidas
    'idx'    : 0,                # índice de la imagen de la animación actual
    'tic'    : time.time(),      # para el cronómetro
    'dir_anterior' : QUIETO,     # dirección anterior
    'ultima_img'   : None,       # imagen y posición asociados al último blit
    'ultima_pos'   : None,       # de la imagen que se colocó en la pantalla
    'tiempo_entre_cuadros':1/20  # velocidad = 10 cuadros por segundo
}
# secuencia de imágenes con la animación del bomberman:
bomberman_imagen = (
             (  "player_abajo_1",                        ), # QUIETO
        tuple( f"player_derec_{i}" for i in [0, 1, 2, 1] ), # DERECHA
        tuple( f"player_arrib_{i}" for i in [0, 1, 2, 1] ), # ARRIBA
        tuple( f"player_izqui_{i}" for i in [0, 1, 2, 1] ), # IZQUIERDA
        tuple( f"player_abajo_{i}" for i in [0, 1, 2, 1] ), # ABAJO
        tuple( f"player_muere_{i}" for i in range(8)     )  # MURIENDO
)

# %% se define el tablero de juego y algunos caracteres especiales
DESTELLO = 'x'
BOMBA    = 'B'
mapa = [
    "###############################",
    "#      ** *    *   *  * * *   #",
    "# # # #*# # #*#*# # # #*#*#*# #",   # "#" -> muro duro
    "#   *     ***  *      *   * * #",   # "*" -> muro suave
    "# # # # # #*# # #*#*# # # # #*#",
    "#            **  *  *         #",
    "# # # # # # # # # #*# #*# # # #",
    "#*  *      *  *      *        #",
    "# # # # #*# # # #*#*# # # # # #",
    "#*    **  *       *           #",
    "# #*# # # # # # #*# # # # # # #",
    "#           *   *  *          #",
    "###############################"
]

# se convierte el mapa a un array de caracteres de NumPy
try:
    mapa = np.array([list(fila) for fila in mapa])
except:
    print("Error en la definición del mapa")
    raise

NFIL, NCOL = mapa.shape  # filas mapa, columnas mapa
assert (NFIL == 13), "El tablero de juego debe tener 13 filas"
assert (NCOL == 31), "El tablero de juego debe tener 31 columnas"

# %%
def cargar_archivo_de_sonido(archivo):
    '''Carga un archivo del directorio "sonidos/" que contiene un sonido .WAV
    '''
    # Se crea la ruta del nombre del archivo a cargar.
    # La función os.path.join() concatena o produce el nombre del archivo de
    # modo que se pueda correr bajo cualquier sistema operativo.
    nombre_archivo = os.path.join('sonidos', archivo + '.wav')
    try:
        return pygame.mixer.Sound(nombre_archivo)
    except pygame.error:
        texto_error = 'No se pudo cargar el sonido {0}.\n{1}'.\
            format(nombre_archivo, pygame.get_error())
        pygame.quit()
        raise SystemExit(texto_error)

# %%
def cargar_archivo_de_imagen(archivo):
    '''Carga un archivo del directorio "imagenes/" que contiene una imagen .PNG
    '''
    # Se crea la ruta del nombre del archivo a cargar.
    # La función os.path.join() concatena o produce el nombre del archivo de
    # modo que se pueda correr bajo cualquier sistema operativo.
    nombre_archivo = os.path.join('imagenes', archivo + '.png')
    try:
        return pygame.image.load(nombre_archivo).convert()
    except pygame.error:
        texto_error = 'No se pudo cargar la imagen {0}.\n{1}'.\
            format(nombre_archivo, pygame.get_error())
        pygame.quit()
        raise SystemExit(texto_error)

# %%
def de_filcol_a_xy(filcol):
    '''Calcula la posición (x,y) equivalente a partir de la posición
    fila, columna con la que se accede al "mapa"
    '''
    return filcol[1]*ANCHOCOL + XTAB, filcol[0]*ALTOFIL  + YTAB # = (x, y)

# %%
def de_xy_a_filcol(x, y):
    '''Calcula el equivalente de las coordenadas (x,y) de una posición dada
    a las filas (fil) y columnas (col) equivalentes para acceder al "mapa"
    '''
    if   y%(2*ALTOFIL) in de_xy_a_filcol.idxs_6701:
        fil = (y + 2*VEL - YTAB)//ALTOFIL
    elif y%(2*ALTOFIL) in de_xy_a_filcol.idxs_2345:
        fil = (y + 1*VEL - YTAB)//ALTOFIL
    else:
        raise ValueError("y no puede tomar el valor que tiene actualmente")

    if   x%(2*ANCHOCOL) in de_xy_a_filcol.idxs_6701:
        col = (x + 2*VEL - XTAB)//ANCHOCOL
    elif x%(2*ANCHOCOL) in de_xy_a_filcol.idxs_2345:
        col = (x + 1*VEL - XTAB)//ANCHOCOL
    else:
        raise ValueError("x no puede tomar el valor que tiene actualmente")

    return fil, col
# creo dos variables estáticas, para no tener que calcularlas en cada llamado
de_xy_a_filcol.idxs_6701 = [6*VEL, 7*VEL, 0*VEL, 1*VEL]
de_xy_a_filcol.idxs_2345 = [2*VEL, 3*VEL, 4*VEL, 5*VEL]

# %%
def dibujar_tablero():
    '''Dibuja el tablero de juego, pero no la barra de estado
    '''
    # Se borra la pantalla
    ventana.fill(COLOR_GRIS)

    # Se dibuja cada una de las celdas del mapa
    for f in range(NFIL):
        for c in range(NCOL):
            if    mapa[f,c] == '#':  celda = 'muro_duro'
            elif  mapa[f,c] == '*':  celda = 'muro_suave'
            else:                    celda = 'cesped'
            ventana.blit(imagen[celda], de_filcol_a_xy((f,c)))

# %%
def dibujar_estado(texto='', pos_horizontal=0):
    '''Dibuja la barra de estado, usando texto con sombra
    '''
    # se renderiza el texto
    surface_texto  = fuente['pixeled'].render(texto, True, COLOR_BLANCO)
    texto_rect = surface_texto.get_rect()
    texto_rect.left = pos_horizontal
    texto_rect.centery = ALTOFIL - 3

    # se renderiza su sombra
    surface_sombra = fuente['pixeled'].render(texto, True, COLOR_NEGRO)
    sombra_rect = surface_sombra.get_rect()
    sombra_rect.left = pos_horizontal + 3
    sombra_rect.centery = ALTOFIL

    # se escriba el texto encima de la sombra
    ventana.blit(surface_sombra, sombra_rect)
    ventana.blit(surface_texto,  texto_rect)

# %%
def bomberman_puede_moverse(dir):
    '''Verifica si el bomberman puede moverse en la dirección indicada.

    La función tiene en cuenta los posibles obstáculos y los corredores libres.

    Uso:
    bomberman_puede_moverse(dir)

    Parámetros de entrada:
    dir : direcciones posibles de movimiento; estas pueden ser una de las
    siguientes: { QUIETO, DERECHA, ARRIBA, IZQUIERDA, ABAJO }.

    "INERCIA" quiere decir que el bomberman se queda estático pero mirando en la
    dirección del movimiento anterior

    "QUIETO" es la posición al principio del juego

    Retorna:
    True o False
    '''
    assert (dir in (QUIETO, DERECHA, ARRIBA, IZQUIERDA, ABAJO)), \
              "En bomberman_puede_moverse(dir), dir tiene un valor no permitido"

    # si el bomberman quiere quedar quieto, lo puede hacer
    if dir == QUIETO: return True

    # inicialmente, se carga al posición actual del bomberman
    x, y     = bomberman['xy']
    fil, col = bomberman['filcol']

    # se ajusta la posición actual del bomberman, de modo que este quede bien
    # centrado en la intersección en el caso de que este esté ubicado a un
    # cuadro de animación de la intersección
    #                                        ####    ####    ####
    # lo que se tiene con # es un muro duro  ####    ####    ####
    #                                        ####    ####    ####
    #                                        ####....####....####
    #                                           .xxxx.  .xxxx.
    #                                           .xxxx.  .xxxx.
    # lo que se tiene con . son las             .xxxx.  .xxxx.
    # posiciones que se ajustan para que        .xxxx.  .xxxx.
    # caigan perfectamente en la             ####....####....####
    # intersección, la cual denotamos con    ####    ####    ####
    # una x                                  ####    ####    ####
    #                                        ####    ####    ####
    if dir in (IZQUIERDA, DERECHA):
        if   y%ALTOFIL == ALTOFIL - VEL:   y += VEL
        elif y%ALTOFIL == VEL:             y -= VEL
    elif dir in (ARRIBA, ABAJO):
        if   x%ANCHOCOL == ANCHOCOL - VEL: x += VEL
        elif x%ANCHOCOL == VEL:            x -= VEL

    # ahora si se calcula la siguiente posición del bomberman
    if   dir == IZQUIERDA:      x_sgte, y_sgte = x-VEL, y
    elif dir == DERECHA:        x_sgte, y_sgte = x+VEL, y
    elif dir == ARRIBA:         x_sgte, y_sgte = x,     y-VEL
    elif dir == ABAJO:          x_sgte, y_sgte = x,     y+VEL

    # si la siguiente posición cae dentro de la celda actual, entonces el
    # bomberman se puede mover
    if     ((dir == IZQUIERDA and x_sgte >= (col*ANCHOCOL + XTAB)) or
            (dir == DERECHA   and x_sgte <= (col*ANCHOCOL + XTAB)) or
            (dir == ARRIBA    and y_sgte >= (fil*ALTOFIL  + YTAB)) or
            (dir == ABAJO     and y_sgte <= (fil*ALTOFIL  + YTAB))):
        return True

    # como la siguiente posición no cae en la celda actual, se calcula la
    # próxima posición en el "mapa"
    if   dir == IZQUIERDA:      fil_sgte, col_sgte = fil,   col-1
    elif dir == DERECHA:        fil_sgte, col_sgte = fil,   col+1
    elif dir == ARRIBA:         fil_sgte, col_sgte = fil-1, col
    elif dir == ABAJO:          fil_sgte, col_sgte = fil+1, col

    # si la posición deseada es un pasillo,
    #     puede moverse,
    # de lo contrario (si es un muro o una bomba),
    #     no puede hacerlo
    return (mapa[fil_sgte, col_sgte] == ' ')

# %%
def bomberman_mover(dir):
    '''Mueve el bomberman a la dirección indicada.

    Uso:
    bomberman_mover(dir)

    Parámetros de entrada:
    dir : direcciones posibles de movimiento; estas pueden ser una de las
    siguientes: { INERCIA, QUIETO, DERECHA, ARRIBA, IZQUIERDA, ABAJO }.

    "INERCIA" quiere decir que el bomberman se queda estático pero mirando en la
    dirección del movimiento anterior

    "QUIETO" es la posición al principio del juego
    '''

    # en caso de que el tiempo_entre_cuadros no se haya cumplido, simplemente
    # grafique la última imagen
    bomberman_toc = time.time()
    if (bomberman_toc - bomberman['tic']) < bomberman['tiempo_entre_cuadros']:
        ventana.blit(bomberman['ultima_img'], bomberman['ultima_pos'])
        return

    # si no se puede mover a la dirección "dir", entonces quédese quieto
    if (dir is not INERCIA) and (not bomberman_puede_moverse(dir)):
        dir = QUIETO

    # se obtienen las coordenadas x,y de la posición del bomberman
    x, y = bomberman['xy']

    # se ajusta la posición actual del bomberman, de modo que este quede bien
    # centrado en la intersección en el caso que este esté ubicado aun cuadro
    # de animación de la intersección
    if dir in (IZQUIERDA, DERECHA):
        if   y%ALTOFIL == ALTOFIL - VEL:   y += VEL
        elif y%ALTOFIL == VEL:             y -= VEL
    elif dir in (ARRIBA, ABAJO):
        if   x%ANCHOCOL == ANCHOCOL - VEL: x += VEL
        elif x%ANCHOCOL == VEL:            x -= VEL

    # actualizar las posiciones del bomberman
    if   dir == IZQUIERDA:                 x -= VEL
    elif dir == DERECHA:                   x += VEL
    elif dir == ARRIBA:                    y -= VEL
    elif dir == ABAJO:                     y += VEL
    elif dir == QUIETO:
        # si el bomberman se queda quieto, se pone la figura 0="player_abajo_1"
        bomberman['idx'] = 0
    elif dir is INERCIA:
        # en este caso, conservar la misma posición que en el cuadro anterior
        dir = bomberman['dir_anterior']
        bomberman['idx'] -= 1

    bomberman['idx'] %= 3  # bomberman['idx'] será 0, 1 o 2 cíclicamente

    # se grafica el bomberman en el tablero de juego, teniendo en cuenta la
    # dirección de movimiento y el índice en la animación a graficar
    bomberman['ultima_img'] = imagen[bomberman_imagen[dir][bomberman['idx']]]
    bomberman['ultima_pos'] = bomberman['xy']
    ventana.blit(bomberman['ultima_img'], bomberman['ultima_pos'])

    # y se actualiza el índice del cuadro a graficar en la siguiente iteración
    bomberman['idx'] += 1

    # se actualiza la posición del bomberman relativa al mapa de juego
    bomberman['filcol'] = de_xy_a_filcol(x, y)

    # se actualiza la posición en el diccionario "bomberman"
    bomberman['xy'] = (x, y)

    # se actualiza la dir_anterior, en caso que el bomberman se quede quieto
    bomberman['dir_anterior'] = dir

    # se actualiza el reloj interno del bomberman
    bomberman['tic'] = time.time()

# %%
def muro_suave_animar_destruccion(muro):
    # en caso que el tiempo_entre_cuadros no se haya cumplido, simplemente
    # grafique la última imagen
    muro_toc = time.time()
    if (muro_toc - muro['tic']) < muro['tiempo_entre_cuadros']:
        ventana.blit(muro['ultima_img'], muro['ultima_pos'])
        return

    # se grafica la imagen de la secuencia de animación de la destrucción del
    # muro_suave
    muro['ultima_img'] = imagen[muro_suave_destruccion[muro['idx']]]
    muro['ultima_pos'] = de_filcol_a_xy(muro['filcol'])
    ventana.blit(muro['ultima_img'], muro['ultima_pos'])

    # si terminó de explotar la bomba, quite el muro_suave del "mapa"
    if muro['idx'] == 6:
        mapa[muro['filcol']] =  ' '
        # se debe informar que el muro fue destruído para posteriormente
        # removerlo de "lista_muro_suaves_en_destruccion"
        muro['destruido'] = True

    # actualiza el índice de la animación a graficar en la próxima iteración
    muro['idx'] += 1

    # se actualiza el reloj interno del muro
    muro['tic'] = time.time()

# %%
def bomba_colocar():
    '''Activa una bomba, pero no la grafica
    '''
    # se añade la bomba a la lista de bombas teniendo en cuenta que su posición
    # es la misma donde está ubicado el bomberman actualmente y se activa reloj
    # interno para la detonación
    sonido['poner_bomba'].play()
    bomba = copy.deepcopy(dict_bomba)
    bomba['filcol'] =  bomberman['filcol']
    bomba['tic'] = bomba['mecha_tic'] = time.time()
    lista_bombas.append(bomba)

# %%
def bomba_activar_y_explotar(bomba):
    '''Grafica las bombas activadas y cuando se cumple el tiempo, las explota
    '''
    # si la bomba no ha explotado (solo está activada), haga lo siguiente
    if not b['explotando']:
        # en caso de que el tiempo_entre_cuadros no se haya cumplido,
        # simplemente  grafique la última imagen
        bomba_toc = time.time()
        if (bomba_toc - bomba['tic']) < bomba['tiempo_entre_cuadros']:
            if bomba['ultima_img'] is None:
                bomba['ultima_img'] = imagen[bomba_secuencia_activada[-1]]
            ventana.blit(bomba['ultima_img'], de_filcol_a_xy(bomba['filcol']))
            return

        if (bomba_toc - bomba['mecha_tic']) < bomba['tiempo_mecha']:
            # si la bomba continúa en la fase de activación

            bomba['idx'] %= 3 # bomba['idx'] será 0, 1 o 2 cíclicamente

            # se grafica la bomba en el tablero de juego, teniendo en cuenta el
            # número de cuadro (idx) en la animación a graficar
            bomba['ultima_img'] = imagen[bomba_secuencia_activada[bomba['idx']]]
            ventana.blit(bomba['ultima_img'], de_filcol_a_xy(bomba['filcol']))

            # y se actualiza el número del cuadro a graficar en la siguiente
            # iteración
            bomba['idx'] += 1

            # se actualiza el reloj interno de la bomba
            bomba['tic'] = time.time()
            return
        else:
            # se acaba de iniciar la explosión
            bomba['explotando'] = True

            # se configuran los datos de la explosión:
            # a) índice inicial de la animación
            bomba['idx'] = 0
            # b) cantidad de cuadros de la onda explosiva
            bomba['onda_viaja'] = 5*[bomba['poder_explosivo']]
            # en la dirección "CENTRO" no hay una estela explosiva
            bomba['onda_viaja'][CENTRO] = 0

            # y suela el boom de la explosión
            sonido['boom'].play()

    # si la bomba está explotando, haga lo siguiente:

    # en caso de que haya terminado de ejecutarse la explosión:
    if bomba['idx'] == 7:
        # se debe informar que la bomba fue detonada para posteriormente
        # removerla de "lista_bombas"
        bomba['detonada'] = True
        return

    # se determina cual de los cuadros de la explosión se debe graficar
    i = bomba_secuencia_onda_explosiva[bomba['idx']]
    f, c = bomba['filcol']

    # se dibuja el destello de la bomba en su posición
    ventana.blit(imagen[f'exp_{i}_centr'], de_filcol_a_xy((f, c)))

    # esta subfunción se coloca en medio del código con el único objeto de
    # reducir la cantidad de código que sigue, ya que todo tiene el mismo patrón
    def explosion(fil, col, dir, p, txt):
        # si no se ha encontrado un límite a la onda explosiva:
        if bomba['onda_viaja'][dir] == bomba['poder_explosivo']:
            # si hay un muro no siga dibujando la onda explosiva
            if mapa[fil, col] in ('#', '*'):     # muro duro/suave
                # se restringe la longitud de la onda explosiva
                bomba['onda_viaja'][dir] = p
                if mapa[fil, col] == '*':        # muro suave
                    # activar la destrucción del muro suave (muro_suave)
                    muro_suave = copy.deepcopy(dict_muro_suave)
                    muro_suave['filcol'] =  fil,col
                    lista_muro_suaves_en_destruccion.append(muro_suave)
                    return
            # pero si no hay muro, se grafica la onda explosiva
            else:
                # se grafica la onda explosiva
                if p == bomba['poder_explosivo']:
                    im = imagen[f'exp_{i}_{txt}_2'] # final de la estela
                else:
                    im = imagen[f'exp_{i}_{txt}_1'] # mitad de la estela
                ventana.blit(im, de_filcol_a_xy((fil, col)))

                # El globo que esta en la posición del destello muere
                for globo in lista_globos.copy():
                    if ((fil,col) == globo['filcol']) and globo['vivo']:
                        globo['idx'] = 0
                        lista_globos_agonizantes.append(globo)
                        lista_globos.remove(globo)
        # si se ha encontrado un límite a la onda explosiva:
        elif p < bomba['onda_viaja'][dir]:
            # se grafica la onda explosiva
            if p == bomba['poder_explosivo']:
                im = imagen[f'exp_{i}_{txt}_2']    # final de la estela
            else:
                im = imagen[f'exp_{i}_{txt}_1']    # mitad de la estela
            ventana.blit(im, de_filcol_a_xy((fil, col)))

            # El globo que esta en la posición del destello muere
            for globo in lista_globos.copy():
                if ((fil,col) == globo['filcol']) and globo['vivo']:
                    globo['idx'] = 0
                    lista_globos_agonizantes.append(globo)
                    lista_globos.remove(globo)

    # se dibuja la onda explosiva de la bomba
    for dir in [DERECHA, ARRIBA, IZQUIERDA, ABAJO]:
        for p in range(1, bomba['onda_viaja'][dir]+1):
            if   (dir == DERECHA):   explosion(f,   c+p, dir, p, 'derec')
            elif (dir == ARRIBA):    explosion(f-p, c,   dir, p, 'arrib')
            elif (dir == IZQUIERDA): explosion(f,   c-p, dir, p, 'izqui')
            elif (dir == ABAJO):     explosion(f+p, c,   dir, p, 'abajo')

    # y se actualiza el número del cuadro a graficar en la siguiente iteración
    bomba['idx'] += 1

# %%
def globo_puede_moverse(globo, dir):
    '''Verifica si el globo puede moverse en la dirección indicada.

    La función tiene en cuenta los posibles obstáculos, los corredores libres,
    las bombas y el destello de las explosiones.

    Uso:
    globo_puede_moverse(globo, dir)

    Parámetros de entrada:
    globo

    dir : direcciones posibles de movimiento; estas pueden ser una de las
    siguientes: { DERECHA, ARRIBA, IZQUIERDA, ABAJO }.

    Retorna:
    True o False
    '''
    assert (dir in (DERECHA, ARRIBA, IZQUIERDA, ABAJO)), \
           "En globo_puede_moverse(globo, dir), dir tiene un valor no permitido"

    # inicialmente, se carga al posición actual del globo
    x, y     = globo['xy']
    fil, col = globo['filcol']

    # se ajusta la posición actual del globo, de modo que este quede bien
    # centrado en la intersección en el caso de que este esté ubicado a un
    # cuadro de animación de la intersección
    if dir in (IZQUIERDA, DERECHA):
        if   y%ALTOFIL == ALTOFIL - VEL:   y += VEL
        elif y%ALTOFIL == VEL:             y -= VEL
    elif dir in (ARRIBA, ABAJO):
        if   x%ANCHOCOL == ANCHOCOL - VEL: x += VEL
        elif x%ANCHOCOL == VEL:            x -= VEL

    # se calcula la siguiente posición del globo
    if   dir == IZQUIERDA:      x_sgte, y_sgte = x-VEL, y
    elif dir == DERECHA:        x_sgte, y_sgte = x+VEL, y
    elif dir == ARRIBA:         x_sgte, y_sgte = x,     y-VEL
    elif dir == ABAJO:          x_sgte, y_sgte = x,     y+VEL

    # si la siguiente posición cae dentro de la celda actual, entonces el
    # globo se puede mover
    if     ((dir == IZQUIERDA and x_sgte >= (col*ANCHOCOL + XTAB)) or
            (dir == DERECHA   and x_sgte <= (col*ANCHOCOL + XTAB)) or
            (dir == ARRIBA    and y_sgte >= (fil*ALTOFIL  + YTAB)) or
            (dir == ABAJO     and y_sgte <= (fil*ALTOFIL  + YTAB))) :
        return True

    # como la siguiente posición no cae en la celda actual, se calcula la
    # próxima posición en el "mapa"
    if   dir == IZQUIERDA:      fil_sgte, col_sgte = fil,   col-1
    elif dir == DERECHA:        fil_sgte, col_sgte = fil,   col+1
    elif dir == ARRIBA:         fil_sgte, col_sgte = fil-1, col
    elif dir == ABAJO:          fil_sgte, col_sgte = fil+1, col

    # el globo no es suicida y por lo tanto no se va a tirar al fuego de la
    # bomba
    if mapa[fil_sgte, col_sgte] == DESTELLO: return False

    # la bomba tampoco le permite avanzar
    if mapa[fil_sgte, col_sgte] == BOMBA: return False

    # si la posición deseada es un pasillo,
    #     puede moverse,
    # en caso contrario (por ejemplo si encuentra un muro),
    #     no lo haga
    return (mapa[fil_sgte, col_sgte] == ' ')

# %%
def globo_mover(globo):
    '''Mueve el globo aleatoriamente

    Uso:
    globo_mover(globo)

    Parámetros de entrada:
    globo : variable del tipo "dict_globo"
    '''
    # inicialmente, se determina la dirección en la que se moverá el globo
    num_pos_puede_moverse = 0

    # este vector almacena la funcion de masa de probabilidades FMP (no
    # normalizadas) de avanzar en la dirección indicada
    # Ver: http://es.wikipedia.org/wiki/Función_de_probabilidad
    fmp_dir = np.array([ 0., 0., 0., 0., 0. ])

    # determinar las direcciones en las que el globo se puede mover
    for dir in [ DERECHA, ARRIBA, IZQUIERDA, ABAJO ]:
        if globo_puede_moverse(globo, dir):
            num_pos_puede_moverse += 1
            fmp_dir[dir] =  1.0

    # se determina la dirección actual
    dir = globo['dir']

    # se determina la dirección contraria a la actual
    if   dir == DERECHA:   dir_contraria = IZQUIERDA
    elif dir == IZQUIERDA: dir_contraria = DERECHA
    elif dir == ARRIBA:    dir_contraria = ABAJO
    elif dir == ABAJO:     dir_contraria = ARRIBA

    # se selecciona la dirección aleatoria
    if num_pos_puede_moverse > 0:
        # se incrementan en 8 veces las probabilidades de moverse hacia
        # adelante (siguiendo la inercia), o hacia atrás (en caso de que se
        # hayan avanzado mas de 40 idxs en la misma dirección
        fmp_dir[dir] *= 50     # seguir la inercia
        if (globo_puede_moverse(globo, dir_contraria) and
                            (globo['caminados_misma_dir'] > 40)):
            fmp_dir[dir_contraria] *= 50

        # se normaliza la FMP "fmp_dir" y se muestrea la nueva dirección
        fmp_dir = fmp_dir/np.sum(fmp_dir)
        nueva_dir = np.random.choice(5, p=fmp_dir)

        # se cuentan los idxs caminados en la misma dirección
        if nueva_dir == dir:
            globo['caminados_misma_dir'] += 1
        else:
            globo['caminados_misma_dir'] = 0
    elif num_pos_puede_moverse == 0:
        # si el globo está encerrado y no se puede mover, entonces:
        #     el globo mira a la otra dirección, en signo de desespero
        nueva_dir = dir_contraria

    # se actualiza la dirección en la que se moverá el globo
    globo['dir'] = dir = nueva_dir

    # una vez determinada la dirección en la que avanzará el globo, se moverá
    # se obtienen las coordenadas x,y de la posición del globo
    x, y = globo['xy']

    # se ajusta la posición actual del globo, de modo que este quede bien
    # centrado en la intersección en el caso que este esté ubicado aun cuadro
    # de animación de la intersección
    if dir in (IZQUIERDA, DERECHA):
        if   y%ALTOFIL == ALTOFIL - VEL:   y += VEL
        elif y%ALTOFIL == VEL:             y -= VEL
    elif dir in (ARRIBA, ABAJO):
        if   x%ANCHOCOL == ANCHOCOL - VEL: x += VEL
        elif x%ANCHOCOL == VEL:            x -= VEL

    # actualizar las posiciones del globo
    if   dir == IZQUIERDA:                 x -= VEL
    elif dir == DERECHA:                   x += VEL
    elif dir == ARRIBA:                    y -= VEL
    elif dir == ABAJO:                     y += VEL

    globo['idx'] %= 3  # globo['idx'] será 0, 1 o 2 cíclicamente

    # se grafica el globo en el tablero de juego, teniendo en cuenta la
    # dirección de movimiento y el cuadro (idx) en la animación a graficar
    tmp = imagen[globo_imagen[dir][globo['idx']]]
    ventana.blit(tmp, globo['xy'])

    # y se actualiza el número del cuadro a graficar en la siguiente iteración
    globo['idx'] += 1

    # se actualiza la posición del globo relativa al mapa de juego
    globo['filcol'] = de_xy_a_filcol(x, y)

    # se actualiza la posición en el diccionario "globo"
    globo['xy'] = (x, y)

# %%
def globo_animar_muerte(globo):
    # se grafica el globo en el tablero de juego, teniendo en cuenta el
    # número de cuadro (idx) en la animación a graficar
    tmp = imagen[globo_imagen[MURIENDO][globo['idx']]]
    ventana.blit(tmp, globo['xy'])

    # y se actualiza el número del cuadro a graficar en la siguiente
    # iteración
    globo['idx'] += 1

    # si la bomba está explotando, haga lo siguiente:
    if globo['idx'] == 5:
        # se debe informar que la bomba fue detonada para posteriormente
        # removerla de la lista que contiene todas las bombas
        globo['vivo'] = False
        return

# %%###### ########## ######## PROGRAMA PRINCIPAL ######## ########## #########
# %% Se inicializa el modo PYGAME
pygame.init()
ventana = pygame.display.set_mode((NCOL*ANCHOCOL, (NFIL+2)*ALTOFIL))
pygame.display.set_caption('Bomberman NES')    # titulo a la ventana

# se crean dos canales de sonido para tocar dos pistas de audio simultaneamente
Canal_Musica_Fondo   = pygame.mixer.Channel(0)
Canal_Efectos_Sonido = pygame.mixer.Channel(1)

# %% Se configura la fuente
fuente = {}
fuente['pixeled'] = pygame.font.Font(os.path.join('fuentes','pixeled.ttf'), 18)
fuente['pixeled'].set_bold(True)

# %% Se leen los sonidos
archivos = [
    '02_Stage_Start',
    '03_Stage_Theme',
    'boom',
    'poner_bomba',
]

sonido = {}     # diccionario vacío
for archivo in archivos:
    sonido[archivo] = cargar_archivo_de_sonido(archivo)

# %% Se leen las imágenes del disco.
# Todas ellas están en el subdir "imagenes" y se les quita la extensión ".png"
archivos = [os.path.splitext(f)[0] for f in sorted(os.listdir('imagenes'))]

# se cargan cada una de las "Surfaces" correspondientes a las imágenes; a cada
# una de ellas se les duplica su tamaño y se dice que el COLOR_CESPED es
# transparente, excepto para el "cesped" mismo.
imagen = {}
for f in archivos:
    imagen[f] = pygame.transform.scale2x(cargar_archivo_de_imagen(f))
    if f != 'cesped':
        imagen[f].set_colorkey(COLOR_CESPED) # COLOR_CESPED es transparente

# %% Se le coloca el ícono a la ventana
pygame.display.set_icon(imagen['player_abajo_1'])

# %% se inicializan los globos (al azar)
n_globos = 10       # número actual de globos
lista_globos = []   # lista de globos
for i in range(n_globos):
    globo = copy.deepcopy(dict_globo)
    while True:
        # seleccione al azar fil y col hasta que encuentre una casilla vacía
        fil = np.random.randint(0, NFIL)
        col = np.random.randint(0, NCOL)
        if mapa[fil][col] == ' ': break
    # se inicializa la posición, la dirección y el cronómetro del globo
    globo['filcol'] = fil, col
    globo['xy']     = de_filcol_a_xy((fil, col))
    globo['dir']    = np.random.randint(1, 4+1)
    globo['tic']    = time.time()
    lista_globos.append(globo)

# %% se inicializa el bomberman
bomberman_mover(QUIETO)   # quédese en la posición "firme" al inicio del juego

# %% se toca la canción de fondo
Canal_Musica_Fondo.play(sonido['03_Stage_Theme'])

# %% se inicializa el reloj para los ciclos
reloj = pygame.time.Clock()

# %% bucle principal
salirse_del_juego = False  # ¿salirse del juego?
while (bomberman['vidas'] > 0) and (not salirse_del_juego):
    # se dibuja el tablero de juego y la línea de estado
    dibujar_tablero()
    dibujar_estado("TIME 90",     30)
    dibujar_estado(str(marcador), 450)
    dibujar_estado(f"LEFT {bomberman['vidas']-1}",     800)

    # se hace la animación de las bombas (o titila activada o explota). El ciclo
    # for se realiza sobre una copia, de modo tal que se pueda remover
    # fácilmente la bomba una vez esta haya sido detonada.
    for b in lista_bombas.copy():
        bomba_activar_y_explotar(b)
        if b['detonada']:
            lista_bombas.remove(b)

    # se hace la animación de la destrucción de los muro_suaves. El ciclo
    # for se realiza sobre una copia, de modo tal que se pueda remover
    # fácilmente el muro_suave una vez esta haya sido detonado.
    for m in lista_muro_suaves_en_destruccion.copy():
        muro_suave_animar_destruccion(m)
        if m['destruido']:
            lista_muro_suaves_en_destruccion.remove(m)

    # se hace la animación de la muerte de los globos por parte de las bombas
    for globo in lista_globos_agonizantes.copy():
        globo_animar_muerte(globo)
        if not globo['vivo']:
            lista_globos_agonizantes.remove(globo)

    # se mueven y grafican los globos
    for globo in lista_globos:
        globo_mover(globo)

    # leer el teclado/mouse/joystick
    for event in pygame.event.get():
        # si se presiona con el mouse la X de la ventana:
        if event.type == pygame.QUIT:
            salirse_del_juego = True

        # si se presiona una tecla:
        if event.type == pygame.KEYDOWN:
            # se sale del juego con ESCAPE
            if event.key == pygame.K_ESCAPE:
                salirse_del_juego = True

            # colocar una bomba con ESPACIO
            if event.key == pygame.K_SPACE:
                bomba_colocar()

            # hacer una pausa con la tecla "P"
            if event.key == pygame.K_p:
                pass

    # si se presiona una tecla:
    tecla = pygame.key.get_pressed()
    if   tecla[pygame.K_UP]:     bomberman_mover(ARRIBA)
    elif tecla[pygame.K_DOWN]:   bomberman_mover(ABAJO)
    elif tecla[pygame.K_LEFT]:   bomberman_mover(IZQUIERDA)
    elif tecla[pygame.K_RIGHT]:  bomberman_mover(DERECHA)
    else:
        # INERCIA quiere decir que el bomberman no se moverá pero se graficará
        # mirando en la dirección anterior
        bomberman_mover(INERCIA)

    # Actualizar la pantalla
    pygame.display.update()

    # número de cuadros/segundo en la animación
    tiempo_entre_ciclos = reloj.tick_busy_loop(16)

# %%
for f in bomberman_imagen[MURIENDO]:
    reloj.tick(10)
    dibujar_tablero()
    ventana.blit(imagen[f], bomberman['xy'])
    pygame.display.update()

# %% BYE, BYE!
pygame.quit()    # finalice el modo PYGAME
