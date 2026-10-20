#!/usr/bin/env python3
"""Plantilla de armado 1:1 (la llama fab_javi.py en un proceso aparte: en el mismo
proceso, después de cargar y modificar otra placa, los bindings de KiCad 10
devuelven objetos sin tipo). Uso: python3 plantilla_armado.py <_centrada.kicad_pcb> <salida.pdf>"""
import subprocess
import sys

import pcbnew

tmp, pdf = sys.argv[1], sys.argv[2]


def cli(*args):
    subprocess.run(['kicad-cli', *args], check=True, capture_output=True)


# Plantilla de armado 1:1 (estilo plano impreso): blanco y negro, sin plano de
# GND, pistas como líneas finas sobre su eje, pads en contorno con número,
# contorno + referencia + nombre de cada módulo, y cotas para medir con calibre.
FMM = pcbnew.FromMM
ba = pcbnew.LoadBoard(tmp)
fps_a = list(ba.GetFootprints())      # antes de modificar (bindings de KiCad 10)
# Posiciones que hacen falta para las cotas, leídas ANTES de tocar la placa: después de
# agregar/quitar objetos los bindings de KiCad 10 devuelven objetos sin tipo.
PADPOS = {(f.GetReference(), p.GetNumber()): (p.GetPosition().x, p.GetPosition().y)
          for f in fps_a for p in f.Pads()}
_eb = ba.GetBoardEdgesBoundingBox()
EB = (_eb.GetLeft(), _eb.GetTop(), _eb.GetRight(), _eb.GetBottom())
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
for fp in fps_a:
    try:                       # en algunas placas KiCad 10 no devuelve una lista (bindings)
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_Fab and g.GetClass() != 'PCB_TEXT':
                g.SetWidth(FMM(0.25))
    except TypeError:
        pass
    try:
        for txt in (fp.Reference(), fp.Value()):
            txt.SetTextSize(pcbnew.VECTOR2I(FMM(1.4), FMM(1.4)))
            txt.SetTextThickness(FMM(0.2))
    except (TypeError, AttributeError):
        pass


def pad(ref, num):
    return pcbnew.VECTOR2I(*PADPOS[(ref, num)])


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


tl, tr = pcbnew.VECTOR2I(EB[0], EB[1]), pcbnew.VECTOR2I(EB[2], EB[1])
bl = pcbnew.VECTOR2I(EB[0], EB[3])
cota(tl, tr, -6)                                  # ancho de la placa
cota(bl, tl, -6)                                  # alto
cota(pad('U1', 'A1'), pad('U1', 'B1'), -5)        # Heltec: entre tiras (22.86)
cota(pad('U1', 'B1'), pad('U1', 'B18'), -5)       # Heltec: largo de tira (43.18)
cota(pad('U1', 'A18'), pad('U1', 'AUX18'), 3)     # pads AUX (17/18), a verificar
cota(pad('U1', 'AUX17'), pad('U1', 'AUX18'), -3)
cota(pad('U4', '1'), pad('U4', '5'), -3)          # ICM: entre tiras (12.70)
cota(pad('J7', '1'), pad('J7', '2'), 5)           # paso de bornera (5.08)
cota(pad('U6', '1'), pad('U6', '6'), 4)           # tira de la SD
cota(pad('U5', '1'), pad('U5', '5'), -3)          # buck: IN ↔ OUT
pcbnew.SaveBoard(tmp, ba)
cli('pcb', 'export', 'pdf', tmp, '--layers', 'F.Fab,F.SilkS,Dwgs.User,Edge.Cuts', '--mode-single',
    '--scale', '1', '--sp', '--black-and-white', '--drill-shape-opt', '2',
    '-o', pdf)

