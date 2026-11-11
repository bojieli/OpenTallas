# ASAP7 vs TSMC N7: what it means for OpenTallas routing and timing
Recorded by COORD 2026-11-11 ~02:1x PST at the OWNER's request. N7 figures are from WikiChip "7 nm lithography process" (Wayback capture 2025-08-09), pasted by the owner. ASAP7 figures are read from the ASAP7 tech LEF used in our flow (asap7_tech.lef: 9 routing layers M1-M9 + Pad).

## Key numbers
| Item | ASAP7 (our flow) | TSMC N7 (WikiChip) |
|---|---|---|
| Fin pitch | 27 nm | 30 nm |
| Contacted gate pitch | 54 nm | 57 nm (HD) / 64 nm (HP) |
| Std cell height | 270 nm, 7.5 tracks at 36 nm | 240 nm 6T (HD), 300 nm 7.5T (HP), 360 nm 9T |
| M1-M3 pitch | 36 nm (ASAP7 assumes EUV) | 40 nm (M0-M4, SADP) |
| M4-M5 pitch | 48 nm | M4 40 nm; M5 76 nm (single patterning) |
| M6-M7 pitch | 64 nm | 76 nm |
| M8-M9 pitch | 80 nm (TOP routing layers) | 76 nm |
| Above M9 | none (Pad 80 nm) | M10 124 nm; M11-M12 720 nm (thick); real products often more |
| Routing layers | 9 | 13+ |
| Nominal Vdd | 0.7 V | (product dependent) |
| HD SRAM bitcell | no real compiler (generated macros) | 0.027 um^2 |
| Density | (predictive) | ~91-97 MTr/mm^2 (HD) |

## Consequences
- ROUTING IS HARDER than N7, mostly over macros. Our hard cores and SRAMs block M1-M5, sometimes M1-M7. That leaves only M6/M7 (plus M8/M9, which go to the die feedthroughs, clock and PDN) over them. N7 SRAMs typically block up to ~M4 and keep ~8 layers above, including thick ones, so we have roughly 3-4x less over-macro capacity. OpenROAD's GRT halving (adjustTransitionLayers) makes it worse. The PDN also competes for M8/M9 and mid layers, because there are no thick top layers for it.
- Local routing is NOT the problem: M1-M3 at 36 nm are denser than N7's 40 nm.
- TIMING IS MIXED. Logic is easy: 833 ps / 1.2 GHz is modest for a 7 nm-class library, and N7 products run 2-4 GHz. Long wires are hard: there are no thick low-R layers, so repeaters go about every 450 um and relay stations/ft are needed for any die-crossing link. N7's 720 nm layers would carry those runs much further.
- SIGN-OFF IS OPTIMISTIC versus a foundry. ASAP7 is predictive, with no foundry OCV/AOCV, SI/EM sign-off or foundry RC deck. We add our own derates (droop, OCV, x1.05 SPICE) and our own RCX calibration.
- DRC IS EASIER: far fewer rules than N7 (no full multi-patterning colouring, simpler via and EOL rules).
- Some of the problem is the TOOL, not the node: the OpenROAD GRT halving heuristic and pin access on porous views (DRT-0073).

## Decisions (OWNER 11-11 ~02:1x: "go with the halving-off and porous core views and clean-slate core placement")
1. GRT halving-off: pinned image opentallas/orfs:asap7lock-grtoff (sha256:2d12164a...), opt-in per row, run as a parallel arm. Stop a design's arm on a DRT failure. Sign-off is unchanged and stays on the stock image.
2. Porous core views: macros expose their real upper-layer OBS instead of solid M1-M5/M7. This is the closest legitimate emulation of commercial SRAM practice. The DRT-0073 pin-access class fix (364106cfe616) is on main.
3. Clean-slate core placement for every unsigned type, designed per family from connectivity, cutting over-macro horizontal demand. Deltas due 10:00, die cuts at 12:00, then one bind and one batch per die.
We do NOT add thick layers: that would stop being ASAP7.
