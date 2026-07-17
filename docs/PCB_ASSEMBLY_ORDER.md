# PCB assembly order values

Use the manufacturer-neutral files in `pcb/`.

| Field | Value |
|---|---|
| Board type | Single board |
| Dimensions | 120 x 75 mm |
| Quantity | 5 recommended for first run |
| Layers | 4 |
| Material | FR-4 |
| Thickness | 1.6 mm |
| Finished copper | 2 oz all layers |
| Minimum track / spacing | 0.20 / 0.20 mm |
| Minimum drill | 0.35 mm routed vias; manufacturer standard acceptable after DFM |
| Surface finish | ENIG |
| Solder mask / silkscreen | Green / white |
| Castellated / edge plating | No |
| Impedance control | No formal coupon; preserve USB pair geometry |
| Electrical test | Yes, 100% |
| Assembly | Turnkey, top side, SMT plus through-hole |
| Solder | Lead-free |
| Inspection | AOI plus manual connector/polarity inspection |

Upload `Gerbers_RevC.zip`, `BOM.csv`, and `PickAndPlace.csv`. Attach the assembly PDF.
Ask engineering to flag all substitutions and confirm the three PPTC exact voltage
ratings. Test pads TP1-TP8 are DNP. The STEP model omits some library 3D bodies but the
footprints and Gerbers are complete.

Do not authorize production quantity until one assembled board passes
`FIRST_ARTICLE_TEST.md`. The main PJ-102AH connector is protected by a 2 A hold fuse;
do not market or operate the board as a 4 A input device.
