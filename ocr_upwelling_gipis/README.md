# OCR Upwelling — versión GIPIS v2 (2026-10-20)

Placa del nodo del frame (OCR que mira al mar, Lu): Heltec WiFi LoRa 32 V4 + OCR por
RS-232 (MAX3232) + inclinación (ICM-20689 y GY-511) + RTC (ZS-042) + respaldo en microSD
+ buck desde la batería de 12 V. Campaña CONAE (SABIA-Mar), octubre 2026.

Parte de la placa de Juan (`OCR_AEREO_HELTEC_V1` en `main`): misma placa de 109,5 × 85,5 mm
y misma ubicación de módulos, con las correcciones de la revisión
(`REVISION_placa_juan_20261020.md`) y **sin relés ni BioShutter** (el OCR toma 12 V directo).

Para la **LPKF ProtoMat S63** del laboratorio: **una sola cara** (todo el cobre abajo),
sin metalizado, sin vías. Lo que no se puede rutear en una cara va con **8 puentes de
alambre W1–W8** (componentes de 2 pads; en el esquemático y en la plantilla).

| | |
|---|---|
| Pistas | 0,92 mm (señal) / 1,38 mm (potencia), mínimo 0,65 entre pines vecinos |
| Aislación | 0,6 mm entre pistas, 0,5 mm entre plano de GND y pistas, borde 1 mm |
| DRC | 0 errores, 0 pads sin conectar, esquemático ↔ PCB en paridad |

## Cambios respecto de la placa de Juan

- Tiras de la Heltec a 22,86 mm y alineadas (estaban a 23,00 y corridas 0,5 mm).
- I2C en GPIO17/18 (pads AUX del lado de J2), como en el protoboard.
- SD en GPIO 39–42 (CS 42, SCK 41, MOSI 40, MISO 39): el 21 es el reset del OLED y el 26
  lo usa la PSRAM.
- ICM-20689 con AD0 a Vext → 0x69 (en 0x68 chocaba con el DS3231) y tiras a 12,70 mm.
- MAX3232 girado 180°; T2IN a GND. UART: GPIO5 → T1IN, R1OUT → GPIO6.
- Fusible a la ENTRADA de los 12 V; D1 Schottky 1N5822; zener 1N5339B (5,6 V) sobre +5V;
  C7 470 µF con footprint de Ø8.
- Buck: J11 IN+, J10 IN− (GND), J8 OUT+ (5 V), J9 OUT− (GND).
- +5V → JP1 → D3 1N5819 → pin 5V de la Heltec (sacar JP1 con la Heltec por USB).
- Borneras Phoenix MCV 5,08: J7 batería (abajo) y J6 OCR en el borde derecho
  (de arriba a abajo GND, RX, TX, +12V).

## Antes de fresar

Imprimir `out/fab_ocr_up/plantilla_1a1_armado.pdf` al 100 % y apoyar los módulos reales.
Sin medir todavía: los pads AUX 17/18 de la Heltec, el orden de pines de la SD (Juan tenía
GND arriba) y del GY-511. Ver `out/fab_ocr_up/LEEME.txt`.

## Regenerar

Todo sale de scripts (no editar el PCB a mano: se pisa al regenerar): `./make.sh`.
`gen_board.py` (ubicación, footprints y pre-ruteos fijos) → `route.py` (Freerouting) →
`plano_gnd.py` → `fix_islas.py` → `convertir_alambres.py` (los tramos de arriba pasan a ser
puentes de alambre W6…, con `jumper_pad_groups`) → `esquema.py` / `gen_sch.py` /
`finalizar.py` → DRC → `fab_javi.py`. Requiere KiCad 10 con Python (`pcbnew`) y
Freerouting 2.4.1 (Java 25). `FREEROUTING_HOST=usuario@host` corre Freerouting en otra
máquina por SSH (en un contenedor `eclipse-temurin:25-jre`); vacío, lo corre local.

GIPIS — UNPSJB.
