# Firmware upload

Arduino IDE setup: install Espressif ESP32 support, select `ESP32S3 Dev Module`, USB CDC On Boot = Enabled, Flash Size = 8MB, PSRAM = OPI PSRAM, and upload over J8 USB-C while MAIN 12 V remains connected.

If the port does not appear, hold BOOT, tap RESET, release RESET, then release BOOT. Upload `redcat_flat_panel.ino`. The RESET, BOOT and MANUAL buttons are marked on the PCB.

Before attaching the tray, adjust `OPEN_ANGLE` and `CLOSED_ANGLE` if the horn direction differs. The limit switches remain the final safety endpoints; the five-second timeout detaches the servo if an endpoint is not reached.
