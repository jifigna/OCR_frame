# Revisión — placa de Juan `OCR_frame/OCR_AEREO_HELTEC_V1` (2026-10-20)

Revisada contra lo que anduvo en el protoboard (`firmware/ocr_bench`) y lo aprendido con el
**OCR Downwelling** (`../ocr_downwelling/`, fabricado para la LPKF). Ya aplicado en la rama
local `ajustes-gipis`: borneras J6/J7 a 5,08 (Phoenix MCV), ICM a 12,70 entre tiras, buck
corregido (J11 IN+, J10 GND, J8 OUT 5 V, J9 GND).

## 1. Bloqueantes

**1.1 No se puede fresar así en la LPKF (sin metalizado).**
- 2 caras, **0 vías**, y 112 de 163 tramos van por **F.Cu** (arriba).
- Hay pistas de arriba que llegan a pads que solo se pueden soldar abajo: tiras de la Heltec
  (JE1 3-6 y 17, J3 4-5), SD (J14 2-6), RTC (JE2 2-5), ICM (J1 3-4, J2 1), J5, MAX3232
  (U2 1-5, 13, 14) y borneras J6/J7. Sin metalizado esas uniones no existen.
- Pistas de 0,5 mm y aislaciones chicas: con las reglas que usamos para la LPKF (pista ≥ 0,8,
  aislación ≥ 0,6) da 128 pistas angostas y 155 faltas de aislación.
- Solución: re-rutear a una cara (B.Cu) con plano de GND, como el downwelling.

**1.2 El OCR y el BioShutter no reciben 12 V.**
- `V+_OCR` (J6.4) y `V+_BIOSHUT` (J19.1) solo van a J17/J18, que **no tienen footprint**.
- El módulo de relés (zona punteada "RELAY" con 4 M3) no tiene redes en sus tiras: la 1×4 en
  (102; 103,5) figura como "J1" (duplicada, sin redes) y la 1×3 en (102; 91,5) es "REF**".
- `INI1`/`INI2` no llegan a ningún GPIO: **los relés no se pueden comandar**.
- En el protoboard: relé OCR = **GPIO4**, relé shutter = **GPIO3** (activos en bajo).
- J19 (BIOSHUT) está en el esquemático pero no en el PCB.

**1.3 ICM-20689 y DS3231 en la misma dirección (0x68).**
- J2.4 (AD0 del ICM) va a GND → 0x68 = RTC. El firmware busca el ICM en 0x69 y después en
  0x68: con AD0 a GND va a tomar el RTC como si fuera el ICM.
- Solución: AD0 (J2.4) a Vext → 0x69 (como estaba previsto).

**1.4 MicroSD en GPIO que están ocupados.**
- CS 47, MISO 48, MOSI **26**, SCK **21**. El 21 es el **reset del OLED** y el 26 lo usa la
  **PSRAM** del ESP32-S3R2 de la V4. Además el firmware prueba un bus I2C en 47/48.
- En el protoboard y en el downwelling: CS 42, SCK 41, MOSI 40, MISO 39 (J3 de la Heltec,
  pines 7-10).

## 2. Importantes

- **Conflictos con el firmware**: SQW del RTC en GPIO4 e INT del ICM en GPIO3 = los pines de
  los relés. El firmware no usa interrupciones (polling): se pueden dejar sin conectar.
- **D2 "1N53xxB" sin valor**: es un zener de 5 W sobre +5 V. Si es de 3,3 V (lo que vimos el
  19/10) quema F1 al encender. Para clamp de 5 V: 1N5339B (5,6 V) o 1N5341B (6,2 V).
- **Sin fusible en los 12 V**: F1 está a la salida del buck; batería → OCR/BioShutter no tiene
  protección. En el downwelling: fusible a la entrada, antes del diodo.
- **USB + batería**: el buck va directo al pin 5V de la Heltec. En el downwelling: jumper
  JP1 + Schottky (1N5819) para enchufar el USB sin pelear con el buck.
- **C7 470 µF con footprint de Ø4 mm / paso 2,0**: un 470 µF real es de Ø8-10 mm, paso 3,5-5.
- **Pads AUX GPIO17/18 (J5)**: Juan tiene SDA más cerca de J2 y SCL más adentro; en el
  downwelling pusimos SCL (18) más cerca de J2. Hay que mirarlo en la Heltec real (y medir la
  distancia a la tira).

## 3. Menores

- MAX3232: T2IN (pin 10) queda al aire → atarlo a GND o Vext.
- J1 duplicado (ICM y la tira del relé), varios "REF**", J13 (I2C auxiliar) sin footprint.
- GY-511 (J12): orden DRDY/INT2 a verificar con el módulo (no lo tenemos en el lab).
- D1 1N5402: cae 0,9 V; una Schottky (1N5822) cae ~0,4 V.
- Pista de INT_INCL_1 a 0,15 mm del agujero M2 en (80,5; 89,5); una punta suelta de 5V cerca
  de J14; 5 courtyards superpuestos; ~110 avisos de serigrafía.

## Lo que está bien

- MAX3232 bien conectado (T1IN ← GPIO5, R1OUT → GPIO6, VCC = Vext). OCR: TX/RX por J6 con GND.
- Heltec alimentada por el pin 5V (no por el 3V3); sensores desde Ve (Vext).
- Pinout de ICM (VCC GND SCL SDA | INT · · AD0) y RTC (GND VCC SDA SCL SQW 32K) coincide con
  los módulos medidos.
