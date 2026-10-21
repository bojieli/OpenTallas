# hcoll_v5_issuer_r256 — 256-row COLL issuer leaf (ot_hgi_coll_issuer_m256, v7 core)

HBM-COLL256-KITS 10-19, coordinator HANDOFF 0ky (2)/(3). Bound by the d4g SW COLL parent at ROWS 256 (ARGMAX at VM_RT 74 =
212 rows; DS RS(144)). ROWS 64/128 parents keep ot_hgi_coll_issuer_m (closed hcoll_v5_issuer, v6 core, names unchanged).

Core: rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_issuer_v7.sv (header explains the structure and the two
programme constraints). Cycle-exact to ot_hgi_coll_static_issuer_v6 #(ROWS 256) on every port (miter, 600 programmes).

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS. cfg/start/start_pc registered in RTL (PIN_REGS=1, as the closed issuer); every output flop Q (raw busy =
   busy_c | start_q, as closed); rst_n loads one synchroniser; reset_landing 2 stages in the kit.
2. Reach: PASS. Longest single-cycle wires: data-stack W face -> bank data regs -> uop_d1 W pins ~175 um; metadata column
   <-> stack channel 63 um; all < 405 um.
3. Fanout: PASS (gate-checked). The decision `take` (comb, from flops) selects ~170 bits (4 x 8-b addresses, CT/CN
   records, L1 data); it arrives ~150 ps before the macro data it selects, so its buffer tree is off the critical path.
   start -> L1 reset (32 x 32 enables) is a registered start, not a critical cone.
4. Depth: PASS by construction. Loop paths: macro Q (1rw 256x64 TT ~340 ps) -> 2:1 -> macro address (~450 ps);
   decision = 32-b compare of two flops; counter forward = 32:1 x 32 b from a flop index. No in->out comb path.
5. Storage: FIXED (was the v6 failure). Data 3 x 2 x 256x256 SRAM; metadata 4 x 256x64 SRAM. Remaining flop arrays:
   row-valid bits 5 x 256 b (single-bit reads), loop counters 32 x 32 b, cfg staging 2 x 512 b (fixed-slot writes);
   each <= 1.3 kb. (v6 ROWS 256: 32 kb of runtime-indexed flops.)
6. Floorplan: macros on the 43.2 lattice (data stack origin (172.8,43.2) abutted pitch 41.088; metadata column origin
   (43.2,172.8) abutted pitch 17.856); >= 20 um channels / core-edge margins (ref_tile gen PASS); W face uop_d1 1,536 b
   over 345.6 um = 4.4/um; aspect 1.08; one connected std-cell band. Outline is macro/pin-bound (6 data SRAMs + 1,536 W
   pins); std-cell util from the gate synthesis is recorded below.
7. Clock: one clock (clk_control) for logic and all ten macros; TT/FF pin-flop spread <= 80 from the gate; route
   io_hold_margin 0.03.
8. Schedule: no added edge on any port (cycle-exact to v6); the two constraints are met by the F20 programme target
   (start_pc at descriptor accept, 53-edge drain) and the compilers (dense loop ids); cost 0 cycles.

## Gate
(see gate_result.json; summary appended by the lane after the --cts gate)
