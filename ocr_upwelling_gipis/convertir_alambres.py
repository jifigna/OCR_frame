#!/usr/bin/env python3
"""Deja ocr_up_ruteada en UNA SOLA CARA: cada cadena de tramos F.Cu entre dos vías
(los "puentes" que deja route.py y los de GND de fix_islas.py) pasa a ser un componente
de alambre W<n> con 2 pads en el lugar de las vías, los dos en la misma red y unidos
como puente (jumper_pad_groups: KiCad 9+ los da por conectados en el DRC). Se borran
las vías y el cobre de arriba, y se vuelve a rellenar el plano.

Deja out/alambres.json (ref, red, extremos, largo) para el esquemático y el LEEME.
Uso: python3 convertir_alambres.py   (después de fix_islas.py)
"""
import collections
import json
import os
import uuid

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, 'ocr_up_ruteada.kicad_pcb')
PRIMER_W = 6                 # W1-W5 son los puentes fijos de gen_board.py
MM = pcbnew.ToMM

b = pcbnew.LoadBoard(F)
tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.F_Cu]
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']


def k(p):
    return (round(MM(p.x), 3), round(MM(p.y), 3))


ady = collections.defaultdict(list)
for t in tracks:
    ady[k(t.GetStart())].append((k(t.GetEnd()), t))
    ady[k(t.GetEnd())].append((k(t.GetStart()), t))
via_net = {k(v.GetPosition()): v.GetNetname() for v in vias}

alambres, usados = [], set()
for p0 in sorted(via_net):
    for q, t in ady.get(p0, []):
        if id(t) in usados:
            continue
        usados.add(id(t))
        largo, cur = MM(t.GetLength()), q
        while cur not in via_net:
            sig = [(r, u) for r, u in ady[cur] if id(u) not in usados]
            if not sig:
                break
            cur, u = sig[0]
            usados.add(id(u))
            largo += MM(u.GetLength())
        alambres.append(dict(net=t.GetNetname(), a=p0, c=cur, largo=round(largo, 1)))

en_uso = {k(v.GetPosition()) for v in vias}
for t in tracks + vias:
    b.Remove(t)
pcbnew.SaveBoard(F, b)

# Footprints de alambre (por texto: jumper_pad_groups no está en los bindings)
nets = {}
txt = open(F).read()
fps = []
for i, w in enumerate(alambres):
    w['ref'] = f'W{PRIMER_W + i}'
    (x1, y1), (x2, y2) = w['a'], w['c']
    net = w['net']
    pads = ''.join(
        f'\t\t(pad "{n}" thru_hole circle (at {x - x1:.3f} {y - y1:.3f}) (size 2 2) (drill 0.8)'
        f' (layers "*.Cu" "*.Mask") (net "{net}") (uuid "{uuid.uuid4()}"))\n'
        for n, (x, y) in (('1', (x1, y1)), ('2', (x2, y2))))
    fps.append(f'''\t(footprint "ocr_up:ALAMBRE"
\t\t(layer "F.Cu")
\t\t(uuid "{uuid.uuid4()}")
\t\t(at {x1:.3f} {y1:.3f})
\t\t(property "Reference" "{w['ref']}" (at {(x2 - x1) / 2:.2f} {(y2 - y1) / 2 - 1.2:.2f} 0) (layer "F.SilkS")
\t\t\t(uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))
\t\t(property "Value" "ALAMBRE" (at {(x2 - x1) / 2:.2f} {(y2 - y1) / 2 + 1.2:.2f} 0) (layer "F.Fab")
\t\t\t(uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))
\t\t(jumper_pad_groups ("1" "2"))
\t\t(attr through_hole)
\t\t(fp_line (start 0 0) (end {x2 - x1:.3f} {y2 - y1:.3f}) (stroke (width 0.3) (type dash)) (layer "F.Fab") (uuid "{uuid.uuid4()}"))
{pads}\t)
''')
i = txt.rindex(')')
open(F, 'w').write(txt[:i] + ''.join(fps) + txt[i:])

# rellenar el plano con los pads nuevos
b = pcbnew.LoadBoard(F)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(F, b)
json.dump([{**w, 'a': list(w['a']), 'c': list(w['c'])} for w in alambres],
          open(os.path.join(HERE, 'out', 'alambres.json'), 'w'), indent=1)
print(f'{len(alambres)} alambres (W{PRIMER_W}..): ' +
      ', '.join(f"{w['ref']} {w['net']} {w['largo']} mm" for w in alambres))
