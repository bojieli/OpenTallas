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
5. Storage HOLD: CHUNK2 does not exempt logical D4 families. Core-c history is
  5444 payload +8172 epoch +2724 valid bits; a real SRAM backend is required.
  Core LM512bits/seen512bits are separately inventoried. No storage waiver.
6. Floorplan: g4b macro lattice/whole faces retained; core box324x149um,
   Z strips151x43.2um. Named mapped c32.12%, w22.69%, e16.15%, Z23.04%;
   whole fixed slot41.1%. Actual post-CTS/repair band fill still required.
7. Clock: seven existing regional roots; u_rx/u_ry fence omission fixed;
   io_hold_margin0.03; actual TT+FF child-inclusive spread must be <=80ps.
8. Schedule: static; no added edge vs g3/g4. Inherited HUB+6, AM+3, reset+10.

This source is under STORAGE and ORIGIN-LATTICE HOLD. It cannot launch a gate.
See results/arch/kv_ahub6_1020/SEMANTIC_AUDIT.md. The R0 lattice proposal is
not applied; existing mirrored origins shift24nm and need structural correction.
This README is a preparation checklist, not a gate verdict or closure approval.
