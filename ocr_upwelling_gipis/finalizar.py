#!/usr/bin/env python3
"""Deja ocr_up_ruteada como proyecto KiCad autocontenido (para Carlos / Javi).

- Rutas de los modelos 3D relativas al proyecto (${KIPRJMOD}/3d/...).
- Agujeros de montaje con referencia H1..H4 y "solo placa" (no van al esquemático).
- Exporta los footprints de la placa a ocr_up.pretty y escribe fp-lib-table y
  sym-lib-table (la librería de símbolos ocr_up.kicad_sym la escribe gen_sch.py).
Idempotente. Uso: python3 finalizar.py
"""
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, 'ocr_up_ruteada.kicad_pcb')
PRETTY = os.path.join(HERE, 'ocr_up.pretty')

b = pcbnew.LoadBoard(F)
n_h = 0
for fp in b.GetFootprints():
    if str(fp.GetFPID().GetLibItemName()) in ('M2', 'M3'):
        n_h += 1
        fp.SetReference(f'H{n_h}')
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
# Pines libres: la red que les asigna el esquemático ("Update PCB from schematic")
xml = os.path.join(HERE, 'out', 'net_sch.xml')
subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', xml,
                os.path.join(HERE, 'ocr_up_ruteada.kicad_sch')], check=True, capture_output=True)
nombres = {(n.get('ref'), n.get('pin')): net.get('name')
           for net in ET.parse(xml).getroot().iter('net') for n in net.iter('node')}
for fp in b.GetFootprints():
    for p in fp.Pads():
        net = nombres.get((fp.GetReference(), p.GetNumber()), '')
        if p.GetNetCode() == 0 and net.startswith('unconnected-'):
            ni = b.FindNet(net)
            if not ni:
                ni = pcbnew.NETINFO_ITEM(b, net)
                b.Add(ni)
            p.SetNet(ni)
pcbnew.SaveBoard(F, b)

# Librería de footprints: uno por nombre (R1/R2 y D1/D2 comparten footprint).
# (FootprintSave no anda desde Python en KiCad 10: se recortan del texto del PCB)
shutil.rmtree(PRETTY, ignore_errors=True)
os.makedirs(PRETTY)
# rutas 3D: el setter de Python no persiste, se corrige en el texto
txt = re.sub(r'\(model "[^"]*/3d/', '(model "${KIPRJMOD}/3d/', open(F).read())
open(F, 'w').write(txt)
vistos = set()
i = 0
while (i := txt.find('\n\t(footprint "ocr_up:', i)) >= 0:
    depth, j = 0, i + 2
    while True:
        c = txt[j]
        depth += (c == '(') - (c == ')')
        j += 1
        if depth == 0:
            break
    blk, i = txt[i + 2:j], j
    name = re.match(r'\(footprint "ocr_up:([^"]+)"', blk).group(1)
    if name in vistos:
        continue
    vistos.add(name)
    blk = blk.replace(f'"ocr_up:{name}"', f'"{name}"\n\t\t(version 20260206)\n\t\t(generator "finalizar.py")', 1)
    blk = re.sub(r'\n\t\t\(at [-\d. ]+\)', '', blk, count=1)          # posición en la placa
    blk = re.sub(r'(\(pad "[^"]*" [^\n]*?\(at [-\d.]+ [-\d.]+) (?:90|180|270)\)', r'\1)', blk)  # giro de la placa
    blk = re.sub(r'\s*\(net "[^"]*"\)', '', blk)                        # redes
    blk = re.sub(r'\s*\(uuid "[^"]*"\)', '', blk)
    open(os.path.join(PRETTY, f'{name}.kicad_mod'), 'w').write(blk.replace('\n\t', '\n') + '\n')

open(os.path.join(HERE, 'fp-lib-table'), 'w').write(
    '(fp_lib_table\n  (version 7)\n'
    '  (lib (name "ocr_up") (type "KiCad") (uri "${KIPRJMOD}/ocr_up.pretty") (options "") (descr "Nodo B"))\n)\n')
open(os.path.join(HERE, 'sym-lib-table'), 'w').write(
    '(sym_lib_table\n  (version 7)\n'
    '  (lib (name "ocr_up") (type "KiCad") (uri "${KIPRJMOD}/ocr_up.kicad_sym") (options "") (descr "Nodo B"))\n)\n')
print(f'{len(vistos)} footprints en ocr_up.pretty, {n_h} agujeros H*, modelos 3D relativos')
