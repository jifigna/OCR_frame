#!/usr/bin/env python3
"""Esquemático del nodo B, dibujado a partir del netlist de gen_board.py.

No hay .kicad_sch: la placa se genera directo desde el código. Este script
lee PARTS/NETS de gen_board y dibuja cada pieza con sus pines (nombre del pin
del módulo + red), al estilo etiquetas de red, más la tabla de conexiones por
red. Sale out/esquematico.svg / .pdf y out/netlist.txt.
Uso: python3 esquema.py
"""
import html
import os
import subprocess

import gen_board as g

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

# Nombre de cada pin, tal como está serigrafiado/documentado en el módulo.
PIN = {
    'J1': {'1': '+12V bat', '2': 'GND'},
    'F1': {'1': '1', '2': '2'},
    'D1': {'1': 'A', '2': 'K'},
    'J2': {'1': 'GND', '2': '+12V OCR'},
    'J3': {'1': 'V+ (pin 4)', '2': 'AGND (pin 3)'},
    'J4': {'1': 'Señal (pin 2)', '2': 'GND (pin 1)'},
    'R1': {'1': '1', '2': '2'},
    'R2': {'1': '1', '2': '2'},
    'C1': {'1': '1', '2': '2'},
    'U3': dict(zip(map(str, range(1, 11)),
                   ['VDD', 'GND', 'SCL', 'SDA', 'ADDR', 'ALRT', 'A0', 'A1', 'A2', 'A3'])),
    'U5': {'1': 'IN−', '2': 'IN−', '3': 'IN+', '4': 'IN+',
           '5': 'OUT−', '6': 'OUT−', '7': 'OUT+', '8': 'OUT+'},
    'JP1': {'1': '1', '2': '2'},
    'D2': {'1': 'A', '2': 'K'},
    'U4': dict(zip(map(str, range(1, 9)),
                   ['SDA', 'SCL', 'GND', 'VCC', 'AD0', 'CL', 'DA', 'INT'])),
    'U2': dict(zip(map(str, range(1, 17)),
                   ['OFF', 'A1', 'A0', 'NC', 'NC', 'NC', '3V3', 'GND',
                    'GND', '5V', 'NC', 'NC', 'RX', 'TX', 'INV', 'ON'])),
    'U6': dict(zip(map(str, range(1, 7)), ['GND', 'VCC', 'MISO', 'MOSI', 'SCK', 'CS'])),
}
HELTEC_J2 = {1: 'GND', 2: '5V', 3: 'Ve', 4: 'Ve'}
HELTEC_J3 = {1: 'GND', 2: '3V3', 3: '3V3', 7: 'GPIO42', 8: 'GPIO41', 9: 'GPIO40', 10: 'GPIO39', 17: 'GPIO6'}
PIN['U1'] = {}
for n in range(1, 19):
    PIN['U1'][f'A{n}'] = f'J2.{n} ' + HELTEC_J2.get(n, '')
    PIN['U1'][f'B{n}'] = f'J3.{n} ' + HELTEC_J3.get(n, '')
PIN['U1']['AUX17'] = 'AUX GPIO17 (SDA)'
PIN['U1']['AUX18'] = 'AUX GPIO18 (SCL)'

TITULO = {
    'J1': 'Bornera batería 12 V', 'F1': 'Fusible 1 A', 'D1': '1N5819 (inversión)',
    'J2': 'Bornera alim. OCR 0222', 'J3': 'Bornera PAR 231 (alim.)', 'J4': 'Bornera PAR 231 (señal)',
    'R1': '10k divisor', 'R2': '10k divisor', 'C1': '22n cerámico',
    'U3': 'ADS1115 (0x48)', 'U5': 'D-SUN buck 12→5.3 V', 'JP1': 'Jumper 5V_EXT',
    'D2': '1N5819 (anti-retorno USB)', 'U1': 'Heltec WiFi LoRa 32 V4',
    'U4': 'ICM-20689 (AD0=0 → 0x68)', 'U2': 'UART MUX 2 click (canal 1)',
    'U6': 'MicroSD HW-125 (5 V)',
}

# Ubicación en la hoja (mm, A3 apaisada) y lado de cada pin (L/R).
LAYOUT = {
    'J1': (20, 40, 'R'), 'F1': (110, 40, 'LR'), 'D1': (185, 40, 'LR'),
    'U5': (110, 75, 'L4R4'), 'JP1': (110, 125, 'LR'), 'D2': (185, 125, 'LR'),
    'J2': (20, 165, 'R'), 'J3': (20, 195, 'R'), 'J4': (20, 220, 'R'),
    'R1': (110, 160, 'LR'), 'R2': (110, 180, 'LR'), 'C1': (110, 200, 'LR'),
    'U3': (185, 160, 'R'),
    'U1': (268, 35, 'AB'),
    'U4': (378, 40, 'L'), 'U2': (292, 165, 'L8R8'), 'U6': (378, 110, 'L'),
}

COL = {'GND': '#222', 'GND_CLICK': '#555'}
for n in ('12V_IN', 'F_OUT', '12V'):
    COL[n] = '#c0392b'
for n in ('5V_DSUN', '5V_JP', '+5V'):
    COL[n] = '#d35400'
for n in ('VE', '3V3'):
    COL[n] = '#b7950b'
for n in ('SDA', 'SCL'):
    COL[n] = '#1f5fbf'
for n in ('SD_CS', 'SD_MOSI', 'SD_MISO', 'SD_SCK'):
    COL[n] = '#1e8449'
for n in ('OCR_RX', 'PAR_SIG', 'PAR_DIV'):
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
    t(12, 16, 'Nodo B (bote) — OCR 0222 Ed + PAR 231 + inclinación · esquemático', 5, weight='bold')
    t(12, 22, 'Generado de gen_board.py (mismo netlist que nodo_b_ruteada.kicad_pcb). '
          'Mismo nombre de red = conectado. Número gris = pad del footprint. × = sin conectar.',
      2.6, fill='#555')
    for p in g.PARTS:
        if p['ref'] in LAYOUT:
            block(p)
    nota(12, 236, [
        'Alimentación',
        '12V_IN → F1 → D1 → 12V → D-SUN (ajustar a ~5.3 V) → JP1 → D2 → +5V → Heltec 5V y SD.',
        'OCR y PAR toman 12 V directo. ADS1115 va de Ve (3.3 V que prende el',
        'firmware); ICM y click del 3V3 de la Heltec (J3.2/3). Sacar JP1 si la Heltec está por USB (hasta confirmar',
        'el diodo de VBUS de la V4).',
    ], 128)
    nota(146, 236, [
        'Señales',
        'I2C (bus del OLED): SDA = GPIO17, SCL = GPIO18 (pads AUX) → ADS1115 0x48 + ICM-20689 0x68.',
        'SD (SPI): CS 42 · SCK 41 · MOSI 40 · MISO 39.',
        'OCR: la señal RS-232 entra por la bornera del propio click (cable, no PCB);',
        'TX del click → GPIO6. A0/A1 = GND → canal 1. PAR 0–5 V → R1/R2 → 0–2.5 V a A0.',
    ], 132)
    nota(284, 236, [
        'Fabricación (LPKF, doble faz sin metalizar)',
        'Pistas abajo (B.Cu) + plano de GND abajo.',
        'Lo que hay en F.Cu son puentes de alambre entre vías,',
        'NO pistas: los zócalos se sueldan solo abajo.',
        'Click: GND por el pin 8; el 9 queda libre (unidos dentro del módulo).',
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
    lines = ['Nodo B — conexiones por red (de gen_board.py)', '']
    for n in g.NETS[1:]:
        if n in nets:
            lines.append(f'{n}')
            lines += [f'    {s}' for s in nets[n]]
    open(os.path.join(OUT, 'netlist.txt'), 'w').write('\n'.join(lines) + '\n')
    print('out/esquematico.{svg,pdf,png}  out/netlist.txt')


if __name__ == '__main__':
    main()
