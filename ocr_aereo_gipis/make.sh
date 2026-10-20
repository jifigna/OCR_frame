#!/bin/bash
# Nodo B / OCR Aéreo — placa completa: generar → rutear (Freerouting, 1 cara + GND ruteado)
# → plano GND → esquemático KiCad + librerías → DRC con paridad → imágenes → Gerber + taladros para la LPKF.
set -e
cd "$(dirname "$0")"
python3 gen_board.py
python3 esquema.py
python3 route.py 60 mixto congnd | grep -E 'PUENTES|SES'
python3 plano_gnd.py
cp nodo_b.kicad_dru nodo_b_ruteada.kicad_dru   # reglas de fresado también en la ruteada
python3 gen_sch.py
python3 finalizar.py
B=nodo_b_ruteada.kicad_pcb
kicad-cli pcb drc $B --schematic-parity -o out/drc_ruteada.rpt --severity-error >/dev/null 2>&1 || true
grep -E 'Found' out/drc_ruteada.rpt
kicad-cli pcb export svg $B --layers B.Cu,F.Cu,Edge.Cuts,F.Fab --mode-single \
    --exclude-drawing-sheet --fit-page-to-board -o out/ruteo.svg >/dev/null 2>&1
rsvg-convert -w 1400 -b white out/ruteo.svg -o out/ruteo.png
R="kicad-cli pcb render --quality high $B"
$R --rotate '-50,0,-25' --perspective --width 1800 --height 1200 -o out/iso.png >/dev/null 2>&1
$R --side top --width 1800 --height 1600 -o out/top3d.png >/dev/null 2>&1
mkdir -p out/gerber
kicad-cli pcb export gerbers $B --layers B.Cu,F.Cu,Edge.Cuts -o out/gerber/ >/dev/null 2>&1
kicad-cli pcb export drill $B --format excellon -o out/gerber/ >/dev/null 2>&1
ls out/gerber
kicad-cli sch export pdf nodo_b_ruteada.kicad_sch -o out/esquematico_kicad.pdf >/dev/null 2>&1
python3 fab_javi.py | tail -1
