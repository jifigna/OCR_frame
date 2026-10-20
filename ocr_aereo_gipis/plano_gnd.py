#!/usr/bin/env python3
"""Plano de GND en B.Cu sobre la placa ruteada, relleno y guardado.
Aislación 0.5 (Pablo 2026-10-20) / ancho mín 0.8 (fresado LPKF), alivio térmico en los pads."""
import pcbnew

F = 'nodo_b_ruteada.kicad_pcb'
b = pcbnew.LoadBoard(F)
for z in list(b.Zones()):
    b.Remove(z)
bb = b.GetBoardEdgesBoundingBox()
z = pcbnew.ZONE(b)
z.SetLayer(pcbnew.B_Cu)
z.SetNetCode(b.GetNetcodeFromNetname('GND'))
z.SetLocalClearance(pcbnew.FromMM(0.5))
z.SetMinThickness(pcbnew.FromMM(0.8))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
z.SetThermalReliefGap(pcbnew.FromMM(0.5))
z.SetThermalReliefSpokeWidth(pcbnew.FromMM(1.0))
z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
o = z.Outline()
o.NewOutline()
for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
             (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
    o.Append(x, y)
b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(F, b)
print('plano GND en B.Cu relleno')
