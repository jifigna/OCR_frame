#!/usr/bin/env python3
"""OCR Upwelling (frame: OCR Lu + BioShutter + inclinación) — generador del PCB, v2.

Parte de la placa de Juan Figna (jifigna/OCR_frame, OCR_AEREO_HELTEC_V1, 2026-10-20):
misma placa de 109,5 x 85,5 y misma ubicación de módulos, con las correcciones de la
revisión (pcb/juan/REVISION_OCR_frame_20261020.md) y el método del OCR Downwelling:
una sola cara (todo el cobre abajo, B.Cu) para la LPKF ProtoMat S63 sin metalizado,
pistas 0,92 / 1,38, aislación 0,6 (0,5 al plano de GND).

Cambios respecto de Juan: tiras de la Heltec a 22,86 y alineadas; I2C por los pads
AUX GPIO17/18; SD en GPIO 39-42; ICM con AD0 a Vext (0x69); SIN relés ni BioShutter
(el OCR toma 12 V directo, como el downwelling); fusible a la entrada de los 12 V, Schottky de inversión, buck corregido
(IN+ J11, GND J10, OUT J8, GND J9) → JP1 → Schottky → +5V; zener 5,6 V; borneras
Phoenix 5,08; ICM con tiras a 12,70.

Eje X a lo ancho, Y hacia abajo, origen arriba a la izquierda, vista superior.
"""

import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
D3 = os.path.join(HERE, '3d')

# ---------------------------------------------------------------- parámetros
BOARD_W, BOARD_H = 109.5, 85.5   # la de Juan
P = 2.54
SOCKET_H = 8.5          # tira hembra vertical 2.54
MOD_ON_SOCKET = 11.0    # base del módulo enchufado (hembra + plástico del macho)

# ---------------------------------------------------------------- nets
NETS = ["", "GND", "BATERIA", "F_OUT", "12V", "5V_JP", "+5V", "5V_TOP", "GND_RTC", "VE_B", "VE",
        "SDA", "SCL", "SDA_B", "SCL_B", "SD_CS", "SD_MOSI", "SD_MISO", "SD_SCK",
        "5V_HEL", "H_TX", "H_RX", "TX_OCR", "RX_OCR",
        "MAX_C1P", "MAX_C1N", "MAX_C2P", "MAX_C2N", "MAX_VSP", "MAX_VSN"]
N = {n: i for i, n in enumerate(NETS)}

# ---------------------------------------------------------------- piezas
# Una pieza: dict(ref, val, x, y, pads=[(num, dx, dy, net, kind)], boxes, holes)
#   kind: 'ov_v' oval alargado en Y (fila horizontal), 'ov_h' alargado en X
#         (fila vertical), 'rect_v'/'rect_h' pin 1, 'big' bornera/diodo,
#         'big2' diodo de 3 A, 'cap' componente chico, 'term' bornera Phoenix
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



def terminal_h(ref, val, x1, y, nets):
    """Bornera Phoenix MCV 1,5/n-G-5.08 vertical contra el borde de abajo (como J6/J7
    de Juan, girada 180°): pad 1 a la derecha, el cable entra por el borde."""
    n = len(nets)
    pads = [(str(i + 1), -BP * i, 0, N[a] if a else 0, 'term') for i, a in enumerate(nets)]
    part(ref, val, x1, y, pads,
         boxes=[(-BP * (n - 1) - 3.08, -3.46, 3.08, 2.4, 0, 9.0, GREEN)],
         lbl=((-BP * (n - 1) / 2, -4.6, 0), (-BP * (n - 1) / 2, -6.0, 0)))


def axial(ref, val, x, y, nets, pitch, vertical, body, kind='big', h=6, color=BLACK):
    """Axial acostado; pad 1 en (x, y) y pad 2 a `pitch` (abajo si vertical)."""
    d2 = (0, pitch) if vertical else (pitch, 0)
    bl, bd = body
    if vertical:
        bx = (-bd / 2, (pitch - bl) / 2, bd / 2, (pitch + bl) / 2)
        lb = ((bd / 2 + 1.0, pitch / 2, 90), (-bd / 2 - 1.0, pitch / 2, 90))
    else:
        bx = ((pitch - bl) / 2, -bd / 2, (pitch + bl) / 2, bd / 2)
        lb = ((pitch / 2, -bd / 2 - 1.0, 0), (pitch / 2, bd / 2 + 1.0, 0))
    part(ref, val, x, y, [('1', 0, 0, N[nets[0]], kind), ('2', d2[0], d2[1], N[nets[1]], kind)],
         boxes=[bx + (0.5, h, color)], lbl=lb)


BP = 5.08
W_SIG, W_PWR = 0.92, 1.38

# === Heltec V4 (USB-C a la derecha) ==========================================
# J2 arriba (y 12.52), J3 abajo, filas a 22.86 alineadas (Juan: 23.00 y corridas
# 0.5 mm). Pin 1 de las dos del lado del USB, en x = 106.08 (el JE1.18 de Juan).
# Pads AUX GPIO17/18 en el extremo opuesto al USB, del lado de J2 (pinout V4: de J3
# a J2 GPIO15, GPIO16, LED, GPIO17, GPIO18). Posición = downwelling (footprint de
# Carlos): MEDIR con la Heltec real (Juan los tiene 0.9 mm más abajo y SDA/SCL al revés).
HX, HY = 106.08, 12.52
j2 = {1: 'GND', 2: '5V_HEL', 3: 'VE', 4: 'VE'}
# J3.1 (GND) libre: la Heltec toma GND por J2.1 (es el mismo GND adentro del módulo).
j3 = {7: 'SD_CS', 8: 'SD_SCK', 9: 'SD_MOSI', 10: 'SD_MISO',
      16: 'H_TX', 17: 'H_RX'}
pads = []
for n in range(1, 19):
    x = -P * (n - 1)
    pads.append((f'A{n}', x, 0, N[j2[n]] if n in j2 else 0, 'rect_v' if n == 1 else 'ov_v'))
    pads.append((f'B{n}', x, 22.86, N[j3[n]] if n in j3 else 0, 'rect_v' if n == 1 else 'ov_v'))
xaux, ymid = -P * 18, 22.86 / 2
pads.append(('AUX17', xaux, ymid - 3.81, N['SDA'], 'ov_h'))
pads.append(('AUX18', xaux, ymid - 6.35, N['SCL'], 'ov_h'))
part('U1', 'HELTEC_V4', HX, HY, pads, boxes=[
    (-P * 17 - 1.27, -1.27, 1.27, 1.27, 0, SOCKET_H, BLACK),
    (-P * 17 - 1.27, 21.59, 1.27, 24.13, 0, SOCKET_H, BLACK),
    (xaux - 1.27, ymid - 7.62, xaux + 1.27, ymid - 2.54, 0, SOCKET_H, BLACK),
    (-50.25, -1.32, 1.55, 24.18, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, DARK),
    (-37.0, 3.0, -11.0, 20.0, MOD_ON_SOCKET + 1.6, MOD_ON_SOCKET + 3.6, BLACK),
    (-5.95, 7.2, 2.35, 15.7, MOD_ON_SOCKET + 1.6, MOD_ON_SOCKET + 4.8, SILVER)],
    lbl=((-22.0, 9.0, 0), (-22.0, 13.0, 0)))

# === MicroSD HW-125 (5 V), tira a la derecha, ranura al borde izquierdo ======
# Agujeros del módulo = los de Juan (2.71/40.71, 7.53/27.53). De arriba a abajo
# CS SCK MOSI MISO VCC GND (modelo del downwelling; Juan tiene GND arriba: VERIFICAR).
sx0, sy0 = 0.66, 5.48
sd_nets = ['GND', 'VCC', 'MISO', 'MOSI', 'SCK', 'CS']
mapn = {'CS': 'SD_CS', 'SCK': 'SD_SCK', 'MOSI': 'SD_MOSI', 'MISO': 'SD_MISO',
        'VCC': '5V_TOP', 'GND': 'GND'}
pads = [(str(i + 1), 46.05, 18.09 - P * i, N[mapn[a]], 'rect_h' if i == 0 else 'ov_h')
        for i, a in enumerate(sd_nets)]
part('U6', 'MICROSD', sx0, sy0, pads,
     boxes=[(44.8, 4.1, 47.3, 19.4, 0, 8.5, BLACK),
            (0, 0, 42.1, 24.1, 3.0, 4.6, BLUE),
            (-0.5, 5.1, 14.1, 19.1, 4.6, 7.0, SILVER)],
     holes=[(2.05, 2.05, 2.2), (40.05, 2.05, 2.2), (2.05, 22.05, 2.2), (40.05, 22.05, 2.2)],
     lbl=((24.0, 10.0, 0), (24.0, 13.0, 0)))

# === RTC ZS-042 (DS3231 0x68 + EEPROM 0x57), tira de Juan ===================
# De arriba a abajo GND VCC SDA SCL SQW 32K (SQW y 32K sin conectar: GPIO4 es del relé).
rtc = [(str(i + 1), 0, P * i, N[a] if a else 0, 'rect_h' if i == 0 else 'ov_h')
       for i, a in enumerate(['GND_RTC', 'VE_B', 'SDA_B', 'SCL_B', '', ''])]
part('U7', 'RTC_ZS-042', 53.47, 35.02, rtc,
     boxes=[(-1.27, -1.27, 1.27, P * 6 - 1.27, 0, SOCKET_H, BLACK),
            (-40.5, -4.5, 1.5, 16.5, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, BLUE),
            (-30.0, 0.0, -10.0, 13.0, 6.0, MOD_ON_SOCKET, SILVER)],        # pila abajo
     holes=[(15.02 - 53.47, 32.52 - 35.02, 2.2), (40.52 - 53.47, 32.52 - 35.02, 2.2),
            (40.52 - 53.47, 49.52 - 35.02, 2.2)],
     lbl=((-20.0, 6.0, 0), (-20.0, 9.0, 0)))

# === ICM-20689 (filas a 12.70), tiras de Juan (J1/J2) ========================
# Izquierda (x 8.02) de arriba a abajo VCC GND SCL SDA; derecha INT DA CL AD0.
# AD0 a Vext → 0x69 (con AD0 a GND quedaba en 0x68 = el DS3231).
icm = (row(4, 0, 0, [N['VE_B'], N['GND'], N['SCL_B'], N['SDA_B']], horizontal=False) +
       row(4, 12.7, 0, [0, 0, 0, N['VE_B']], horizontal=False, first=5))
part('U4', 'ICM-20689', 8.02, 55.21, icm, boxes=[
    (-1.27, -1.27, 1.27, P * 4 - 1.27, 0, SOCKET_H, BLACK),
    (11.43, -1.27, 13.97, P * 4 - 1.27, 0, SOCKET_H, BLACK),
    (-1.15, -1.89, 13.85, 9.51, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, (.1, .1, .1))],
    lbl=((6.35, 3.0, 0), (6.35, 5.5, 0)))

# === GY-511 (LSM303DLHC), tira de Juan (J12) =================================
# 1 DRDY 2 INT1 3 INT2 4 SDA 5 SCL 6 GND 7 3V3 (Vext) 8 VIN (orden de Juan: VERIFICAR).
gy = row(8, 0, 0, [0, 0, 0, N['SDA_B'], N['SCL_B'], N['GND'], N['VE_B'], 0])
part('U8', 'GY-511', 4.57, 67.53, gy,
     boxes=[(-1.27, -1.27, P * 8 - 1.27, 1.27, 0, SOCKET_H, BLACK),
            (-1.8, -1.6, 19.6, 13.0, MOD_ON_SOCKET, MOD_ON_SOCKET + 1.6, BLUE)],
     holes=[(5.37 - 4.57, 78.42 - 67.53, 2.2), (21.68 - 4.57, 78.42 - 67.53, 2.2)],
     lbl=((8.9, 4.0, 0), (8.9, 6.5, 0)))

# === Buck (módulo de Juan, 4 esquinas con tira de 2) =========================
# J11 IN+ (abajo izq), J10 GND/IN- (arriba izq), J8 OUT+ 5 V (abajo der), J9 GND/OUT-
# (arriba der) — corregido por Pablo 2026-10-20. Ajustar a ~5.3 V (cae la Schottky D3).
# IN− (J10) sin red: en el módulo IN− y OUT− son la misma tierra; va al plano por J9.
bk = [('1', 0, 0, 0, 'ov_h'), ('2', 0, 2.54, 0, 'ov_h'),          # J10
      ('3', 0, 10.77, N['12V'], 'ov_h'), ('4', 0, 13.31, 0, 'ov_h'),      # J11
      ('5', 19.5, -0.23, 0, 'ov_h'), ('6', 19.5, 2.31, N['GND'], 'ov_h'),  # J9
      ('7', 19.5, 10.77, N['+5V'], 'ov_h'), ('8', 19.5, 13.31, 0, 'ov_h')]  # J8
part('U5', 'BUCK', 36.02, 55.48, bk, boxes=[
    (-1.27, -1.27, 1.27, 3.81, 0, 2.5, BLACK), (-1.27, 9.5, 1.27, 14.58, 0, 2.5, BLACK),
    (18.23, -1.5, 20.77, 3.58, 0, 2.5, BLACK), (18.23, 9.5, 20.77, 14.58, 0, 2.5, BLACK),
    (-1.8, -1.8, 21.3, 15.1, 2.5, 4.1, GREEN), (7.0, 3.0, 12.5, 9.0, 4.1, 8.0, SILVER)],
    lbl=((9.75, 5.0, 0), (9.75, 7.5, 0)))

# === Entrada de 12 V: bornera → fusible → Schottky → 12V =====================
# Fusible a la ENTRADA (Juan lo tenía a la salida del buck). D1 Schottky 3 A
# (1N5822, DO-201AD como el 1N5402 de Juan). J7: el pad de la izquierda es BATERÍA.
terminal_h('J7', 'BATERIA', 34.12, 82.6, ['GND', 'BATERIA'])
axial('F1', 'FUSE_2A', 26.2, 54.19, ['F_OUT', 'BATERIA'], 15.24, True, (9.9, 3.6), 'big', 5, TAN)
axial('D1', '1N5822', 31.52, 54.4, ['F_OUT', '12V'], 15.24, True, (9.5, 5.3), 'big2', 6)
# Zener de 5 W sobre +5V (clamp): 1N5339B = 5.6 V (Juan: "1N53xxB" sin valor). K = +5V.
axial('D2', '1N5339B', 49.64, 74.53, ['+5V', 'GND'], -15.24, False, (8.5, 5.0), 'big2', 6)

# === +5V → JP1 → D3 (anti-retorno USB) → pin 5V de la Heltec =================
# Como el downwelling, pero el diodo protege solo la entrada de la Heltec: la SD, los
# relés y el zener toman +5V directo del buck. Sacar JP1 con la Heltec por USB hasta
# confirmar el diodo de VBUS de la V4. Arriba de la tira J2, donde hay lugar.
part('JP1', '5V_EXT', 86.0, 4.5, [('1', 0, 0, N['5V_TOP'], 'rect_v'), ('2', P, 0, N['5V_JP'], 'ov_v')],
     boxes=[(-1.27, -1.27, P + 1.27, 1.27, 0, 2.5, BLACK)], lbl=((1.27, -2.4, 0), (1.27, 2.6, 0)))
axial('D3', '1N5819', 92.5, 4.5, ['5V_JP', '5V_HEL'], 7.62, False, (5.2, 2.7), 'cap', 3)

# === Capacitores =============================================================
# C7 470 µF / 10 V electrolítico (Ø8, paso 3.5; el de Juan tenía footprint de Ø4)
part('C7', '470uF', 51.5, 5.0, [('1', 0, 0, N['5V_TOP'], 'big'), ('2', 3.5, 0, N['GND'], 'big')],
     boxes=[(-2.25, -4.0, 5.75, 4.0, 0.5, 12.5, BLACK)], lbl=((1.75, -5.0, 0), (1.75, 5.0, 0)))

# === MAX3232 (DIP-16, en zócalo), GIRADO 180° respecto de Juan =================
# Fila de abajo (y 64.19, izq → der): 9 R2OUT, 10 T2IN (a GND: entrada CMOS al aire),
# 11 T1IN ← GPIO5, 12 R1OUT → GPIO6, 13 R1IN ← TX del OCR, 14 T1OUT → RX del OCR,
# 15 GND, 16 VCC. Así la UART de la Heltec llega por la izquierda y la del OCR por la
# derecha sin cruzarse. Fila de arriba (y 54.02, der → izq): 1 C1+ ... 8 R2IN, con los
# capacitores de bombeo arriba, cada uno alineado con sus pines. Pin 1 arriba a la der.
mx = {1: 'MAX_C1P', 2: 'MAX_VSP', 3: 'MAX_C1N', 4: 'MAX_C2P', 5: 'MAX_C2N', 6: 'MAX_VSN',
      10: 'GND', 11: 'H_TX', 12: 'H_RX', 13: 'TX_OCR', 14: 'RX_OCR', 15: 'GND', 16: 'VE'}
pads = []
for k in range(1, 17):
    x = 92.41 - P * (k - 1) if k <= 8 else 74.63 + P * (k - 9)
    y = 54.02 if k <= 8 else 64.19
    pads.append((str(k), round(x - 74.63, 3), round(y - 64.19, 3), N[mx[k]] if k in mx else 0,
                 'rect_v' if k == 1 else 'ov_v'))
part('U2', 'MAX3232', 74.63, 64.19, pads,
     boxes=[(-1.6, -11.4, 19.4, 1.25, 0, 4.0, BLACK), (-0.6, -9.6, 18.4, -0.6, 4.0, 7.5, DARK)],
     lbl=((8.9, -4.0, 0), (8.9, -6.0, 0)))
axial('C5', '100n', 87.33, 49.4, ['MAX_C1N', 'MAX_C1P'], 5.08, False, (4.0, 2.5), 'cap', 6, YELLOW)
axial('C9', '100n', 71.2, 49.4, ['GND', 'MAX_VSN'], 5.08, False, (4.0, 2.5), 'cap', 6, YELLOW)
axial('C6', '100n', 79.71, 45.0, ['MAX_C2N', 'MAX_C2P'], 5.08, False, (4.0, 2.5), 'cap', 6, YELLOW)
axial('C8', '100n', 89.87, 45.0, ['MAX_VSP', 'GND'], 5.08, False, (4.0, 2.5), 'cap', 6, YELLOW)
# C4 (VCC del MAX3232), a la derecha del pin 16
axial('C4', '100n', 95.5, 57.0, ['VE', 'GND'], 5.08, True, (5.0, 2.5), 'cap', 6, YELLOW)

# (y = 82.6: 1 mm de cobre al borde; Juan las tenía en 83.03 con 0.5)
# === Bornera del OCR (Phoenix 5.08), en el BORDE DERECHO ====================
# SIN relés ni BioShutter (Pablo, 2026-10-20): el OCR toma los 12 V directo, como el
# downwelling. De arriba a abajo GND, RX, TX, +12V: RX y TX entran al MAX3232 por la
# derecha sin cruzarse y el 12V llega desde D1 por abajo. El cable entra por el borde.
def terminal_v(ref, val, x, y1, nets):
    n = len(nets)
    pads = [(str(i + 1), 0, BP * i, N[a] if a else 0, 'termh') for i, a in enumerate(nets)]
    part(ref, val, x, y1, pads,
         boxes=[(-2.4, -3.08, 3.46, BP * (n - 1) + 3.08, 0, 9.0, GREEN)],
         lbl=((-4.6, BP * (n - 1) / 2, 90), (-6.0, BP * (n - 1) / 2, 90)))


terminal_v('J6', 'OCR', 105.6, 55.0, ['GND', 'RX_OCR', 'TX_OCR', '12V'])

# === Puente de 5 V (W3): el +5V del buck no tiene cómo llegar a la SD/C7/JP1 sin
# cruzar el haz de la SD. Alambre de arriba de la tira J2 (y 9) a abajo del haz (y 32.4),
# al lado del extremo de la Heltec (pasa por arriba de los pads AUX: alambre aislado).
part('W3', 'PUENTE_5V', 60.6, 9.0, [('1', 0, 0, N['5V_TOP'], 'cap'), ('2', 0, 23.4, N['+5V'], 'cap')],
     boxes=[], lbl=((2.2, 11.0, 90), (3.8, 11.0, 90)))

# === Puente de Vext (W5): la UART de la Heltec, el +5V de W3 y el 12V encierran al
# MAX3232; el Vext de la izquierda (RTC, ICM, GY-511 → red VE_B) pasa por arriba.
part('W5', 'PUENTE_VE', 70.5, 41.5, [('1', 0, 0, N['VE'], 'cap'), ('2', 57.9 - 70.5, 0, N['VE_B'], 'cap')],
     boxes=[], lbl=((-6.3, -2.0, 0), (-6.3, -3.4, 0)))

# === Puente de GND del RTC (W4): su pad de GND queda encerrado entre el I2C, el VE,
# el haz de la SD y el +5V. Alambre del pad de al lado (GND_RTC) al plano, más abajo.
part('W4', 'PUENTE_GND', 56.8, 35.02, [('1', 0, 0, N['GND_RTC'], 'cap'), ('2', 0, 17.4, N['GND'], 'cap')],
     boxes=[], lbl=((2.2, 8.7, 90), (3.8, 8.7, 90)))

# === Puentes de alambre del I2C (W1 SCL, W2 SDA) =============================
# El haz de la SD (GPIO 39-42 → tira de la SD) y el I2C (pads AUX → RTC/ICM/GY-511)
# se cruzan sí o sí en una cara: el I2C pasa por arriba con un alambre. Son piezas
# de 2 pads (redes distintas: SCL / SCL_B), así quedan en el esquemático y el BOM.
# (el pad del lado de la Heltec va entre las tiras, a la derecha de los AUX)
part('W1', 'PUENTE_SCL', 63.6, 17.6, [('1', 0, 0, N['SCL'], 'cap'), ('2', 45.0 - 63.6, 31.0 - 17.6, N['SCL_B'], 'cap')],
     boxes=[], lbl=((-6.0, 6.0, 0), (-6.0, 8.0, 0)))
part('W2', 'PUENTE_SDA', 63.6, 20.6, [('1', 0, 0, N['SDA'], 'cap'), ('2', 51.5 - 63.6, 32.4 - 20.6, N['SDA_B'], 'cap')],
     boxes=[], lbl=((-2.5, 6.0, 0), (-2.5, 8.0, 0)))

# Pre-ruteos fijos (Freerouting no los toca).
# SD: de J3.7-10 suben entre las tiras, van a la izquierda por debajo de los pads AUX
# y entran a la tira de la SD por la derecha. CS arriba / MISO abajo en los dos
# extremos: con este orden de giros las 4 no se cruzan. Paso 2.0 (1.08 entre pistas).
def _sd(xp, yh, xv, ypin):
    return [(xp, HY + 22.86), (xp, yh), (xv, yh), (xv, ypin), (sx0 + 46.05, ypin)]
TRACKS = [# +5V: VCC de la SD → C7 → JP1 por arriba de la tira J2 (Freerouting no lo encontraba)
          # (sale del VCC de la SD por la izquierda de su tira, por debajo del módulo)
          ('5V_TOP', W_PWR, [(sx0 + 46.05, sy0 + 18.09 - P), (43.4, sy0 + 18.09 - P), (43.4, 8.2),
                             (86.0, 8.2), (86.0, 4.5)]),
          ('5V_TOP', W_PWR, [(51.5, 8.2), (51.5, 5.0)]),
          # W3 (puente de 5 V sobre el haz de la SD) → baja a la salida del buck (J8)
          # (x 60.6, 1.2 mm: deja un pasillo de 5 mm a la derecha de la tira del RTC)
          ('5V_TOP', W_PWR, [(60.6, 9.0), (60.6, 8.2)]),
          ('+5V', 1.2, [(60.6, 32.4), (60.6, 62.0), (56.35, 66.25), (36.02 + 19.5, 55.48 + 10.77)]),
          # GND del RTC → W4 (pad de al lado)
          ('GND_RTC', W_SIG, [(53.47, 35.02), (56.8, 35.02)]),
          # VE: de J2.3 entre las tiras por debajo de J2.2/J2.1 y por el borde derecho
          # (0.8 mm) hasta C4 y el VCC del MAX3232 (pin 16).
          ('VE', 0.8, [(HX - 2 * P, HY), (HX - 2 * P, HY + 3.0), (107.98, HY + 3.0), (107.98, 50.0),
                       (98.0, 50.0), (95.5, 52.5), (95.5, 57.0)]),
          ('VE', W_SIG, [(92.41, 64.19), (92.41, 57.0), (95.5, 57.0)]),
          ('VE', 0.8, [(98.0, 50.0), (98.0, 41.5), (70.5, 41.5)]),            # → W5
          ('VE_B', W_SIG, [(57.9, 41.5), (57.9, 38.6), (56.94, 37.56), (53.47, 37.56)]),  # W5 → RTC
          # 12V: de D1 (K) por abajo hasta el +12V de J6 (la bornera del OCR, borde derecho)
          ('12V', W_PWR, [(31.52, 69.64), (31.52, 77.6), (105.6, 77.6), (105.6, 70.24)]),
          # UART de la Heltec (GPIO5/6) al MAX3232 (pines 11/12 desde abajo, por la izquierda)
          ('H_TX', W_SIG, [(HX - P * 15, HY + 22.86), (HX - P * 15, 67.4), (79.71, 67.4), (79.71, 64.19)]),
          ('H_RX', W_SIG, [(HX - P * 16, HY + 22.86), (HX - P * 16, 69.4), (82.25, 69.4), (82.25, 64.19)]),
          # UART del OCR (J6) al MAX3232 (pines 14/13 desde abajo, por la derecha)
          ('RX_OCR', W_SIG, [(105.6, 60.08), (100.0, 60.08), (100.0, 67.4), (87.33, 67.4), (87.33, 64.19)]),
          ('TX_OCR', W_SIG, [(105.6, 65.16), (101.6, 65.16), (101.6, 69.4), (84.79, 69.4), (84.79, 64.19)]),
          ('SD_CS', W_SIG, _sd(HX - P * 6, 24.0, 55.6, sy0 + 18.09 - P * 5)),
          ('SD_SCK', W_SIG, _sd(HX - P * 7, 26.0, 53.6, sy0 + 18.09 - P * 4)),
          ('SD_MOSI', W_SIG, _sd(HX - P * 8, 28.0, 51.6, sy0 + 18.09 - P * 3)),
          ('SD_MISO', W_SIG, _sd(HX - P * 9, 30.0, 49.6, sy0 + 18.09 - P * 2))]
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

# Agujeros de esquina de la placa (los de los módulos van con cada módulo).
MOUNTING = [(2.52, 2.52, 2.2), (107.03, 2.52, 2.2), (2.52, 83.03, 2.2), (107.03, 83.03, 2.2)]

TEXTS = []

# ---------------------------------------------------------------- emisión
PAD = {'ov_v': ('oval', 1.8, 3.0, 1.0), 'ov_h': ('oval', 3.0, 1.8, 1.0),
       'rect_v': ('rect', 1.8, 3.0, 1.0), 'rect_h': ('rect', 3.0, 1.8, 1.0),
       'big': ('circle', 2.6, 2.6, 1.2), 'big2': ('circle', 3.0, 3.0, 1.4),
       'cap': ('circle', 2.0, 2.0, 0.8),
       'to92': ('oval', 1.5, 2.4, 0.8),
       'term': ('oval', 2.0, 3.6, 1.2),      # Phoenix MCV 5.08 (drill 1.2)
       'pin': ('circle', 1.8, 1.8, 1.0),
       'termh': ('oval', 3.6, 2.0, 1.2)}     # Phoenix en el borde derecho


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
    s = f'  (footprint "ocr_up:{p["val"] or p["ref"]}" (layer "F.Cu") {u()} (at {p["x"]} {p["y"]}{f" {p['rot']}" if p["rot"] else ""})\n'
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


def emit_hole(x, y, d, ref):
    return (f'  (footprint "ocr_up:M{int(d)}" (layer "F.Cu") {u()} (at {x} {y})\n'
            f'    (attr through_hole board_only exclude_from_bom)\n'
            f'    (fp_text reference "{ref}" (at 0 -2.5) (layer "F.Fab") '
            f'(effects (font (size 1 1) (thickness 0.15))) {u()})\n'
            f'    (pad "" np_thru_hole circle (at 0 0) (size {d} {d}) (drill {d}) '
            f'(layers "*.Cu" "*.Mask") {u()})\n  )\n')


def emit_edge():
    c = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    return ''.join(f'  (gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) '
                   f'(layer "Edge.Cuts") (width 0.1) {u()})\n'
                   for a, b in zip(c, c[1:] + c[:1]))


HEADER = '''(kicad_pcb (version 20221018) (generator ocr_up)
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
    for hx, hy, _ in MOUNTING:
        for r, x0, y0, x1, y1, z0, z1 in absb:
            if x0 - 2.0 < hx < x1 + 2.0 and y0 - 2.0 < hy < y1 + 2.0 and z0 < 3:
                errs.append(f'agujero M3 ({hx},{hy}) choca con {r}')
    return sorted(set(errs))


def main():
    out = HEADER + ''.join(f'  (net {i} "{n}")\n' for i, n in enumerate(NETS))
    out += ''.join(emit_part(p) for p in PARTS)
    out += ''.join(emit_hole(x, y, d, f'H{i + 1}') for i, (x, y, d) in enumerate(MOUNTING))
    for net, w, pts in TRACKS:
        out += ''.join(f'  (segment locked (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {w}) '
                       f'(layer "B.Cu") (net {N[net]}) {u()})\n' for a, b in zip(pts, pts[1:]))
    for t, x, y in TEXTS:
        out += (f'  (gr_text "{t}" (at {x} {y}) (layer "B.Cu") {u()}\n'
                f'    (effects (font (size 3.5 3.5) (thickness 0.8)) (justify mirror)))\n')
    out += emit_edge() + ')\n'
    open(os.path.join(HERE, 'ocr_up.kicad_pcb'), 'w').write(out)
    zmax = max(b[5] for p in PARTS for b in p['boxes'])
    print(f'ocr_up.kicad_pcb: {len(PARTS)} piezas, placa {BOARD_W} x {BOARD_H} mm, '
          f'altura máx {zmax} mm')
    for e in chequeo():
        print('  !', e)


if __name__ == '__main__':
    main()
