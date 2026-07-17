# Firmware

The source sketch is `redcat_flat_panel/redcat_flat_panel.ino`. It was compile-tested
with Arduino-ESP32 3.3.10 and ESP32Servo 3.2.1 for:

- board: `ESP32S3 Dev Module`;
- USB Mode: `Hardware CDC and JTAG`;
- USB CDC On Boot: `Enabled`;
- Flash Size: `8MB`;
- Partition Scheme: `8M with SPIFFS`;
- PSRAM: `Disabled`.

The ready-to-flash merged image is `build/redcat_flat_panel.ino.merged.bin`.
Flash at address `0x0` with Espressif tools, or open the sketch in Arduino IDE.
USB alone powers the logic in Rev C; MAIN 12 V is not required for flashing.

If the USB port does not enumerate, hold BOOT, tap RESET, release RESET, then release
BOOT. J9 also exposes 3V3, GND, UART TX/RX, EN, and BOOT for recovery.

Endpoint and LED calibration are stored in ESP32 NVS:

```text
SET OPEN_ANGLE 112
SET CLOSED_ANGLE 8
SET GAMMA 1.0
SAVE
```

The firmware never powers the servo unless a move is active. Do not attach the tray
until direction, both NC switches, and endpoint angles have been tested unloaded.
