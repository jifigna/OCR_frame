#!/usr/bin/env python3
"""Esquemático KiCad (.kicad_sch) del nodo B, generado del netlist de gen_board.py.

Cada pieza es un símbolo rectangular con los pines numerados igual que los pads
del PCB (nombres de esquema.PIN) y cada pin termina en una etiqueta de red;
los pines libres llevan no-connect. El campo Footprint apunta al mismo
footprint del PCB (nodo_b:<valor>), así que el chequeo de paridad
esquemático↔PCB de KiCad (drc --schematic-parity) compara los dos.
Uso: python3 gen_sch.py   (deja nodo_b_ruteada.kicad_sch)
"""
import os
import uuid

import esquema as e
import gen_board as g

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = 'nodo_b_ruteada'
G = 2.54            # grilla
PIN_LEN = 2.54
ROOT = str(uuid.uuid4())


def u():
    return str(uuid.uuid4())


def snap(v):
    return round(v / G) * G


def fmt(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def font(size=1.27, extra=''):
    return f'(effects (font (size {size} {size})){extra})'


def sides(p):
    """Reparte los pads a izquierda/derecha según el LAYOUT de esquema.py."""
    mode = e.LAYOUT[p['ref']][2]
    pads = [(num, net) for num, _, _, net, _ in p['pads']]
    if mode == 'AB':
        return ([q for q in pads if q[0].startswith('A')],
                [q for q in pads if q[0].startswith('B')])
    if mode == 'LR':
        return pads[:1], pads[1:]
    if mode.startswith('L') and len(mode) > 1:
        k = int(mode[1:mode.index('R')])
        return pads[:k], pads[k:]
    if mode == 'L':
        return pads, []
    return [], pads


def pin_name(ref, num):
    return e.PIN.get(ref, {}).get(num, num).strip() or num


def geometry(p):
    left, right = sides(p)
    n = max(len(left), len(right))
    names = [pin_name(p['ref'], num) for num, _ in left + right]
    longest = max((len(s) for s in names), default=2)
    half_w = snap(max(5.08, longest * 1.0 + 2.54) / 2 + 1.27)
    if left and right:
        half_w = snap(max(half_w, longest * 0.8 + 3.81))
    h = G * (n + 1)
    return left, right, half_w, h


def lib_symbol(p, name):
    left, right, hw, h = geometry(p)
    top = h / 2
    s = [f'    (symbol "{name}" (pin_names (offset 0.762)) (in_bom yes) (on_board yes)',
         f'      (property "Reference" "{p["ref"][0] if p["ref"][0] in "RCDF" else "U"}" (at 0 {fmt(top + 1.27)} 0) {font()})',
         f'      (property "Value" "{p["val"]}" (at 0 {fmt(-top - 1.27)} 0) {font()})',
         f'      (property "Footprint" "" (at 0 0 0) {font(extra=" hide")})',
         f'      (property "Datasheet" "" (at 0 0 0) {font(extra=" hide")})',
         f'      (symbol "{name.split(":")[1]}_0_1"',
         f'        (rectangle (start {fmt(-hw)} {fmt(top)}) (end {fmt(hw)} {fmt(-top)})'
         f' (stroke (width 0.254) (type default)) (fill (type background))))',
         f'      (symbol "{name.split(":")[1]}_1_1"']
    for side, lst in (('L', left), ('R', right)):
        for i, (num, _) in enumerate(lst):
            y = top - G * (i + 1)
            x, ang = (-hw - PIN_LEN, 0) if side == 'L' else (hw + PIN_LEN, 180)
            s.append(f'        (pin passive line (at {fmt(x)} {fmt(y)} {ang}) (length {PIN_LEN})'
                     f' (name "{pin_name(p["ref"], num)}" {font(1.0)})'
                     f' (number "{num}" {font(1.0)}))')
    s += ['      )', '    )']
    return '\n'.join(s), left, right, hw, top


def label(net, x, y, side):
    ang, just = (180, 'right') if side == 'L' else (0, 'left')
    return (f'  (global_label "{net}" (shape passive) (at {fmt(x)} {fmt(y)} {ang}) (fields_autoplaced)'
            f' (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{u()}"))')


def main():
    libs, insts, labels = [], [], []
    for p in g.PARTS:
        ref = p['ref']
        name = f'nodo_b:{ref}_{p["val"]}'.replace(' ', '_')
        sym, left, right, hw, top = lib_symbol(p, name)
        libs.append(sym)
        lx, ly, _ = e.LAYOUT[ref]
        X, Y = snap(lx + hw + 12), snap(ly + top + 6)
        fp = f'nodo_b:{p["val"] or ref}'
        pins = ''.join(f'\n    (pin "{num}" (uuid "{u()}"))' for num, _ in left + right)
        insts.append(
            f'  (symbol (lib_id "{name}") (at {fmt(X)} {fmt(Y)} 0) (unit 1)'
            f' (in_bom yes) (on_board yes) (dnp no) (uuid "{u()}")\n'
            f'    (property "Reference" "{ref}" (at {fmt(X)} {fmt(Y - top - 1.27)} 0) {font()})\n'
            f'    (property "Value" "{p["val"]}" (at {fmt(X)} {fmt(Y + top + 1.27)} 0) {font()})\n'
            f'    (property "Footprint" "{fp}" (at {fmt(X)} {fmt(Y)} 0) {font(extra=" hide")})\n'
            f'    (property "Datasheet" "" (at {fmt(X)} {fmt(Y)} 0) {font(extra=" hide")})\n'
            f'{pins}\n'
            f'    (instances (project "{PROJ}" (path "/{ROOT}" (reference "{ref}") (unit 1))))\n  )')
        for side, lst in (('L', left), ('R', right)):
            for i, (num, net) in enumerate(lst):
                py = Y - (top - G * (i + 1))
                px = X - hw - PIN_LEN if side == 'L' else X + hw + PIN_LEN
                if net:
                    labels.append(label(g.NETS[net], px, py, side))
                else:
                    labels.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid "{u()}"))')

    notas = ('Nodo B (bote) — OCR 0222 Ed + PAR 231 + ICM-20689. Generado por gen_sch.py '
             'desde gen_board.py: NO editar a mano, regenerar.\\n'
             'Placa: LPKF ProtoMat S63, una cara (B.Cu) + puentes de alambre arriba (F.Cu).\\n'
             'I2C en GPIO17/18 (pads AUX de la V4, bus del OLED 0x3C): ICM-20689 0x68 (AD0=GND), ADS1115 0x48 (ADDR=GND).\\n'
             'SD por SPI: CS 42, SCK 41, MOSI 40, MISO 39. OCR (TX del click) -> GPIO6.\\n'
             'JP1: sacarlo con la notebook por USB hasta confirmar diodo en VBUS de la V4. '
             'D-SUN ajustado a ~5,3 V (cae ~0,3 V en D2).')
    out = [f'(kicad_sch (version 20231120) (generator "gen_sch.py") (generator_version "8.0")',
           f'  (uuid "{ROOT}")',
           '  (paper "A3")',
           '  (title_block (title "Nodo B — OCR + PAR (bote)") (company "GIPIS — UNPSJB")'
           ' (comment 1 "Campaña CONAE oct 2026"))',
           '  (lib_symbols', *libs, '  )',
           f'  (text "{notas}" (at 20 255 0) (effects (font (size 1.5 1.5)) (justify left bottom))'
           f' (uuid "{u()}"))',
           *insts, *labels,
           '  (sheet_instances (path "/" (page "1")))',
           ')']
    # descripción de cada pieza como texto suelto debajo del símbolo
    for p in g.PARTS:
        _, _, hw, top = lib_symbol(p, 'x:x')[1:]
        lx, ly, _ = e.LAYOUT[p['ref']]
        X, Y = snap(lx + hw + 12), snap(ly + top + 6)
        out.insert(-2, f'  (text "{e.TITULO.get(p["ref"], "")}" (at {fmt(X)} {fmt(Y + top + 3.81)} 0)'
                       f' (effects (font (size 1 1) italic)) (uuid "{u()}"))')
    path = os.path.join(HERE, f'{PROJ}.kicad_sch')
    open(path, 'w').write('\n'.join(out) + '\n')
    # misma definición como librería del proyecto (sym-lib-table → nodo_b)
    sym = '\n'.join(s.replace('(symbol "nodo_b:', '(symbol "', 1) for s in libs)
    open(os.path.join(HERE, 'nodo_b.kicad_sym'), 'w').write(
        f'(kicad_symbol_lib (version 20231120) (generator "gen_sch.py")\n{sym}\n)\n')
    print(f'{PROJ}.kicad_sch: {len(g.PARTS)} símbolos, {len(labels)} etiquetas/no-connect')


if __name__ == '__main__':
    main()
