# HBM adjacent-face transport turn — personally viewed 2026-10-29

Pictures: `results/hbm_transport_1029/turn_diagnosis.png` and
`results/hbm_transport_1029/turn_allocated.png`.

The original centroid-turn model gives a 471.2um discontinuity for the widest
paired bit when it rotates the ribbon offset from Y to X. More pipeline stages
cannot remove that discontinuity. The repaired model gives each actual pin bit
its own continuous Manhattan turn; the right panel's paths remain continuous.

Actual allocated NE_b101 L12x1 has 2,828 payload bits plus epoch, seven stages
and six internal FF banks. The FF homes follow available horizontal gaps and
free upper street rather than forming a wall over a core. Its worst measured
paired hop is 287.5um. Across all six FT slots the worst is 396.1um. Other
unchanged core geometry and face pin names remain visible. Routing wires over
M5 cores assumes M6/M7; register cells remain outside the shared corridor
allocator's physical macro pin-access keepoff. This picture is a geometric
construction diagnostic, not a routed clock/PDN or cut-capacity proof.

Verdict: **PASS-COND for construction only; HOLD P&R/STA.** The M7-only compressed
Z-band pricing successor must pass. The atomic ring/street/native-bank plan,
full G0, exact source allocation, clock load and PG continuity remain required.
Each added stage must reach TOK/model before adoption. No whole-die G1 or G3
claim is made by this narrow review.
