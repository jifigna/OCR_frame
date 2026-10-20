#!/usr/bin/env python3
"""Une las islas del plano de GND al plano principal con puentes de alambre.

Después de plano_gnd.py: rellena dejando las islas, busca las que tienen pads
de GND y, para cada una, el par de puntos (isla, plano principal) más cercano
donde entra una vía de 2 mm sin acercarse a otro cobre. Pone dos vías y un
tramo en F.Cu entre ellas (= alambre soldado arriba), y vuelve a rellenar.
"""
import math

import numpy as np
import pcbnew

F = 'ocr_up_ruteada.kicad_pcb'
MM = pcbnew.FromMM
VIA_D, VIA_DRILL, TRACK_W, CLR = 2.0, 0.8, 0.8, 0.6

b = pcbnew.LoadBoard(F)
gnd = b.GetNetcodeFromNetname('GND')
zona = [z for z in b.Zones() if z.GetNetCode() == gnd][0]


def rellenar(modo):
    zona.SetIslandRemovalMode(modo)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return zona.GetFilledPolysList(pcbnew.B_Cu)


polys = rellenar(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
n = polys.OutlineCount()
areas = [abs(polys.Outline(i).Area()) for i in range(n)]
principal = areas.index(max(areas))
pads = [p for p in b.GetPads()]
pads_gnd = [p for p in pads if p.GetNetCode() == gnd]


def dentro(i, x, y, r):
    """El círculo de radio r (mm) centrado en (x, y) entra en el contorno i."""
    pts = [(x, y)] + [(x + r * math.cos(a), y + r * math.sin(a))
                      for a in [k * math.pi / 4 for k in range(8)]]
    return all(polys.Contains(pcbnew.VECTOR2I(MM(px), MM(py)), i) for px, py in pts)


def muestras(i, bbox, paso=0.5):
    x0, y0, x1, y1 = bbox
    out = []
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            if dentro(i, x, y, VIA_D / 2 + 0.2):   # el plano deja 0.5 a las pistas; el DRC pide 0.6
                out.append((x, y))
            x += paso
        y += paso
    return out


def _dist_seg(p, a, c):
    ax, ay = a; cx, cy = c; px, py = p
    dx, dy = cx - ax, cy - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def _seg_seg(a, c, p, q):
    """Distancia mínima entre los segmentos a-c y p-q (0 si se cruzan)."""
    def ccw(u, v, w):
        return (w[1] - u[1]) * (v[0] - u[0]) - (v[1] - u[1]) * (w[0] - u[0])
    if (ccw(a, c, p) > 0) != (ccw(a, c, q) > 0) and (ccw(p, q, a) > 0) != (ccw(p, q, c) > 0):
        return 0.0
    return min(_dist_seg(p, a, c), _dist_seg(q, a, c), _dist_seg(a, p, q), _dist_seg(c, p, q))


# Cobre de arriba que ya puso el ruteo (doble faz): pistas F.Cu y vías.
MMv = pcbnew.ToMM
F_TRACKS = [((MMv(t.GetStart().x), MMv(t.GetStart().y)), (MMv(t.GetEnd().x), MMv(t.GetEnd().y)),
             MMv(t.GetWidth()) / 2) for t in b.GetTracks()
            if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.F_Cu]
B_TRACKS = [((MMv(t.GetStart().x), MMv(t.GetStart().y)), (MMv(t.GetEnd().x), MMv(t.GetEnd().y)),
             MMv(t.GetWidth()) / 2) for t in b.GetTracks()
            if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.B_Cu]
VIAS = [((MMv(v.GetPosition().x), MMv(v.GetPosition().y)), MMv(v.GetWidth(pcbnew.F_Cu)) / 2)
        for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']


def libre(a, c):
    """El tramo a-c en F.Cu (con sus vías en a y c) no pasa cerca de pads, de pistas
    de arriba ni de otras vías."""
    for p in pads:
        px, py = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
        r = pcbnew.ToMM(max(p.GetSize().x, p.GetSize().y)) / 2
        if _dist_seg((px, py), a, c) < r + CLR + max(TRACK_W, VIA_D) / 2:
            return False
    for p, q, hw in F_TRACKS:
        if _seg_seg(a, c, p, q) < hw + CLR + max(TRACK_W, VIA_D) / 2:
            return False
    for v, r in VIAS:
        if _dist_seg(v, a, c) < r + CLR + max(TRACK_W, VIA_D) / 2:
            return False
    for p, q, hw in B_TRACKS:           # las vías también tienen cobre abajo
        for v in (a, c):
            if _dist_seg(v, p, q) < hw + CLR + VIA_D / 2:
                return False
    return True


def bbox_de(i):
    bb = polys.Outline(i).BBox()
    return (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
            pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))


def toca(p, i):
    """El pad (recortado del relleno por su alivio térmico) tiene cobre del contorno i alrededor."""
    px, py = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    r = pcbnew.ToMM(max(p.GetSize().x, p.GetSize().y)) / 2 + 0.9
    return any(polys.Contains(pcbnew.VECTOR2I(MM(px + r * math.cos(a)), MM(py + r * math.sin(a))), i)
               for a in [k * math.pi / 8 for k in range(16)])


# Pad aislado = no toca el plano principal. Por cada uno, un puente a UNA de
# las islas que toca (si toca varias, alcanza con una; se deduplica).
islas = {}
for p in pads_gnd:
    if toca(p, principal):
        continue
    nombre = p.GetParentAsString() + '.' + p.GetNumber()
    tocadas = [i for i in range(n) if i != principal and toca(p, i)]
    if not tocadas:
        print(f'  ! {nombre}: no toca ningún relleno')
        continue
    ya = [i for i in tocadas if i in islas]
    islas.setdefault(ya[0] if ya else max(tocadas, key=lambda i: areas[i]), []).append(nombre)
islas = list(islas.items())

puentes = []
for i, con_pads in islas:
    x0, y0, x1, y1 = bbox_de(i)
    pi = muestras(i, (x0, y0, x1, y1))
    pm = muestras(principal, (x0 - 20, y0 - 20, x1 + 20, y1 + 20))
    # pares ordenados por distancia; el primero libre es el más corto
    mejor = None
    if pi and pm:
        A, C = np.array(pi), np.array(pm)
        D = np.hypot(A[:, None, 0] - C[None, :, 0], A[:, None, 1] - C[None, :, 1])
        for k in np.argsort(D, axis=None):
            ia, ic = divmod(int(k), len(pm))
            if libre(pi[ia], pm[ic]):
                mejor = (float(D[ia, ic]), pi[ia], pm[ic])
                break
    if not mejor:
        print(f'  ! isla {con_pads}: sin lugar para el puente')
        continue
    d, a, c = mejor
    for x, y in (a, c):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        v.SetWidth(MM(VIA_D))
        v.SetDrill(MM(VIA_DRILL))
        v.SetNetCode(gnd)
        b.Add(v)
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    t.SetWidth(MM(TRACK_W))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNetCode(gnd)
    b.Add(t)
    puentes.append(d)
    VIAS.extend([(a, VIA_D / 2), (c, VIA_D / 2)])
    F_TRACKS.append((a, c, TRACK_W / 2))
    print(f'  puente GND {d:.1f} mm para {", ".join(con_pads)}')

rellenar(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.SaveBoard(F, b)
print(f'{len(puentes)} puentes de GND')
