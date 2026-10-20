#!/usr/bin/env python3
"""Nodo B (bote: OCR 0222 Ed + PAR 231 + inclinación) — generador del PCB.

Prototipo para los ensayos de la visita CONAE (26-30 oct 2026). Replica el
protoboard que ya anduvo (2026-10-16) + respaldo en microSD + alimentación
desde la batería de 12 V con el D-SUN. Método y reglas del nodo A (LPKF
ProtoMat S63, doble faz sin metalizar: zócalos soldados solo abajo, arriba
solo puentes entre vías).

Eje X a lo ancho, Y hacia abajo, origen arriba a la izquierda, vista superior.
"""

import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
D3 = os.path.join(HERE, '3d')

# ---------------------------------------------------------------- parámetros
BOARD_W, BOARD_H = 104.0, 90.0   # caja de Carlos 110 x 100
P = 2.54
SOCKET_H = 8.5          # tira hembra vertical 2.54
MOD_ON_SOCKET = 11.0    # base del módulo enchufado (hembra + plástico del macho)

# ---------------------------------------------------------------- nets
NETS = ["", "GND", "12V_IN", "F_OUT", "12V", "5V_DSUN", "5V_JP", "+5V", "3V3", "VE",
        "SDA", "SCL", "SD_CS", "SD_MOSI", "SD_MISO", "SD_SCK", "OCR_RX",
        "PAR_SIG", "PAR_DIV", "GND_CLICK"]
N = {n: i for i, n in enumerate(NETS)}

# ---------------------------------------------------------------- piezas
# Una pieza: dict(ref, val, x, y, pads=[(num, dx, dy, net, kind)], boxes, holes)
#   kind: 'ov_v' oval alargado en Y (fila horizontal), 'ov_h' alargado en X
#         (fila vertical), 'rect_v'/'rect_h' pin 1, 'big' bornera/diodo,
#         'big2' diodo de 3 A, 'cap' componente chico
#   boxes: [(x0, y0, x1, y1, z0, z1, (r, g, b))] en coords locales
#   holes: [(dx, dy, diam)] agujeros sin cobre (tornillo del módulo)
PARTS = []


def row(n_pins, x0, y0, nets, horizontal=True, pitch=P, kind=None, first=1):
    """Fila de pads: horizontal → avanza en X; vertical → avanza en Y."""
    pads = []
    for i in range(n_pins):
        dx, dy = (x0 + pitch * i, y0) if horizontal else (x0, y0 + pitch * i)
        if kind:
            k = kind
        else:
            k = ('rect_' if i == 0 else 'ov_') + ('v' if horizontal else 'h')
        pads.append((str(first + i), dx, dy, nets[i], k))
    return pads


def part(ref, val, x, y, pads, boxes=(), holes=(), rot=0, lbl=None):
    """rot: 0, 90 o 180 (giro del footprint en la placa; pads y cajas en coords locales)."""
    PARTS.append(dict(ref=ref, val=val, x=x, y=y, pads=pads, rot=rot, lbl=lbl,
                      boxes=list(boxes), holes=list(holes)))


BLACK, GREEN, BLUE, DARK = (.08, .08, .08), (.1, .6, .25), (.1, .25, .7), (.15, .15, .2)
SILVER, YELLOW, TAN = (.75, .75, .78), (.9, .75, .2), (.8, .65, .45)
CYAN, COPPER = (.2, .5, .8), (.7, .4, .2)


def terminal(ref, val, x, y, nets, pitch=3.5):
    """Bornera enchufable vertical (macho en placa), pines hacia abajo (Y).
    Stock del lab: verdes de 5.08 (2 y 3 polos) y de 3.5 (hasta 12 polos)."""
    n = len(nets)
    pads = row(n, 0, 0, [N[a] for a in nets], horizontal=False, pitch=pitch, kind='big')
    half, mid = pitch / 2, pitch * (n - 1) / 2
    # textos verticales a los costados de los pads (centrados tapaban los pads)
    part(ref, val, x, y, pads,
         boxes=[(-3.5, -half, 3.5, pitch * n - half, 0, 12, GREEN)],
         lbl=((-2.5, mid, 90), (2.5, mid, 90)))


def header_v(ref, val, x, y, nets, h=SOCKET_H):
    """Tira vertical (pines en Y) — hembra o macho, caja negra."""
    n = len(nets)
    pads = row(n, 0, 0, [N[a] if a else 0 for a in nets], horizontal=False)
    part(ref, val, x, y, pads,
         boxes=[(-1.27, -1.27, 1.27, P * n - 1.27, 0, h, BLACK)])


def header_h(ref, val, x, y, nets, h=SOCKET_H):
    n = len(nets)
    pads = row(n, 0, 0, [N[a] if a else 0 for a in nets], horizontal=True)
    part(ref, val, x, y, pads,
         boxes=[(-1.27, -1.27, P * n - 1.27, 1.27, 0, h, BLACK)],
         lbl=((P * (n - 1) / 2, 2.4, 0), (P * (n - 1) / 2, 3.7, 0)))


def axial_v(ref, val, x, y, a, b, color, kind='big', h=11, lbl=None):
    """Axial parado, patas en Y separadas 5.08. Por defecto: referencia arriba,
    valor vertical abajo."""
    part(ref, val, x, y, [('1', 0, 0, N[a], kind), ('2', 0, 5.08, N[b], kind)],
         boxes=[(-1.8, -1.8, 1.8, 1.8, 0, h, color)],
         lbl=lbl or ((0, -2.3, 0), (0, 10.0, 90)))


def axial_h(ref, val, x, y, a, b, color, kind='cap', h=9):
    """Axial parado, patas en X separadas 5.08."""
    part(ref, val, x, y, [('1', 0, 0, N[a], kind), ('2', 5.08, 0, N[b], kind)],
         boxes=[(-1.3, -1.3, 1.3, 1.3, 0, h, color)],
         lbl=((2.54, -1.9, 0), (2.54, 1.9, 0)))


def radial(ref, val, x, y, a, b, d, pitch, h, color=BLACK):
    """Electrolítico / inductor radial: pin 1 (+) a la izquierda."""
    part(ref, val, x, y, [('1', -pitch / 2, 0, N[a], 'big'), ('2', pitch / 2, 0, N[b], 'big')],
         boxes=[(-d / 2, -d / 2, d / 2, d / 2, 0.5, h, color)])


# === Bornes (borde izquierdo): batería, OCR, PAR =============================
# Todas de 2 polos, paso 5.08 (Pablo, 2026-10-20); el PAR usa dos de 2.
BP = 5.08
terminal('J1', 'BAT_12V', 4.5, 3.0, ['12V_IN', 'GND'], pitch=BP)
axial_v('F1', 'FUSE_1A', 11.0, 3.0, '12V_IN', 'F_OUT', TAN)
axial_v('D1', '1N5819', 15.5, 3.0, 'F_OUT', '12V', BLACK)
# OCR: solo alimentación; la señal (naranja) entra por la bornera del click.
terminal('J2', 'OCR_12V', 4.5, 13.2, ['GND', '12V'], pitch=BP)   # 12V abajo: sigue al PAR
# PAR, de arriba a abajo = pines 4 (V+), 3 (AGND) | 2 (señal), 1 (GND) del conector.
terminal('J3', 'PAR_PWR', 4.5, 23.4, ['12V', 'GND'], pitch=BP)
terminal('J4', 'PAR_SIG', 4.5, 33.6, ['PAR_SIG', 'GND'], pitch=BP)

# Divisor del PAR (0-5 V → 0-2.5 V) + filtro, DEBAJO del ADS1115 (el módulo
# queda a 11 mm sobre la tira hembra). C1 cerámico (NO electrolítico).
axial_h('R1', '10k', 18.5, 23.0, 'PAR_SIG', 'PAR_DIV', TAN, h=8)
axial_h('R2', '10k', 28.5, 23.0, 'GND', 'PAR_DIV', TAN, h=8)
axial_h('C1', '22n', 28.5, 29.0, 'PAR_DIV', 'GND', YELLOW, h=6)

# === ADS1115 (módulo 1x10), girado 180°: placa del módulo hacia ABAJO ========
# (2026-10-20) Así VDD/SCL/SDA quedan del lado de la Heltec (der) y A0 del lado
# del divisor (izq): de izq a der A3 A2 A1 A0 ALRT ADDR SDA SCL GND VDD.
ax0, ay0 = 43.4, 36.0     # pin 1 (VDD), el de la derecha
ads = row(10, 0, 0, [N['VE'], N['GND'], N['SCL'], N['SDA'], N['GND'], 0,
                     N['PAR_DIV'], 0, 0, 0])
part('U3', 'ADS1115', ax0, ay0, ads, boxes=[
    (-1.27, -1.27, P * 10 - 1.27, 1.27, 0, SOCKET_H, BLACK),
    (-3.0, -16.0, 26.0, 1.6, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, BLUE)], rot=180)

# === D-SUN (buck ajustable, 4 contactos de 2 pines) =========================
# Vista superior: IN- arriba izq, IN+ abajo izq, OUT- arriba der, OUT+ abajo
# der (el preset al lado de OUT+). Geometría: pares verticales, IN↔OUT a 18.5 mm
# (Pablo 2026-10-20; antes 17.78 = 7 pasos del protoboard), par de arriba ↔ par
# de abajo a 10.16 (2 agujeros libres entre pares).
DS_X, DS_Y = 18.5, 10.16
dx0, dy0 = 62.0, 3.5
pads = []
for num, (px, py, net) in enumerate([(0, 0, 'GND'), (0, DS_Y, '12V'),
                                     (DS_X, 0, 'GND'), (DS_X, DS_Y, '5V_DSUN')]):
    for k in range(2):
        pads.append((f'{num * 2 + k + 1}', px, py + P * k, N[net], 'big'))
part('U5', 'D-SUN', dx0, dy0, pads, boxes=[
    (-2.0, -2.4, DS_X + 2.0, DS_Y + P + 2.4, 2.5, 4.1, GREEN),
    (6.0, 0.5, 12.0, 6.5, 4.1, 8.0, SILVER)])

# JP1 corta el 5 V del D-SUN (sacarlo con la notebook enchufada por USB hasta
# confirmar que la V4 tiene diodo en VBUS). D2 evita que el USB alimente al
# D-SUN al revés. Con D2, ajustar el D-SUN a ~5.3 V.
header_h('JP1', '5V_EXT', 84.0, 14.9, ['5V_DSUN', '5V_JP'], h=2.5)
axial_v('D2', '1N5819', 92.0, 17.5, '5V_JP', '+5V', BLACK,
        lbl=((-2.3, 2.54, 90), (2.3, 2.54, 90)))

# === Heltec V4 (USB-C hacia la derecha) =====================================
# J2 fila de arriba, J3 fila de abajo, pin 1 del lado del USB; filas a 22.86.
# Corrida 3 mm del borde derecho: por ahí baja el +5V a la SD.
# I2C en GPIO17/18 (bus del OLED, Wire), como en el protoboard (2026-10-20). En
# la V4 salen por los pads auxiliares del extremo opuesto al USB: posición
# tomada del footprint de Carlos (GIPIS_LIB, pads 37/38) — VERIFICAR 1:1.
HW, HH = 51.8, 25.5
hx0, hy0 = BOARD_W - HW - 4.3, 30.0
# GND por J2.1 (abierto al plano de arriba); J3.1 queda libre: abajo lo encierran
# el 3V3 y el haz de la SD (son el mismo GND dentro de la Heltec).
j2 = {1: 'GND', 2: '+5V', 3: 'VE', 4: 'VE'}
# SD: CS=GPIO42 (J3.7), SCK=41 (J3.8), MOSI=40 (J3.9), MISO=39 (J3.10) — en este
# orden las 4 pistas llegan a la tira de la SD sin cruzarse.
# J3.2/J3.3 = 3V3 (siempre prendido) para ICM y click: sale entre las tiras,
# sale por el extremo de la Heltec y llega al ICM sin cruzar el I2C (con Ve no había camino).
j3 = {2: '3V3', 3: '3V3', 7: 'SD_CS', 8: 'SD_SCK', 9: 'SD_MOSI', 10: 'SD_MISO', 17: 'OCR_RX'}
pads = []
for n in range(1, 19):
    x = HW - 1.55 - P * (n - 1)
    pads.append((f'A{n}', x, 1.32, N[j2[n]] if n in j2 else 0, 'rect_v' if n == 1 else 'ov_v'))
    pads.append((f'B{n}', x, 1.32 + 22.86, N[j3[n]] if n in j3 else 0, 'rect_v' if n == 1 else 'ov_v'))
# Auxiliares: 2.54 más allá de J2/J3.18. En el extremo opuesto al USB van, de J3
# a J2: GPIO15, GPIO16, LED, GPIO17, GPIO18 (pinout V4, Pablo 2026-10-20) → 17/18
# del lado de J2, el 18 el más cercano. El footprint de Carlos los tiene del lado
# de J3. Separaciones del centro (3.81 / 6.35) tomadas de ese footprint: MEDIR.
xaux, ymid = HW - 1.55 - P * 18, 1.32 + 22.86 / 2
pads.append(('AUX17', xaux, ymid - 3.81, N['SDA'], 'ov_h'))
pads.append(('AUX18', xaux, ymid - 6.35, N['SCL'], 'ov_h'))
xa, xb = HW - 1.55 - P * 17 - 1.27, HW - 1.55 + 1.27
part('U1', 'HELTEC_V4', hx0, hy0, pads, boxes=[
    (xa, 0.05, xb, 2.59, 0, SOCKET_H, BLACK),
    (xa, 22.91, xb, 25.45, 0, SOCKET_H, BLACK),
    (xaux - 1.27, ymid - 7.62, xaux + 1.27, ymid - 2.54, 0, SOCKET_H, BLACK),   # aux 17/18
    (0, 0, HW, HH, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, DARK),
    (14, 4, 40, 21, MOD_ON_SOCKET + 1.6, MOD_ON_SOCKET + 3.6, BLACK),     # OLED
    (HW - 7.5, 8.5, HW + 0.8, 17.0, MOD_ON_SOCKET + 1.6, MOD_ON_SOCKET + 4.8, SILVER),  # USB-C
])

# === ICM-20689 (15 x 11.4, 2 columnas de 4 a 12.7 mm), chip arriba ==========
# Girado 180°: der (de arriba a abajo) SDA SCL GND VCC, izq AD0 CL DA INT
# (AD0 a GND → 0x68: con AD0 a 3V3 la pista cruzaba el interior del ICM y
# aislaba el plano de abajo; el firmware prueba 0x69 y 0x68). Los ejes X/Y del
# módulo quedan invertidos: el cero se toma montado igual, y el signo de
# pitch/roll se corrige en el visor si hace falta.
ix0, iy0 = 2.0, 48.0
icm = (row(4, 13.85, 1.89, [N['SDA'], N['SCL'], N['GND'], N['3V3']], horizontal=False) +
       row(4, 1.15, 1.89, [N['GND'], 0, 0, 0], horizontal=False, first=5))
part('U4', 'ICM-20689', ix0, iy0, icm, boxes=[
    (-0.12, 0.62, 2.42, 10.78, 0, SOCKET_H, BLACK),
    (12.58, 0.62, 15.12, 10.78, 0, SOCKET_H, BLACK),
    (0, 0, 15.0, 11.4, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, (.1, .1, .1))])

# === UART MUX 2 click (mikroBUS, filas a 22.86), bornera hacia la IZQUIERDA ==
# Girado 90° (2026-10-20): con la bornera hacia arriba quedaba inaccesible; da
# al borde izquierdo, como las otras borneras. Fila de arriba (izq → der):
# ON INV TX RX NC NC 5V GND; fila de abajo: OFF A1 A0 NC NC NC 3V3 GND. Así el
# TX mira a la Heltec y el 3V3 queda del lado del ICM. (Girado 180° el I2C, el
# VE y el OCR_RX se cruzaban: 19 puentes.)
# Footprint de Carlos (GIPIS_LIB UART_MUX_2_Click_MikroBUS_Socket): origen abajo
# al centro, pads 1-8 a la izq de arriba a abajo (OFF A1 A0 NC NC NC 3V3 GND) y
# 16-9 a la der de arriba a abajo (ON INV TX RX NC NC 5V GND), numeración
# mikroBUS. Mismas posiciones que el GIPIS_LIB; solo los pads son óvalos de
# 3.0 x 1.8 (los redondos de 2.0 dejan 0.54 entre pads, menos que la aislación).
# A0/A1 a GND = canal 1; alimentado de 3V3 (J3.3). TX del click → GPIO6 (J3.17).
cx0, cy0 = 43.9, 74.0      # origen del footprint (abajo al centro → extremo derecho)
# A1/A0 van al GND del propio click (pad 8, unido al 9 adentro del módulo): así
# no dependen de que el plano llegue a esa columna, que queda encerrada por pistas.
# Pads 2-3 (A1/A0) y 8 a GND; el 9 (GND, unido al 8 dentro del módulo) queda
# libre: su lado de la placa está encerrado por OCR_RX/3V3 y necesitaba un puente.
CLICK = {1: '', 2: 'GND', 3: 'GND', 4: '', 5: '', 6: '', 7: '3V3',
         8: 'GND', 9: '', 10: '', 11: '', 12: '', 13: '', 14: 'OCR_RX',
         15: '', 16: ''}
click = []
for n in list(range(1, 9)) + list(range(16, 8, -1)):   # orden físico (esquema)
    net = CLICK[n]
    x, y = (-11.43, -20.32 + P * (n - 1)) if n <= 8 else (11.43, -2.54 - P * (n - 9))
    click.append((str(n), x, y, N[net] if net else 0, 'rect_h' if n == 1 else 'ov_h'))
part('U2', 'UART_MUX_2_Click_MikroBUS_Socket', cx0, cy0, click, boxes=[
    (-12.70, -21.59, -10.16, -1.27, 0, SOCKET_H, BLACK),
    (10.16, -21.59, 12.70, -1.27, 0, SOCKET_H, BLACK),
    (-12.70, -42.90, 12.70, 0, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, GREEN),
    (-9.5, -42.90, 9.5, -35.9, MOD_ON_SOCKET + 1.6, MOD_ON_SOCKET + 9.6, BLUE)],  # bornera
    rot=90)

# === MicroSD HW-125 (5 V), tira a la izq, ranura de la tarjeta a la derecha ==
# Girada 180° (2026-10-20): con la ranura a la izq la tarjeta quedaba tapada
# por el click; ahora sale por el borde derecho de la placa.
# De arriba a abajo: GND VCC MISO MOSI SCK CS (así las 4 pistas de J3.7-10
# llegan sin cruzarse, sin tocar los GPIO).
sx0, sy0 = 61.4, 62.0
sd_nets = ['GND', 'VCC', 'MISO', 'MOSI', 'SCK', 'CS']
mapn = {'CS': 'SD_CS', 'SCK': 'SD_SCK', 'MOSI': 'SD_MOSI', 'MISO': 'SD_MISO',
        'VCC': '+5V', 'GND': 'GND'}
pads = [(str(i + 1), -3.95, 6.01 + P * i, N[mapn[a]], 'rect_h' if i == 0 else 'ov_h')
        for i, a in enumerate(sd_nets)]
part('U6', 'MICROSD', sx0, sy0, pads,
     boxes=[(-5.2, 4.7, -2.7, 20.0, 0, 8.5, BLACK),
            (0, 0, 42.1, 24.1, 3.0, 4.6, BLUE),
            (28.0, 5.0, 42.6, 19.0, 4.6, 7.0, SILVER)],
     holes=[(2.05, 2.05, 2.2), (40.05, 2.05, 2.2), (2.05, 22.05, 2.2), (40.05, 22.05, 2.2)])

# Pre-ruteo fijo (locked, Freerouting no lo toca): el +5V de la SD baja por el
# borde derecho y pasa por DEBAJO del módulo SD hasta VCC por la izquierda. Si
# Freerouting lo lleva por el lado de la Heltec encierra al click y el OCR_RX y
# el I2C terminan en puentes largos.
# Anchos = netclass del proyecto (.kicad_pro), +15 % pedido por Pablo 2026-10-20.
W_SIG, W_PWR = 0.92, 1.38
# Fila de abajo del click (pads 1-8) y su pad 7 (3V3) / 8 (GND).
yc = cy0 + 11.43
TRACKS = [# +5V: D2 → J2.2 (desde arriba) → entre las tiras por debajo de J2.1 → borde
          # derecho → por debajo de la SD → VCC de la SD por la izquierda. Pasar por
          # debajo de J2.1 deja el GND de la Heltec abierto al plano de arriba (por
          # encima lo encerraba), y por debajo de la SD no cruza el haz SPI.
          ('+5V', W_PWR, [(92.0, 22.58), (95.61, 26.19), (95.61, 34.6), (101.5, 34.6),
                          (101.5, 58.5), (99.0, 61.0), (99.0, 87.4), (54.0, 87.4),
                          (54.0, 70.56), (sx0 - 3.95, 70.56)]),
          # 3V3 de J3.3 al ICM: sube entre las tiras de la Heltec, sale por el extremo
          # (entre J3.18 y los pads AUX) y baja en diagonal al pin 4 del ICM.
          ('3V3', W_SIG, [(93.07, 54.18), (93.07, 51.34), (48.5, 51.34), (42.3, 57.51),
                          (15.85, 57.51)]),
          # 3V3 del ICM (pin 4) al 3V3 del click (pad 7, fila de abajo): baja por la
          # izquierda y entra entre las filas del click (abajo del módulo no hay pines).
          ('3V3', W_SIG, [(15.85, 57.51), (15.85, 74.5), (38.82, 74.5), (38.82, yc)]),
          # A1/A0 (pads 2-3) al GND del click (pad 8) por debajo de la fila de abajo,
          # sin cruzar el 3V3 que entra al pad 7.
          ('GND', W_SIG, [(26.12, yc), (28.66, yc)]),
          ('GND', W_SIG, [(28.66, yc), (28.66, yc + 2.82), (41.36, yc + 2.82), (41.36, yc)])]


def chaflan(pts, c=1.0):
    """Esquinas de 90° → dos de 45° (corta c mm de cada lado, o menos si el tramo es corto)."""
    out = [pts[0]]
    for a, v, b in zip(pts, pts[1:], pts[2:]):
        d1 = (v[0] - a[0], v[1] - a[1]); d2 = (b[0] - v[0], b[1] - v[1])
        l1, l2 = (d1[0] ** 2 + d1[1] ** 2) ** .5, (d2[0] ** 2 + d2[1] ** 2) ** .5
        if abs(d1[0] * d2[0] + d1[1] * d2[1]) > 1e-6 * l1 * l2:     # no es 90°
            out.append(v)
            continue
        k = min(c, l1 / 2, l2 / 2)
        out += [(round(v[0] - d1[0] / l1 * k, 3), round(v[1] - d1[1] / l1 * k, 3)),
                (round(v[0] + d2[0] / l2 * k, 3), round(v[1] + d2[1] / l2 * k, 3))]
    return out + [pts[-1]]


TRACKS = [(net, w, chaflan(pts)) for net, w, pts in TRACKS]

MOUNTING = [(3.5, 86.5), (48.0, 86.5), (3.5, 46.0), (100.5, 4.0)]

# Texto fresado en el cobre de abajo (espejado: se lee mirando el lado cobre), en
# el hueco entre D1 y el D-SUN donde solo hay plano. Trazo 0.8 = pista mínima.
TEXTS = [('GIPIS', 39.0, 4.2), ('OCR AEREO', 39.0, 9.0)]

# ---------------------------------------------------------------- emisión
PAD = {'ov_v': ('oval', 1.8, 3.0, 1.0), 'ov_h': ('oval', 3.0, 1.8, 1.0),
       'rect_v': ('rect', 1.8, 3.0, 1.0), 'rect_h': ('rect', 3.0, 1.8, 1.0),
       'big': ('circle', 2.6, 2.6, 1.2), 'big2': ('circle', 3.0, 3.0, 1.4),
       'cap': ('circle', 2.0, 2.0, 0.8),
       'to92': ('oval', 1.5, 2.4, 0.8)}


def u():
    return f'(tstamp "{uuid.uuid4()}")'


def wrl(path, boxes):
    """Cajas en VRML (unidad KiCad = 0.1 pulgada); Y invertida en 3D."""
    k = 1 / 2.54
    out = ['#VRML V2.0 utf8']
    for x0, y0, x1, y1, z0, z1, (r, g, b) in boxes:
        pts = [(x, -y, z) for z in (z0, z1) for (x, y) in
               ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        pts = ', '.join(f'{x*k:.4f} {y*k:.4f} {z*k:.4f}' for x, y, z in pts)
        faces = '0,1,2,3,-1, 7,6,5,4,-1, 0,4,5,1,-1, 1,5,6,2,-1, 2,6,7,3,-1, 3,7,4,0,-1'
        out.append(f'Shape {{ appearance Appearance {{ material Material {{ '
                   f'diffuseColor {r} {g} {b} }} }} geometry IndexedFaceSet {{ '
                   f'solid FALSE coord Coordinate {{ point [ {pts} ] }} '
                   f'coordIndex [ {faces} ] }} }}')
    open(path, 'w').write('\n'.join(out) + '\n')


def emit_part(p):
    s = f'  (footprint "nodo_b:{p["val"] or p["ref"]}" (layer "F.Cu") {u()} (at {p["x"]} {p["y"]}{f" {p['rot']}" if p["rot"] else ""})\n'
    s += '    (attr through_hole)\n'
    bx = [b[:4] for b in p['boxes']] or [(-2, -2, 2, 2)]
    x0 = min(b[0] for b in bx); y0 = min(b[1] for b in bx)
    x1 = max(b[2] for b in bx); y1 = max(b[3] for b in bx)
    (rx, ry, rr), (vx, vy, vr) = p['lbl'] or (((x0 + x1) / 2, (y0 + y1) / 2, 0),
                                              ((x0 + x1) / 2, (y0 + y1) / 2 + 1.5, 0))
    s += (f'    (fp_text reference "{p["ref"]}" (at {rx:.2f} {ry:.2f} {rr}) '
          f'(layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) {u()})\n')
    s += (f'    (fp_text value "{p["val"]}" (at {vx:.2f} {vy:.2f} {vr}) '
          f'(layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))) {u()})\n')
    s += (f'    (fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width 0.12) '
          f'(type solid)) (fill none) (layer "F.Fab") {u()})\n')
    for num, dx, dy, net, kind in p['pads']:
        shape, w, h, drill = PAD[kind]
        netref = f' (net {net} "{NETS[net]}")' if net else ''
        s += (f'    (pad "{num}" thru_hole {shape} (at {dx} {dy}{f" {p['rot']}" if p["rot"] else ""}) (size {w} {h}) '
              f'(drill {drill}) (layers "*.Cu" "*.Mask"){netref} {u()})\n')
    for dx, dy, d in p['holes']:
        s += (f'    (pad "" np_thru_hole circle (at {dx} {dy}) (size {d} {d}) '
              f'(drill {d}) (layers "*.Cu" "*.Mask") {u()})\n')
    if p['boxes']:
        wrl(os.path.join(D3, f'{p["ref"]}.wrl'), p['boxes'])
        s += (f'    (model "${{KIPRJMOD}}/3d/{p["ref"]}.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) '
              f'(rotate (xyz 0 0 0)))\n')
    return s + '  )\n'


def emit_hole(x, y, ref):
    return (f'  (footprint "nodo_b:M3" (layer "F.Cu") {u()} (at {x} {y})\n'
            f'    (attr through_hole board_only exclude_from_bom)\n'
            f'    (fp_text reference "{ref}" (at 0 -2.5) (layer "F.Fab") '
            f'(effects (font (size 1 1) (thickness 0.15))) {u()})\n'
            f'    (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) '
            f'(layers "*.Cu" "*.Mask") {u()})\n  )\n')


def emit_edge():
    c = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    return ''.join(f'  (gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) '
                   f'(layer "Edge.Cuts") (width 0.1) {u()})\n'
                   for a, b in zip(c, c[1:] + c[:1]))


HEADER = '''(kicad_pcb (version 20221018) (generator nodo_b)
  (general (thickness 1.6))
  (paper "A4")
  (layers
    (0 "F.Cu" signal) (31 "B.Cu" signal)
    (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user)
    (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user)
    (48 "B.Fab" user) (49 "F.Fab" user)
  )
  (setup (pad_to_mask_clearance 0))
'''


def chequeo():
    """Choques 3D entre cajas de piezas distintas, y cajas fuera de la placa."""
    errs = []
    absb = []
    for p in PARTS:
        for b in p['boxes']:
            if p['rot'] == 180:
                b = (-b[2], -b[3], -b[0], -b[1]) + tuple(b[4:])
            elif p['rot'] == 90:      # KiCad: (lx, ly) → (ly, -lx)
                b = (b[1], -b[2], b[3], -b[0]) + tuple(b[4:])
            absb.append((p['ref'], b[0] + p['x'], b[1] + p['y'], b[2] + p['x'],
                         b[3] + p['y'], b[4], b[5]))
    for i, a in enumerate(absb):
        for b in absb[i + 1:]:
            if a[0] == b[0]:
                continue
            if (a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]
                    and a[5] < b[6] and b[5] < a[6]):
                errs.append(f'choque {a[0]} / {b[0]}')
    for r, x0, y0, x1, y1, z0, z1 in absb:
        if (x0 < -0.01 or y0 < -0.01 or x1 > BOARD_W + 1.0 or y1 > BOARD_H + 0.01):
            errs.append(f'{r} fuera de la placa ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})')
    for hx, hy in MOUNTING:
        for r, x0, y0, x1, y1, z0, z1 in absb:
            if x0 - 2.0 < hx < x1 + 2.0 and y0 - 2.0 < hy < y1 + 2.0 and z0 < 3:
                errs.append(f'agujero M3 ({hx},{hy}) choca con {r}')
    return sorted(set(errs))


def main():
    out = HEADER + ''.join(f'  (net {i} "{n}")\n' for i, n in enumerate(NETS))
    out += ''.join(emit_part(p) for p in PARTS)
    out += ''.join(emit_hole(x, y, f'H{i + 1}') for i, (x, y) in enumerate(MOUNTING))
    for net, w, pts in TRACKS:
        out += ''.join(f'  (segment locked (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {w}) '
                       f'(layer "B.Cu") (net {N[net]}) {u()})\n' for a, b in zip(pts, pts[1:]))
    for t, x, y in TEXTS:
        out += (f'  (gr_text "{t}" (at {x} {y}) (layer "B.Cu") {u()}\n'
                f'    (effects (font (size 3.5 3.5) (thickness 0.8)) (justify mirror)))\n')
    out += emit_edge() + ')\n'
    open(os.path.join(HERE, 'nodo_b.kicad_pcb'), 'w').write(out)
    zmax = max(b[5] for p in PARTS for b in p['boxes'])
    print(f'nodo_b.kicad_pcb: {len(PARTS)} piezas, placa {BOARD_W} x {BOARD_H} mm, '
          f'altura máx {zmax} mm')
    for e in chequeo():
        print('  !', e)


if __name__ == '__main__':
    main()
