# ASCOM / Alpaca USB control

The Rev C USB-C connector exposes the ESP32-S3 native USB serial port. The included
bridge presents it to ASCOM as a standard `CoverCalibrator` device over ASCOM Alpaca.
ASCOM Platform 6.5 or newer can discover Alpaca devices; Platform 7.1 is recommended.

## Quick start

1. Flash the Rev C firmware with **USB CDC On Boot = Enabled**.
2. Connect USB-C to the Windows imaging computer. MAIN 12 V is still required for
   servo or LED operation; USB powers only the controller logic.
3. Run `UniversalFlatPanelAlpaca.exe --connect`. Windows may ask for permission for
   local-network discovery; allow Private networks.
4. In the ASCOM Chooser, select the discovered **Universal Flat Panel Rev C**
   CoverCalibrator device.

Use `--port COM7 --connect` if automatic ESP32 port detection selects the wrong port.
The bridge listens on Alpaca TCP port 11111 and discovery UDP port 32227.

ASCOM commands hold a renewable 15-second control lease. When the bridge disconnects
or stops heartbeating, control automatically returns to the isolated ASIAIR input.
