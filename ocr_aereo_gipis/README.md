# OCR Aéreo — versión GIPIS (definitiva, 2026-10-20)

Placa del nodo aéreo/bote: Heltec WiFi LoRa 32 V4 + OCR 0222 Ed (por UART MUX 2 click)
+ PAR 231 (por ADS1115) + inclinación (ICM-20689) + respaldo en microSD + alimentación
de batería de 12 V con buck D-SUN. Para la campaña CONAE (SABIA-Mar), octubre 2026.

Diseñada para fabricar en la **LPKF ProtoMat S63** del laboratorio: **una sola cara**
(todo el cobre abajo, B.Cu), **sin puentes**, sin metalizado. Los zócalos se sueldan
solo del lado del cobre.

| | |
|---|---|
| Placa | 104 × 90 mm, FR4 1,6 mm |
| Pistas | 0,92 mm (señal) / 1,38 mm (potencia), mínimo 0,8 |
| Aislación | 0,6 mm entre pistas, 0,5 mm entre plano de GND y pistas |
| Borde | 1 mm |
| DRC | 0 errores, 0 pads sin conectar, esquemático ↔ PCB en paridad |

## Conexiones principales

- **I2C en GPIO17/18** (bus del OLED, como en el protoboard), por los pads auxiliares
  de la V4 en el extremo opuesto al USB, del lado de J2. ADS1115 en 0x48, ICM-20689
  en 0x68 (AD0 a GND).
- **OCR**: TX del click → GPIO6 (J3.17). Click en canal 1 (A0/A1 a GND).
- **microSD (HW-125, 5 V)**: CS 42, SCK 41, MOSI 40, MISO 39.
- **Alimentación**: 12 V → fusible → 1N5819 → D-SUN (~5,3 V) → JP1 → 1N5819 → +5V
  (Heltec y SD). ADS1115 desde Ve; ICM y click desde 3V3 (J3.3).
- **Borneras** de 2 polos, paso 5,08: J1 batería, J2 alimentación del OCR,
  J3 alimentación del PAR, J4 señal del PAR. La bornera del click da al borde izquierdo.

## Antes de fresar

Imprimir `out/fab_nodo_b/plantilla_1a1_armado.pdf` al 100 % (sin "ajustar a página")
y apoyar los módulos reales. **Sin medir todavía**: la posición de los pads auxiliares
GPIO17/18 de la Heltec y el paso de las borneras. Ver `out/fab_nodo_b/LEEME.txt`.

## Archivos

- `nodo_b_ruteada.kicad_pro` — proyecto KiCad 10 (PCB ruteado + esquemático + librerías
  del proyecto `nodo_b.pretty` / `nodo_b.kicad_sym` + modelos 3D en `3d/`).
- `out/fab_nodo_b/` (y `.zip`) — paquete de fabricación: Gerber, Excellon, plantillas 1:1,
  LEEME con mechas.
- `out/` — esquemático en PDF, imágenes del ruteo y 3D, reporte de DRC.

## Regenerar

Todo sale de scripts (no editar el PCB a mano: se pisa al regenerar):

```
./make.sh
```

`gen_board.py` (ubicación, footprints y pre-ruteos fijos) → `route.py` (Freerouting:
una cara, GND ruteado) → `plano_gnd.py` → `gen_sch.py` + `finalizar.py` (esquemático
y librerías) → DRC → `fab_javi.py` (paquete de fabricación). Requiere KiCad 10 con
Python (`pcbnew`), Java y Freerouting 2.4.1 (`FREEROUTING_JAR` para indicar dónde está
el `.jar`; por defecto `~/.local/share/freerouting/freerouting-2.4.1.jar`).

GIPIS — UNPSJB.
