#!/usr/bin/env python3
"""Esquemático del OCR Upwelling v2, dibujado a partir del netlist de gen_board.py.

No hay .kicad_sch: la placa se genera directo desde el código. Este script
lee PARTS/NETS de gen_board y dibuja cada pieza con sus pines (nombre del pin
del módulo + red), al estilo etiquetas de red, más la tabla de conexiones por
red. Sale out/esquematico.svg / .pdf y out/netlist.txt.
Uso: python3 esquema.py
"""
import html
import json
import os
import subprocess

import gen_board as g

# Alambres que convertir_alambres.py sacó del ruteo (W6...): van al esquemático
# como piezas de 2 pines en la misma red (puente de alambre).
_AL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'alambres.json')
ALAMBRES = json.load(open(_AL)) if os.path.exists(_AL) else []
for _w in ALAMBRES:
    _n = g.N[_w['net']]
    g.PARTS.append(dict(ref=_w['ref'], val='ALAMBRE', x=_w['a'][0], y=_w['a'][1], rot=0, lbl=None,
                        boxes=[], holes=[],
                        pads=[('1', 0, 0, _n, 'cap'),
                              ('2', round(_w['c'][0] - _w['a'][0], 3), round(_w['c'][1] - _w['a'][1], 3), _n, 'cap')]))

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

# Nombre de cada pin, tal como está serigrafiado/documentado en el módulo.
PIN = {
    'J7': {'1': 'GND', '2': '+12V bat'},
    'F1': {'1': '1', '2': '2'},
    'D1': {'1': 'A', '2': 'K'},
    'D2': {'1': 'K', '2': 'A'},
    'D3': {'1': 'A', '2': 'K'},
    'JP1': {'1': '1', '2': '2'},
    'C7': {'1': '+', '2': '−'},
    'C4': {'1': '1', '2': '2'}, 'C5': {'1': '1', '2': '2'}, 'C6': {'1': '1', '2': '2'},
    'C8': {'1': '1', '2': '2'}, 'C9': {'1': '1', '2': '2'},
    'U5': {'1': 'IN− (J10)', '2': 'J10.2', '3': 'IN+ (J11)', '4': 'J11.2',
           '5': 'J9.1', '6': 'OUT− (J9)', '7': 'OUT+ (J8)', '8': 'J8.2'},
    'U2': dict(zip(map(str, range(1, 17)),
                   ['C1+', 'V+', 'C1−', 'C2+', 'C2−', 'V−', 'T2OUT', 'R2IN',
                    'R2OUT', 'T2IN', 'T1IN', 'R1OUT', 'R1IN', 'T1OUT', 'GND', 'VCC'])),
    'U4': dict(zip(map(str, range(1, 9)), ['VCC', 'GND', 'SCL', 'SDA', 'INT', 'DA', 'CL', 'AD0'])),
    'U8': dict(zip(map(str, range(1, 9)), ['DRDY', 'INT1', 'INT2', 'SDA', 'SCL', 'GND', '3V3', 'VIN'])),
    'U7': dict(zip(map(str, range(1, 7)), ['GND', 'VCC', 'SDA', 'SCL', 'SQW', '32K'])),
    'U6': dict(zip(map(str, range(1, 7)), ['GND', 'VCC', 'MISO', 'MOSI', 'SCK', 'CS'])),
    'J6': {'1': 'GND', '2': 'RX OCR', '3': 'TX OCR', '4': '+12V OCR'},
    'W1': {'1': '1', '2': '2'}, 'W2': {'1': '1', '2': '2'}, 'W3': {'1': '1', '2': '2'}, 'W4': {'1': '1', '2': '2'}, 'W5': {'1': '1', '2': '2'},
}
HELTEC_J2 = {1: 'GND', 2: '5V', 3: 'Ve', 4: 'Ve'}
HELTEC_J3 = {1: 'GND', 7: 'GPIO42', 8: 'GPIO41', 9: 'GPIO40', 10: 'GPIO39',
             16: 'GPIO5', 17: 'GPIO6'}
PIN['U1'] = {}
for n in range(1, 19):
    PIN['U1'][f'A{n}'] = f'J2.{n} ' + HELTEC_J2.get(n, '')
    PIN['U1'][f'B{n}'] = f'J3.{n} ' + HELTEC_J3.get(n, '')
PIN['U1']['AUX17'] = 'AUX GPIO17 (SDA)'
PIN['U1']['AUX18'] = 'AUX GPIO18 (SCL)'

TITULO = {
    'J7': 'Bornera batería 12 V', 'F1': 'Fusible 2 A (entrada)', 'D1': '1N5822 (inversión, 3 A)',
    'U5': 'Buck 12→5.3 V', 'D2': '1N5339B zener 5.6 V (clamp)', 'C7': '470 µF / 10 V',
    'JP1': 'Jumper 5V_EXT', 'D3': '1N5819 (anti-retorno USB)', 'C4': '100 nF (Vext)',
    'U2': 'MAX3232 (RS-232 del OCR)', 'C5': '100 nF', 'C6': '100 nF', 'C8': '100 nF', 'C9': '100 nF',
'U1': 'Heltec WiFi LoRa 32 V4',
    'U6': 'MicroSD HW-125 (5 V)', 'U4': 'ICM-20689 (AD0=1 → 0x69)', 'U7': 'RTC ZS-042 (DS3231 0x68)',
    'U8': 'GY-511 LSM303DLHC', 'J6': 'Bornera OCR (12 V directo)', 'W1': 'Puente de alambre (I2C SCL)', 'W2': 'Puente de alambre (I2C SDA)', 'W3': 'Puente de alambre (5 V a la SD)', 'W4': 'Puente de alambre (GND del RTC)', 'W5': 'Puente de alambre (Vext a RTC/ICM/GY)',
}

# Ubicación en la hoja (mm, A3 apaisada) y lado de cada pin (L/R).
LAYOUT = {
    'J7': (20, 38, 'R'), 'J6': (20, 70, 'R'), 'W1': (20, 175, 'LR'), 'W2': (20, 195, 'LR'), 'W3': (20, 215, 'LR'), 'W4': (20, 235, 'LR'),
    'F1': (95, 38, 'LR'), 'D1': (95, 58, 'LR'), 'U5': (95, 82, 'L4R4'), 'D2': (95, 132, 'LR'),
    'C7': (95, 152, 'LR'), 'JP1': (95, 172, 'LR'), 'D3': (95, 192, 'LR'), 'C4': (95, 212, 'LR'),
    'U2': (180, 38, 'L8R8'), 'C5': (180, 96, 'LR'), 'C6': (180, 116, 'LR'), 'C8': (180, 136, 'LR'),
    'C9': (180, 156, 'LR'),
    'U1': (268, 35, 'AB'),
    'W5': (268, 140, 'LR'),
    'U6': (378, 38, 'L'), 'U4': (378, 80, 'L'), 'U7': (378, 130, 'L'), 'U8': (378, 170, 'L'),
}

for _i, _w in enumerate(ALAMBRES):
    LAYOUT[_w['ref']] = (268, 158 + 18 * _i, 'LR')
    PIN[_w['ref']] = {'1': '1', '2': '2'}
    TITULO[_w['ref']] = f"Alambre ({_w['net']}, {_w['largo']} mm)"

COL = {'GND': '#222', 'GND_RTC': '#555'}
for n in ('BATERIA', 'F_OUT', '12V'):
    COL[n] = '#c0392b'
for n in ('+5V', '5V_JP', '5V_HEL', '5V_TOP'):
    COL[n] = '#d35400'
COL['VE'] = COL['VE_B'] = '#b7950b'
for n in ('SDA', 'SCL', 'SDA_B', 'SCL_B'):
    COL[n] = '#1f5fbf'
for n in ('SD_CS', 'SD_MOSI', 'SD_MISO', 'SD_SCK'):
    COL[n] = '#1e8449'
for n in ('H_TX', 'H_RX', 'TX_OCR', 'RX_OCR'):
    COL[n] = '#7d3c98'

PITCH, BOXW, STUB = 4.4, 34, 7
S = []


def t(x, y, s, size=2.6, anchor='start', weight='normal', fill='#111'):
    S.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
             f'font-weight="{weight}" fill="{fill}" font-family="DejaVu Sans, sans-serif">'
             f'{html.escape(s)}</text>')


def label(x, y, net, side):
    """Etiqueta de red con punta hacia el pin."""
    c = COL.get(net, '#333')
    w = 3.8 + 1.72 * len(net)
    h = 3.4
    if side == 'L':   # etiqueta a la izquierda del cable
        x1, x0 = x, x - w
        pts = f'{x1},{y} {x1-1.6},{y-h/2} {x0},{y-h/2} {x0},{y+h/2} {x1-1.6},{y+h/2}'
        tx = x0 + 0.8
    else:
        x0, x1 = x, x + w
        pts = f'{x0},{y} {x0+1.6},{y-h/2} {x1},{y-h/2} {x1},{y+h/2} {x0+1.6},{y+h/2}'
        tx = x0 + 2.2
    S.append(f'<polygon points="{pts}" fill="white" stroke="{c}" stroke-width="0.35"/>')
    t(tx, y + 0.9, net, 2.4, fill=c, weight='bold')


def pin(xb, y, name, num, net, side):
    xe = xb - STUB if side == 'L' else xb + STUB
    if net:
        S.append(f'<line x1="{xb}" y1="{y}" x2="{xe}" y2="{y}" stroke="{COL.get(net, "#333")}" stroke-width="0.4"/>')
        label(xe, y, net, side)
    else:
        S.append(f'<line x1="{xb}" y1="{y}" x2="{xe+(2 if side=="L" else -2)}" y2="{y}" stroke="#aaa" stroke-width="0.3"/>')
        xm = xe + (2 if side == 'L' else -2)
        S.append(f'<path d="M{xm-1},{y-1} l2,2 M{xm-1},{y+1} l2,-2" stroke="#aaa" stroke-width="0.35"/>')
    # nombre adentro de la caja, número afuera sobre el cable
    if side == 'L':
        t(xb + 1.2, y + 0.9, name, 2.4)
        t(xb - 1.0, y - 0.6, num, 1.8, 'end', fill='#777')
    else:
        t(xb - 1.2, y + 0.9, name, 2.4, 'end')
        t(xb + 1.0, y - 0.6, num, 1.8, fill='#777')


def block(p):
    ref = p['ref']
    x, y, mode = LAYOUT[ref]
    pads = [(num, NET) for num, _, _, NET, _ in p['pads']]
    if mode == 'AB':
        left = [q for q in pads if q[0].startswith('A')]
        right = [q for q in pads if q[0].startswith('B')]
    elif mode == 'LR':
        left, right = pads[:1], pads[1:]
    elif mode.startswith('L') and len(mode) > 1:
        k = int(mode[1:mode.index('R')])
        left, right = pads[:k], pads[k:]
    elif mode == 'L':
        left, right = pads, []
    else:
        left, right = [], pads
    n = max(len(left), len(right))
    w = 52 if mode == 'AB' else (22 if mode == 'LR' else (30 if mode == 'L' else BOXW))
    h = PITCH * n + 3
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fbf8ef" stroke="#333" stroke-width="0.45"/>')
    t(x, y - 4.2, ref, 3.0, weight='bold')
    t(x + 1.0 + 1.9 * len(ref), y - 4.2, TITULO.get(ref, p['val']), 2.4, fill='#444')
    for side, lst, xb in (('L', left, x), ('R', right, x + w)):
        for i, (num, net) in enumerate(lst):
            yy = y + 3.4 + PITCH * i
            pin(xb, yy, PIN[ref].get(num, num).strip(), num, g.NETS[net] if net else '', side)


def nota(x, y, lines, w=120):
    h = 4.2 * len(lines) + 4
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f4f6f9" stroke="#99a" stroke-width="0.3" rx="1.5"/>')
    for i, s in enumerate(lines):
        t(x + 2.5, y + 5 + 4.2 * i, s, 2.5, weight='bold' if i == 0 else 'normal')


def main():
    W, H = 420, 297
    S.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    S.append(f'<rect x="5" y="5" width="{W-10}" height="{H-10}" fill="none" stroke="#333" stroke-width="0.5"/>')
    t(12, 16, 'OCR Upwelling (frame) — OCR Lu + inclinación · esquemático v2 (sin relés)', 5, weight='bold')
    t(12, 22, 'Generado de gen_board.py (mismo netlist que ocr_up_ruteada.kicad_pcb), sobre la placa de '
          'Juan Figna. Mismo nombre de red = conectado. Número gris = pad. × = sin conectar.',
      2.6, fill='#555')
    for p in g.PARTS:
        if p['ref'] in LAYOUT:
            block(p)
    nota(12, 232, [
        'Alimentación',
        'Batería → F1 (2 A) → D1 1N5822 → 12V → OCR (J6) directo y buck (≈5.3 V) → +5V (zener D2)',
        '→ W3 → 5V_TOP: SD y C7 → JP1 → D3 1N5819 → 5V_HEL → pin 5V de la Heltec (sacar JP1 por USB).',
        'Vext (Ve): MAX3232, ICM, GY-511 y RTC. Sin relés ni BioShutter: el OCR queda',
        'prendido mientras haya batería.',
    ], 132)
    nota(150, 232, [
        'Señales',
        'I2C (OLED): SDA = GPIO17, SCL = GPIO18 (AUX) → puentes W1/W2 → ICM 0x69, GY-511, RTC 0x68.',
        'SD (SPI): CS 42 · SCK 41 · MOSI 40 · MISO 39. OCR: GPIO5 → T1IN, R1OUT → GPIO6 (MAX3232).',
        'Sin conectar: INT del ICM y del GY-511, SQW y 32K del RTC (el firmware hace polling).',
    ], 128)
    nota(284, 232, [
        'Fabricación (LPKF, doble faz sin metalizar)',
        'Cobre abajo (B.Cu) + plano de GND; arriba pocos tramos entre vías',
        '(alambre en cada vía). Los zócalos se sueldan solo abajo.',
        'W1-W5: puentes de alambre aislado del lado de componentes.',
    ], 124)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
           f'viewBox="0 0 {W} {H}">\n' + '\n'.join(S) + '\n</svg>\n')
    sp = os.path.join(OUT, 'esquematico.svg')
    open(sp, 'w').write(svg)
    subprocess.run(['rsvg-convert', '-f', 'pdf', sp, '-o', os.path.join(OUT, 'esquematico.pdf')], check=True)
    subprocess.run(['rsvg-convert', '-w', '3000', '-b', 'white', sp, '-o',
                    os.path.join(OUT, 'esquematico.png')], check=True)

    # Netlist legible: red → pines
    nets = {}
    for p in g.PARTS:
        for num, _, _, net, _ in p['pads']:
            if net:
                nombre = PIN.get(p['ref'], {}).get(num, num).strip()
                nets.setdefault(g.NETS[net], []).append(f'{p["ref"]}.{num} ({nombre})')
    lines = ['OCR Upwelling v2 — conexiones por red (de gen_board.py)', '']
    for n in g.NETS[1:]:
        if n in nets:
            lines.append(f'{n}')
            lines += [f'    {s}' for s in nets[n]]
    open(os.path.join(OUT, 'netlist.txt'), 'w').write('\n'.join(lines) + '\n')
    print('out/esquematico.{svg,pdf,png}  out/netlist.txt')


if __name__ == '__main__':
    main()
