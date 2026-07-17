# Integrated circuit diagram and connector map

```mermaid
flowchart LR
  J1["J1 MAIN 12 V"] --> F1["F1 3 A resettable fuse"] --> Q1["Q1 reverse-polarity MOSFET"] --> V12["Protected 12 V"]
  V12 --> U3["U3 AP62401 6.0 V / 4 A"] --> J3["J3 DS3218 servo"]
  V12 --> U4["U4 AP63203 3.3 V / 2 A"] --> U1["U1 ESP32-S3"]
  V12 --> J4["J4 flat-panel LED +"]
  J4 --> Q2["Q2 PWM low-side switch"] --> GND["GND"]
  J2["J2 ASIAIR adjustable 12 V PWM"] --> R9["R9 2.2 k"] --> U5["U5 optocoupler"] --> U1
  U1 -->|"GPIO18"| J3
  U1 -->|"GPIO5 PWM"| Q2
  J5["J5 open limit"] --> U1
  J6["J6 closed limit"] --> U1
  J7["J7 manual button"] --> U1
  J8["J8 USB-C"] --> U2["U2 USB ESD"] --> U1
```

## ESP32-S3 signals

| Function | GPIO |
|---|---:|
| ASIAIR optocoupler input | 4 |
| LED PWM | 5 |
| Open limit | 6 |
| Closed limit | 7 |
| Manual button | 9 |
| Servo PWM | 18 |
| USB D- / D+ | 19 / 20 |
| Status LED | 15 |

The AP62401 feedback divider is 64.9 k / 10 k for nominal 6.0 V. R18 pulls its enable input high. The ESP32-S3 rail is a fixed 3.3 V AP63203. C2 and C7 provide input and servo transient energy. D1 clamps input transients; Q1 and F1 handle reverse polarity and sustained over-current.
