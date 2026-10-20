# qkd_ahub_g6b: AHUB6 structural successor

Do not inherit g4's gate. Native mapped admission must PASS with exact loaded
Liberties before this first layout gate. Exactness witnesses must match g6.

SAFE review before gate:
1. Pins: registered as in g3;32 same-edge start copies; reset source pin7 D loads.
2. Reach: existing landed D4/K2 region crossings; u_rx/u_ry now inside c beside
   core and reciprocal child, existing single-cycle segments below405um.
3. Fanout: mandatory actual-Liberty full dynamic/reset BUF/INV census required;
   attach the exact actual-top/source receipt. No waiver is permitted.
4. Depth: exact FP-max comparison duplicated in8-bit output cones, semantic
   decoder partitions; stage boundaries unchanged; gate must measure <=600ps.
5. Storage: two-bit local rings, four slots; core LM512bits/seen512bits, no new
   runtime-indexed storage above2kb. Extra metadata flops are priced explicitly.
6. Floorplan: g4b macro lattice/whole faces retained; core box324x149um,
   Z strips151x43.2um; source SYNTHESIS area and current fill still need receipt.
7. Clock: seven existing regional roots; u_rx/u_ry fence omission fixed;
   io_hold_margin0.03; actual TT+FF child-inclusive spread must be <=80ps.
8. Schedule: static; no added edge vs g3/g4. Inherited HUB+6, AM+3, reset+10.

This README is a preparation checklist, not a gate verdict or closure approval.
