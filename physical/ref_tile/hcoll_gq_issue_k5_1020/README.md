# hcoll_gq_issue_k5_1020 (LEAD4-HBM/HBM-COLL6 10-20) -- gq issue leaf (H.STA.BLK.3 / 16.5), STRUCTURAL redesign after k3 FAIL and k4/k4b GRT congestion

Branch claude/coll6-gq-k5-1020 (base HBM-COLLFUSE2-VME af944e962 = k4 S2TOP/FAN32 leaf + VM_RT 74 SRAM ring + ISSUE_AHEAD 1;
p192 SRAM view from origin/main). k5 and k5b are PARALLEL geometries of the same RTL; bind the first that closes, cancel the other.
Params VM_RT 74, ISSUE_AHEAD 1 (the die's hcollgi bank-latency class); defines OT_COLLQ_SRAM OT_GQ_FAN32 OT_GQ_S2TOP OT_GQ_P192.

## Why
- k3: trial GRT overflow 206, every marker in the aq0 SRAM gaps / on its 10 pins/um E face; logic crowded into the gaps.
- k4/k4b (abutted 41-um stacks, off-lattice pitch 41.088): still in GRT congestion extra iterations after ~5 h (same signature).
  Root cause in both: each 128x256 macro carries ~410 M4 pins on a 41 um face (10 pins/um); no channel width escapes that.

## Change (structural, no RTL function change)
- OT_GQ_P192: the quantiser element-line SRAMs instantiate ot_sram_1r1w_128x256_m1_r2c2_p192_mir = the same array with its pins at
  0.192 um pitch (94.824 x 80.472, ~410 pins per 80.5 um face = 5.1 pins/um <= 6). Same ports, same behavioural model (diff = name).
- Two regional halves: aq0 + its 4-macro stack on the W, aq1 + its stack on the E (MY so both busy rd_out/wd faces face OUTWARD into the W/E
  channels; the centre only sees the light faces: tied w_mask + wd 119); the shared event/VM-request/ring/target logic in the centre band.
  Each half's crossing to the centre is flop->flop (aq_x register -> aq13 S0 pin register; aq13 output registers -> aq_q_q), i.e. landed.
- Stacks on the literal 43.2 lattice (pitch 86.4, 5.9 um N/S gaps carry no pins; rows cut there by MACRO_ROWS_HALO_Y 3.24 so no cells
  crowd into them). Pin-face halo 21.6 um. No SRAM pin face abuts another macro face, a tile pin face or a lane face.
- Geometry: 475.2 x 475.2 (aspect 1.0); stacks y 86.4..426.1, aq0 x 86.4 R0, aq1 x 302.4 MY; centre band 121.2 um; S corridor 86.4 (VM ring macros (216,43.2) R0 / (259.2,43.2) MY), N corridor 49.1.
- Clock: clock_split_km K=8 regional roots on clk (k3 single root measured 99.1/86.6 ps spread).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input captured at its pin / every output a flop Q (gather stage table); reset_landing 2 stages, rst_n x4 face copies.
2 Reach: PASS -- each quantiser's logic sits beside its own stack; centre band to either stack < 250 um; gate long-wire check rechecks.
3 Fanout: census at this gate (mandatory pre-floorplan native32 census; k4 K-census max 32, IA/VM_RT ring adds per-stage copies).
4 Depth: PASS (k4 S2TOP removed the 768 ps s2->s3 path); TT setup measured at this gate.
5 Storage: PASS -- 8 x 128x256 element-line SRAMs + VM_RT SRAM ring (2 x 64x16), no flop arrays.
6 Floorplan: FIXED -- macro faces 5.1 pins/um, macros on the 43.2 lattice, busy faces outward to wide channels, no abutted pin faces,
  no gap pockets, one std band, aspect <= 1.2. Utilisation WAIVED below 40% (fill_reason pin_bound).
7 Clock: FIXED -- K=8 regional roots (clock_split_km); pin-flop spread <= 80 ps TT+FF checked at this gate; io_hold_margin 0.03.
8 Schedule: PASS -- static; 0 added edges vs k4ia1 (SRAM view swap only).

## Benches (job): k4ia1 bench set with OT_GQ_P192=1 (aq_sram_exact + slot mutant, aq_s2top + K mutant, COLLQ_IA ia1/ia2 + slot/dep/iaign).
