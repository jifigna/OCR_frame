#!/usr/bin/env python3
"""Paquete de fabricación del nodo B para la LPKF ProtoMat S63 (lo maneja Javi).

Deja out/fab_ocr_up/ y out/fab_ocr_up.zip con Gerber (B.Cu, F.Cu, contorno),
taladros Excellon, plantillas 1:1 en PDF, imágenes, LEEME.txt con la tabla de
mechas y los puentes de alambre, y el proyecto KiCad completo en kicad/.
Uso: python3 fab_javi.py   (después de make.sh / finalizar.py)
"""
import collections
import json
import os
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'ocr_up_ruteada.kicad_pcb')
OUT = os.path.join(HERE, 'out', 'fab_ocr_up')
GER = os.path.join(OUT, 'gerber')
MM = pcbnew.ToMM


def cli(*args):
    subprocess.run(['kicad-cli', *args], check=True, capture_output=True)


shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(GER)

# Gerber RS-274X clásico (sin X2) y Excellon en mm: lo que mejor importa CircuitPro.
cli('pcb', 'export', 'gerbers', PCB, '--layers', 'B.Cu,F.Cu,Edge.Cuts', '--no-x2',
    '--no-netlist', '-o', GER + '/')
cli('pcb', 'export', 'drill', PCB, '--format', 'excellon', '--excellon-units', 'mm',
    '--excellon-zeros-format', 'decimal', '--excellon-separate-th', '--generate-map',
    '--map-format', 'pdf', '-o', GER + '/')

# Plantillas 1:1: montaje (vista de arriba) y cobre de abajo (espejado = visto desde
# abajo). Se imprimen de una copia corrida al centro de la A4 (fuera del margen).
tmp = os.path.join(OUT, '_centrada.kicad_pcb')
bc = pcbnew.LoadBoard(PCB)
bbc = bc.GetBoardEdgesBoundingBox()
d = pcbnew.VECTOR2I(pcbnew.FromMM(148.5) - bbc.GetCenter().x, pcbnew.FromMM(105) - bbc.GetCenter().y)
for it in [*bc.GetFootprints(), *bc.GetTracks(), *bc.GetDrawings(), *bc.Zones()]:
    it.Move(d)
pcbnew.SaveBoard(tmp, bc)
cli('pcb', 'export', 'pdf', tmp, '--layers', 'F.Fab,F.Cu,Edge.Cuts', '--mode-single',
    '--scale', '1', '--sp', '--drill-shape-opt', '2',
    '-o', os.path.join(OUT, 'plantilla_1a1_montaje_arriba.pdf'))
cli('pcb', 'export', 'pdf', tmp, '--layers', 'B.Cu,Edge.Cuts', '--mode-single', '--mirror',
    '--scale', '1', '--drill-shape-opt', '2',
    '-o', os.path.join(OUT, 'plantilla_1a1_cobre_abajo_espejado.pdf'))

# Plantilla de armado 1:1 (estilo plano impreso), en un proceso aparte.
# (KiCad 10 a veces termina con segfault AL SALIR, con el PDF ya escrito: se verifica el PDF)
subprocess.run([sys.executable, os.path.join(HERE, 'plantilla_armado.py'), tmp,
                os.path.join(OUT, 'plantilla_1a1_armado.pdf')])
assert os.path.getsize(os.path.join(OUT, 'plantilla_1a1_armado.pdf')) > 10000, 'falló la plantilla de armado'

for ext in ('.kicad_pcb', '.kicad_prl', '.kicad_pro'):
    if os.path.exists(tmp.replace('.kicad_pcb', ext)):
        os.remove(tmp.replace('.kicad_pcb', ext))
for img in ('ruteo.png', 'iso.png', 'esquematico.pdf', 'esquematico_kicad.pdf'):
    src = os.path.join(HERE, 'out', img)
    if os.path.exists(src):
        shutil.copy(src, OUT)

# Tabla de mechas y puentes
b = pcbnew.LoadBoard(PCB)
bb = b.GetBoardEdgesBoundingBox()
w, h = MM(bb.GetWidth()), MM(bb.GetHeight())
mechas = collections.Counter()
for p in b.GetPads():
    tipo = 'sin cobre' if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else 'pad'
    mechas[(round(MM(p.GetDrillSize().x), 2), tipo)] += 1
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
for v in vias:
    mechas[(round(MM(v.GetDrill()), 2), 'vía (alambre)')] += 1
x0, y0 = MM(bb.GetX()), MM(bb.GetY())
puentes = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.F_Cu]
# Alambres que convertir_alambres.py sacó del ruteo (W6...), además de W1-W5.
_al = os.path.join(HERE, 'out', 'alambres.json')
alambres = json.load(open(_al)) if os.path.exists(_al) else []
min_w = min(MM(t.GetWidth()) for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK')

L = [f'OCR UPWELLING v2 (frame) — OCR Lu + inclinación (sin relés) — LPKF ProtoMat S63',
     f'GIPIS / UNPSJB — campaña CONAE oct 2026',
     '',
     f'Tamaño: {w:.1f} x {h:.1f} mm.  Material: FR4 1,6 mm, cobre 35 µm. SIN metalizado.',
     f'Pista mínima {min_w:.1f} mm, aislación mínima 0,6 mm, borde 1 mm.',
     '',
     'ARCHIVOS (gerber/)',
     '  *-B_Cu.gbl        cobre de ABAJO: todas las pistas + plano de GND. Es la cara a fresar.',
     '  *-F_Cu.gtl        cobre de ARRIBA: vacío (simple faz), no se fresa.',
     '  *-Edge_Cuts.gm1   contorno (fresa de corte).',
     '  *-PTH.drl         agujeros de pads y vías (Excellon, mm, decimal).',
     '  *-NPTH.drl        agujeros sin cobre: M3 de montaje y los 4 del módulo SD.',
     '  *-drl_map.pdf     mapa de agujeros.',
     '  Gerber vistos desde ARRIBA (sin espejar): en CircuitPro asignar B_Cu a BottomLayer',
     '  y el programa lo espeja solo. Origen absoluto (el de KiCad), igual para todos.',
     '',
     'CÓMO FABRICARLA',
     '  SIMPLE FAZ: fresar solo B_Cu (todas las pistas + plano de GND) + taladros +',
     '  contorno. Los zócalos y las borneras se sueldan abajo.',
     f'  Alambres aislados del lado de componentes, con las puntas soldadas abajo:',
     f'  {5 + len(alambres)} puentes W1-W{5 + len(alambres)}, cada uno con sus 2 pads (en el esquemático y en la',
     '  plantilla de montaje):',
     '  W1 (I2C SCL) y W2 (I2C SDA) pasan por arriba del haz de la SD; W3 lleva el 5 V del',
     '  buck a la SD; W4 une el GND del RTC al plano; W5 lleva el Vext al RTC, ICM y',
     '  GY-511. Sus 2 pads están en la plantilla.',
     '',
     'MECHAS',
     ]
for (d, tipo), n in sorted(mechas.items()):
    L.append(f'  {d:4.2f} mm  x{n:3d}   {tipo}')
L += ['', f'PUENTES W6-W{5 + len(alambres)} (del ruteo) — mm desde la esquina superior izquierda']
for w in alambres:
    a, c = w['a'], w['c']
    L.append(f"  {w['ref']:4s} {w['net']:8s} ({a[0] - x0:5.1f}, {a[1] - y0:5.1f}) → ({c[0] - x0:5.1f}, {c[1] - y0:5.1f})"
             f"  {w['largo']:4.1f} mm")
L += ['',
      'ANTES DE FRESAR',
      '  Imprimir plantilla_1a1_montaje_arriba.pdf al 100 % (sin "ajustar a página") y',
      '  apoyar los módulos reales: Heltec V4, microSD HW-125, RTC ZS-042, ICM-20689,',
      '  GY-511, buck y MAX3232. Medir con calibre una distancia',
      '  conocida en el papel (OJO: la Xerox 3345 achica al 95 % si se manda el PDF por',
      '  CUPS; mandarla en PostScript directo).',
      '  Sin medir todavía: los pads AUX de la Heltec (GPIO17/18) y el orden de pines de',
      '  la SD (Juan tenía GND arriba) y del GY-511.',
      '',
      'PROYECTO KiCad 10 (kicad/): esquemático + PCB + librerías del proyecto.',
      'Se genera por script (gen_board.py, gen_sch.py): no editar a mano.']
open(os.path.join(OUT, 'LEEME.txt'), 'w').write('\n'.join(L) + '\n')

# Proyecto KiCad autocontenido
K = os.path.join(OUT, 'kicad')
os.makedirs(K)
for f in ('ocr_up_ruteada.kicad_pcb', 'ocr_up_ruteada.kicad_sch', 'ocr_up_ruteada.kicad_pro',
          'ocr_up_ruteada.kicad_prl', 'ocr_up_ruteada.kicad_dru', 'ocr_up.kicad_sym',
          'fp-lib-table', 'sym-lib-table'):
    shutil.copy(os.path.join(HERE, f), K)
shutil.copytree(os.path.join(HERE, 'ocr_up.pretty'), os.path.join(K, 'ocr_up.pretty'))
shutil.copytree(os.path.join(HERE, '3d'), os.path.join(K, '3d'))

z = shutil.make_archive(OUT, 'zip', os.path.dirname(OUT), os.path.basename(OUT))
print('\n'.join(L))
print('\n→', z)
