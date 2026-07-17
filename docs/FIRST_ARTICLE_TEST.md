# Mandatory first-article test

Record board serial number, test date, ambient temperature, supply model, and every
measurement. Do not install on optics until sections 1-5 pass.

## 1. Unpowered inspection

- Confirm polarities of C2, C7, D1, D2, D6, D7, LED1, and LED2.
- Confirm U1, U3, U4, Q1, Q3, F1-F3, and both barrel jacks match the BOM.
- Inspect USB-C and all fine-pitch joints under magnification.
- Check MAIN-to-GND and 6V-to-GND are not shorted.
- Confirm J3 keyed pin order: 6 V / GND / signal.

## 2. Logic power

1. Connect USB-C only. Confirm TP4 = 3.20-3.40 V and TP2/TP3 = 0 V.
2. Confirm the USB serial port enumerates and `HELLO` / `STATUS` respond.
3. Confirm `STATUS` reports `mainPower:false`; OPEN/CLOSE must return a power fault.
4. Apply MAIN 12.0 V with a 0.5 A current limit and no servo/LED loads.
5. Confirm TP1 = supply voltage after protection, TP2 = 5.85-6.15 V, TP4 = 3.20-3.40 V.
6. Remove USB while MAIN remains: logic must stay running without reset.
7. Reconnect USB: MAIN must not back-feed more than 50 mV onto a disconnected USB source.

## 3. Limits and servo

- Wire each switch COM-NC. Mid-travel must report both limits false; manually release one
  switch at a time and confirm only the corresponding endpoint reports true.
- Disconnect either limit cable: the open wire must be treated as an active endpoint/fault.
- Confirm both limits open simultaneously produces `BOTH_LIMITS_OPEN` and servo power off.
- Connect the unloaded servo with a 1.5 A supply limit. Run 20 full cycles.
- Confirm TP3 is about 6 V only during motion and returns to 0 V afterward.
- Hold the horn briefly before a limit: timeout/fault must cut TP3. Do not stall longer
  than one second during this deliberate test.
- Record peak input current and peak servo current. If normal motion approaches fuse or
  connector limits, correct the mechanism rather than increasing fuse values.

## 4. LED and ASIAIR

- Connect the intended LED panel. Test LIGHT 256, 1024, 2048, and 4095 for five minutes.
- Confirm LED is always off while cover is open or moving.
- Record input current at maximum brightness; it must remain below 2 A total board input.
- Connect the actual ASIAIR Plus output to J2. Record `asiairDuty` at app settings 0, 5,
  10, 50, and 100%. Confirm the cover/brightness mapping and lease fallback.

## 5. Thermal and USB/ASCOM

- Run maximum LED brightness for 30 minutes, then 20 servo cycles. Measure U3, U4, Q1,
  Q3, F1-F3, L1, L2, C2, and C7. Target under 70 C; any part above 80 C fails.
- While the servo moves, continuously query `STATUS`; USB must not disconnect or reset.
- Run the Alpaca bridge, discover it in ASCOM, and test OpenCover, CloseCover,
  CalibratorOn at four levels, CalibratorOff, HaltCover, and disconnect fallback.
- Run ASCOM ConformU CoverCalibrator tests against the physical device.

## 6. Optics and full installation

- Capture a flat at a mid-range brightness. Measure centre and four corner medians after
  excluding dust motes. Aim for less than 10% centre-to-corner spread and no LED hotspots.
- Add diffusion or improve the light-guide pattern if uniformity fails; do not correct a
  visibly nonuniform panel only with software.
- Complete the full-mount clearance test, cable drip loops, strain relief, and tether.
- Perform 50 loaded cycles before enabling unattended operation.
