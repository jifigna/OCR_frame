#!/usr/bin/env python3
"""Ruteo automático con Freerouting: B.Cu + puentes de alambre en F.Cu.

pcbnew → DSN → (ajustes de capas) → Freerouting → SES → pcbnew.
Modos:
  1cara    sin F.Cu ni vías: todo abajo (puede dejar conexiones sin rutear)
  puentes  F.Cu solo entre vías propias (= alambres)
  mixto    (por defecto) primero 1cara; se bloquea lo ruteado y lo que falta
           se completa en modo puentes. Freerouting en modo puentes usa F.Cu
           aunque haya camino abajo; así los puentes quedan solo donde hacen falta.
Uso: python3 route.py [pasadas] [modo]   (deja ocr_up_ruteada.kicad_pcb)
"""
import os
import re
import subprocess
import sys

import pcbnew

JAR = os.environ.get('FREEROUTING_JAR',
                     os.path.expanduser('~/.local/share/freerouting/freerouting-2.4.1.jar'))
PASSES = sys.argv[1] if len(sys.argv) > 1 else '40'
MODE = sys.argv[2] if len(sys.argv) > 2 else 'mixto'
OUT = 'ocr_up_ruteada.kicad_pcb'


def preparar(dsn, mode):
    if mode == '1cara':
        # sin capa F.Cu ni vías: todo abajo
        dsn = re.sub(r'\(layer F\.Cu\s*\(type signal\)\s*\(property\s*\(index 0\)\s*\)\s*\)', '', dsn, count=1)
        dsn = re.sub(r'\(via "[^"]+"\)', '', dsn)
        dsn = re.sub(r'\(shape \((?:circle|rect|path|polygon) F\.Cu[^()]*\)\)', '', dsn)
    else:
        # F.Cu = capa de puentes de alambre: solo se conecta a vías (agujeros propios),
        # nunca a pads de componentes (los zócalos no se sueldan del lado de arriba)
        def strip(m):
            blk = m.group(0)
            if blk.startswith('(padstack "Via') or blk.startswith('(padstack Via'):
                return blk
            return re.sub(r'\(shape \((?:circle|rect|path|polygon) F\.Cu[^()]*\)\)', '', blk)
        dsn = re.sub(r'\(padstack [^\n]*\n(?:\s+\(shape[^\n]*\n)+\s+\(attach[^\n]*\n\s+\)', strip, dsn)

        # ...pero el cobre del pad SÍ existe arriba (placa doble faz): keepout en
        # F.Cu sobre cada pin para que ningún puente pase por encima de un pad.
        def size(ps):
            nums = [int(float(n)) for n in re.findall(r'(\d+(?:\.\d+)?)(?=x|_um)', ps)]
            return max(nums) if nums else 2000

        def keepouts(m):
            img = m.group(0)
            # + 1.2 mm: la aislación de 0.6 a cada lado (al keepout Freerouting no le deja aislación)
            ko = ''.join(f'      (keepout "" (circle F.Cu {size(ps) + 1200} {x} {y}))\n'
                         for ps, x, y in re.findall(
                             r'\(pin (\S+) (?:\(rotate [^)]*\) )?\S+ (-?[\d.]+) (-?[\d.]+)\)', img))
            return img[:img.rindex(')')] + ko + '    )'
        dsn = re.sub(r'\(image [^\n]*\n(?:\s+\((?:outline|pin|keepout)[^\n]*\n)*\s+\)', keepouts, dsn)

    # El borde de 1 mm (fresa de contorno) no viaja en el DSN: se achica el
    # contorno 0.4 mm (más los 0.6 de aislación que Freerouting ya respeta).
    def inset(m):
        nums = [float(v) for v in m.group(2).split()]
        xs, ys = nums[0::2], nums[1::2]
        x0, x1, y0, y1 = min(xs) + 400, max(xs) - 400, min(ys) + 400, max(ys) - 400
        pts = [(x1, y0), (x0, y0), (x0, y1), (x1, y1), (x1, y0)]
        return m.group(1) + '  '.join(f'{x:.0f} {y:.0f}' for x, y in pts) + ')'
    dsn = re.sub(r'(\(boundary\s*\(path pcb \d+\s+)([-\d.\s]+)\)', inset, dsn, count=1)
    # GND no se rutea: lo cubre el plano de cobre (plano_gnd.py)
    if 'congnd' not in sys.argv:
        dsn = re.sub(r'\(net GND\s*\(pins[^)]*\)\s*\)', '', dsn, count=1)
    return dsn


def rutear(src, mode):
    """Rutea src en el modo dado y deja el resultado en OUT. Devuelve el log."""
    b = pcbnew.LoadBoard(src)
    pcbnew.ExportSpecctraDSN(b, 'out/ocr_up.dsn')
    open('out/ocr_up_1cara.dsn', 'w').write(preparar(open('out/ocr_up.dsn').read(), mode))
    args = ['-de', 'ocr_up_1cara.dsn', '-do', 'ocr_up.ses', '-mp', PASSES, '--gui.enabled=false']
    host = os.environ.get('FREEROUTING_HOST')       # p. ej. iagipis@iagipis
    if host:
        # Freerouting en otra máquina (IA GIPIS), en un contenedor con Java 25: acá
        # pablo-work se apaga en seco con todos los núcleos al 100 % (2026-10-20).
        subprocess.run(['scp', '-q', 'out/ocr_up_1cara.dsn', f'{host}:freerouting/'], check=True)
        r = subprocess.run(['ssh', host, 'cd ~/freerouting && rm -f ocr_up.ses && docker run --rm --cpus 10 '
                            '-v ~/freerouting:/w -w /w eclipse-temurin:25-jre java -jar freerouting-2.4.1.jar '
                            + ' '.join(args)], capture_output=True, text=True, timeout=1800)
        subprocess.run(['scp', '-q', f'{host}:freerouting/ocr_up.ses', 'out/ocr_up.ses'], check=True)
    else:
        # Local: hilos limitados y prioridad baja (FREEROUTING_MT para cambiarlo).
        a = [x.replace('ocr_up_1cara.dsn', 'out/ocr_up_1cara.dsn').replace('ocr_up.ses', 'out/ocr_up.ses') for x in args]
        r = subprocess.run(['taskset', '-c', '0-3', 'nice', '-n', '15', 'java', '-Xmx3g', '-jar', JAR,
                            '-mt', os.environ.get('FREEROUTING_MT', '2')] + a,
                           capture_output=True, text=True, timeout=1800)
    log = r.stdout + r.stderr
    open(f'out/freerouting_{mode}.log', 'w').write(log)
    b = pcbnew.LoadBoard(src)
    ok = pcbnew.ImportSpecctraSES(b, 'out/ocr_up.ses')
    pcbnew.SaveBoard(OUT, b)
    sin = re.findall(r'\((\d+) unrouted', log)
    print(f'{mode}: SES importado {ok}, sin rutear {sin[-1] if sin else "?"}')
    return log


def bloquear(lock):
    b = pcbnew.LoadBoard(OUT)
    for t in b.GetTracks():
        t.SetLocked(lock)
    pcbnew.SaveBoard(OUT, b)


if MODE == 'mixto':
    log = rutear('ocr_up.kicad_pcb', '1cara')
    if not re.search(r'\(0 unrouted', log.splitlines()[-1] if log else ''):
        bloquear(True)                      # lo de abajo queda fijo (type fix)
        rutear(OUT, 'puentes')
    # se desbloquea todo salvo el pre-ruteo de gen_board.py (para editar a mano)
    pre = {(round(t.GetStart().x), round(t.GetStart().y))
           for t in pcbnew.LoadBoard('ocr_up.kicad_pcb').GetTracks()}
    b = pcbnew.LoadBoard(OUT)
    for t in b.GetTracks():
        t.SetLocked((round(t.GetStart().x), round(t.GetStart().y)) in pre)
    pcbnew.SaveBoard(OUT, b)
else:
    rutear('ocr_up.kicad_pcb', MODE)

# Conteo de puentes: tramos conexos de F.Cu
b = pcbnew.LoadBoard(OUT)
fc = [t for t in b.GetTracks() if t.GetLayer() == pcbnew.F_Cu and t.GetClass() == 'PCB_TRACK']
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
def key(p): return (round(p.x / 1e4), round(p.y / 1e4))
par = {}
def find(a):
    while par.setdefault(a, a) != a:
        a = par[a]
    return a
for t in fc:
    par[find(key(t.GetStart()))] = find(key(t.GetEnd()))
grupos = {find(k) for k in par}
print(f'vías: {len(vias)}  segmentos arriba: {len(fc)}  PUENTES: {len(grupos)}')
