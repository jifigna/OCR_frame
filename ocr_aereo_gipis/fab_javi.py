#!/usr/bin/env python3
"""Paquete de fabricación del nodo B para la LPKF ProtoMat S63 (lo maneja Javi).

Deja out/fab_nodo_b/ y out/fab_nodo_b.zip con Gerber (B.Cu, F.Cu, contorno),
taladros Excellon, plantillas 1:1 en PDF, imágenes, LEEME.txt con la tabla de
mechas y los puentes de alambre, y el proyecto KiCad completo en kicad/.
Uso: python3 fab_javi.py   (después de make.sh / finalizar.py)
"""
import collections
import os
import shutil
import subprocess

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'nodo_b_ruteada.kicad_pcb')
OUT = os.path.join(HERE, 'out', 'fab_nodo_b')
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

# Plantilla de armado 1:1 (estilo plano impreso): blanco y negro, sin plano de
# GND, pistas como líneas finas sobre su eje, pads en contorno con número,
# contorno + referencia + nombre de cada módulo, y cotas para medir con calibre.
FMM = pcbnew.FromMM
ba = pcbnew.LoadBoard(tmp)
for z in list(ba.Zones()):
    ba.Remove(z)
for t in list(ba.GetTracks()):
    if t.GetClass() == 'PCB_TRACK':
        s = pcbnew.PCB_SHAPE(ba)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(t.GetStart())
        s.SetEnd(t.GetEnd())
        s.SetWidth(FMM(0.3) if t.GetLayer() == pcbnew.B_Cu else FMM(0.6))   # puentes más gruesos
        s.SetLayer(pcbnew.Dwgs_User)
        ba.Add(s)
    ba.Remove(t)
for fp in ba.GetFootprints():
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and g.GetClass() != 'PCB_TEXT':
            g.SetWidth(FMM(0.25))
    for txt in (fp.Reference(), fp.Value()):
        txt.SetTextSize(pcbnew.VECTOR2I(FMM(1.4), FMM(1.4)))
        txt.SetTextThickness(FMM(0.2))


def pad(ref, num):
    return next(p for p in ba.FindFootprintByReference(ref).Pads() if p.GetNumber() == num).GetPosition()


def cota(a, b, alto):
    """Cota alineada a-b (VECTOR2I), desplazada `alto` mm; texto en mm con 2 decimales."""
    d = pcbnew.PCB_DIM_ALIGNED(ba)
    d.SetLayer(pcbnew.Dwgs_User)
    d.SetStart(a)
    d.SetEnd(b)
    d.SetHeight(FMM(alto))
    d.SetUnits(pcbnew.EDA_UNITS_MM)
    d.SetPrecision(pcbnew.DIM_PRECISION_X_XX)
    d.SetTextSize(pcbnew.VECTOR2I(FMM(1.3), FMM(1.3)))
    d.SetLineThickness(FMM(0.15))
    ba.Add(d)


eb = ba.GetBoardEdgesBoundingBox()
tl, tr = eb.GetOrigin(), pcbnew.VECTOR2I(eb.GetRight(), eb.GetTop())
bl = pcbnew.VECTOR2I(eb.GetLeft(), eb.GetBottom())
cota(tl, tr, -6)                                  # ancho de la placa
cota(bl, tl, -6)                                  # alto
cota(pad('U1', 'A1'), pad('U1', 'B1'), -5)        # Heltec: entre tiras (22.86)
cota(pad('U1', 'B1'), pad('U1', 'B18'), -5)       # Heltec: largo de tira (43.18)
cota(pad('U1', 'A18'), pad('U1', 'AUX18'), 3)    # pads AUX (17/18), a verificar
cota(pad('U1', 'AUX17'), pad('U1', 'AUX18'), -3)
cota(pad('U2', '1'), pad('U2', '16'), 4)          # click: entre filas (22.86)
cota(pad('J1', '1'), pad('J1', '2'), 5)           # paso de bornera (5.08)
cota(pad('U6', '1'), pad('U6', '6'), 4)           # tira de la SD
pcbnew.SaveBoard(tmp, ba)
cli('pcb', 'export', 'pdf', tmp, '--layers', 'F.Fab,F.SilkS,Dwgs.User,Edge.Cuts', '--mode-single',
    '--scale', '1', '--sp', '--black-and-white', '--drill-shape-opt', '2',
    '-o', os.path.join(OUT, 'plantilla_1a1_armado.pdf'))

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
min_w = min(MM(t.GetWidth()) for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK')

L = [f'NODO B (bote) — OCR 0222 Ed + PAR 231 — placa para la LPKF ProtoMat S63',
     f'GIPIS / UNPSJB — campaña CONAE oct 2026',
     '',
     f'Tamaño: {w:.1f} x {h:.1f} mm.  Material: FR4 1,6 mm, cobre 35 µm. SIN metalizado.',
     f'Pista mínima {min_w:.1f} mm, aislación mínima 0,6 mm, borde 1 mm.',
     '',
     'ARCHIVOS (gerber/)',
     '  *-B_Cu.gbl        cobre de ABAJO: todas las pistas + plano de GND. Es la cara a fresar.',
     '  *-F_Cu.gtl        cobre de ARRIBA: solo pads y los puentes (ver abajo).',
     '  *-Edge_Cuts.gm1   contorno (fresa de corte).',
     '  *-PTH.drl         agujeros de pads y vías (Excellon, mm, decimal).',
     '  *-NPTH.drl        agujeros sin cobre: M3 de montaje y los 4 del módulo SD.',
     '  *-drl_map.pdf     mapa de agujeros.',
     '  Gerber vistos desde ARRIBA (sin espejar): en CircuitPro asignar B_Cu a BottomLayer',
     '  y el programa lo espeja solo. Origen absoluto (el de KiCad), igual para todos.',
     '',
     'CÓMO FABRICARLA',
     '  Opción 1 (preferida): placa SIMPLE FAZ, cobre abajo. Fresar solo B_Cu + taladros +',
     '    contorno. Los puentes se hacen con alambre aislado del lado de componentes.',
     '  Opción 2: placa DOBLE FAZ. Además fresar F_Cu (aislación alrededor de cada pad,',
     '    si no la cara de arriba cortocircuita todos los pines). Las pistas de F_Cu ya son',
     '    los puentes; en cada vía pasar un alambre y soldarlo de los dos lados.',
     '  En los dos casos los zócalos se sueldan SOLO abajo.',
     '',
     'MECHAS',
     ]
for (d, tipo), n in sorted(mechas.items()):
    L.append(f'  {d:4.2f} mm  x{n:3d}   {tipo}')
L += ['', f'PUENTES ({len(puentes)}) — coordenadas en mm desde la esquina superior izquierda']
for i, t in enumerate(puentes, 1):
    s, e = t.GetStart(), t.GetEnd()
    L.append(f'  P{i}  {t.GetNetname():8s} ({MM(s.x) - x0:5.1f}, {MM(s.y) - y0:5.1f}) → '
             f'({MM(e.x) - x0:5.1f}, {MM(e.y) - y0:5.1f})  {MM(t.GetLength()):4.1f} mm')
L += ['',
      'ANTES DE FRESAR',
      '  Imprimir plantilla_1a1_montaje_arriba.pdf al 100 % (sin "ajustar a página") y',
      '  apoyar los módulos reales: Heltec V4, ADS1115, ICM-20689, UART MUX 2 click,',
      '  microSD HW-125 y D-SUN. Medir con calibre una distancia conocida en el papel.',
      '  OJO, sin medir todavía: (1) los 2 pads AUX de la Heltec (GPIO17/18 = I2C), en',
      '  el extremo opuesto al USB, posición tomada del footprint de Carlos; (2) el paso',
      '  de las borneras (5,08 mm).',
      '',
      'PROYECTO KiCad 10 (kicad/): esquemático + PCB + librerías del proyecto.',
      'Se genera por script (gen_board.py, gen_sch.py): no editar a mano.']
open(os.path.join(OUT, 'LEEME.txt'), 'w').write('\n'.join(L) + '\n')

# Proyecto KiCad autocontenido
K = os.path.join(OUT, 'kicad')
os.makedirs(K)
for f in ('nodo_b_ruteada.kicad_pcb', 'nodo_b_ruteada.kicad_sch', 'nodo_b_ruteada.kicad_pro',
          'nodo_b_ruteada.kicad_prl', 'nodo_b_ruteada.kicad_dru', 'nodo_b.kicad_sym',
          'fp-lib-table', 'sym-lib-table'):
    shutil.copy(os.path.join(HERE, f), K)
shutil.copytree(os.path.join(HERE, 'nodo_b.pretty'), os.path.join(K, 'nodo_b.pretty'))
shutil.copytree(os.path.join(HERE, '3d'), os.path.join(K, '3d'))

z = shutil.make_archive(OUT, 'zip', os.path.dirname(OUT), os.path.basename(OUT))
print('\n'.join(L))
print('\n→', z)
