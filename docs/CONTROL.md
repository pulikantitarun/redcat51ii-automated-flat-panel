# ASIAIR, ASCOM, and manual control

## ASIAIR Plus

J1 remains connected to a constant 12 V supply. Connect J2 to one adjustable ASIAIR
DC output with a centre-positive male-to-male DC cable. The optocoupler reads that port
as a signal only.

Default mapping after 400 ms of stable input:

- 0-2%: open cover, light off;
- about 5%: close cover, light off;
- 8-100%: close cover and map the remaining range to brightness.

There is 1% hysteresis around both boundaries. Before unattended use, exercise the real
ASIAIR output from 0%, 5%, 10%, 50%, and 100% while watching the `asiairDuty` field in
USB `STATUS`. Confirm whether the installed ASIAIR firmware provides PWM, steady on/off,
or another adjustable-output behavior. Record the measured values in the first-article
test sheet; do not assume app percentages equal measured duty cycle.

## ASCOM

Connect J8 USB-C to the Windows imaging computer and run
`ascom/UniversalFlatPanelAlpaca.exe --connect`. The ASCOM Chooser sees a standard
CoverCalibrator device through Alpaca. MAIN 12 V is still required for motion/light.

ASCOM owns control while its 15-second lease is renewed. `RELEASE`, disconnecting USB,
or stopping the bridge lets the lease expire and returns control to ASIAIR. The included
bridge executable passed its local Alpaca management-endpoint smoke test; run ASCOM
ConformU against the physical first article before public release.

## Manual

Long-press the MANUAL button for at least 1.2 seconds. This cancels the ASCOM lease,
toggles open/closed, and holds manual control for 30 seconds. A short accidental press
does nothing. The same behavior is available on J7.

## USB serial protocol

Commands are ASCII lines at 115200 baud. Important commands:

```text
HELLO
CLAIM
HEARTBEAT
RELEASE
STATUS
OPEN
CLOSE
HALT
LIGHT 0..4095
OFF
CLEAR
GETCFG
SET OPEN_ANGLE 112
SET CLOSED_ANGLE 8
SET GAMMA 1.0
SAVE
```

`STATUS` returns JSON containing cover, motion, fault, brightness, power, both limits,
filtered ASIAIR duty, and current control owner.

## Status LED

- steady: closed and healthy;
- slow 1-second pulse: ASCOM owns control;
- rapid 150 ms flash: moving;
- three short flashes: latched fault;
- short heartbeat: open/idle.
