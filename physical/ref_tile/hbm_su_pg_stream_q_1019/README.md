# hbm_su_pg_stream_q_1019 (HBM d4g LIGHT SU slice stream sibling, one-root half on clk_ctl; H.STA.BLK.15.3.2)

Kit generator: tools/ref_tile/specs_hbm_su3/mk_pg_stream_split.py. RTL: ot_hbm_su_static_pg_stream_q
(rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_stream_split.sv, programme/multirate_bridge_split.sv).

Re-shape p2 (HBM-SAFE-PGSTREAM, 10-19): the pair is rotated and stacked as q 432 x 216 over s 432 x 216. Each half is 2:1,
and the pair is 432 x 432. Before, q was 86.4 x 432 (5:1) and s was 216 x 432, with the seam on one M4 column at 5.4/um.
In try 3 both halves hit GPL-0305 because the routability loop could not spread that face. Try 4 turned routability-driven
GPL off; the owner rule forbids that squeeze, so p2 keeps routability ON.
Faces: N slice S band 1,178 b (2.7/um, M3/M5), S seam 2,346 b (5.5/um over M3+M5), W clk_ctl/rst_n/bridge_rst_n.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS (in RTL). Every boundary bit is a register in RTL. Inputs go straight into the request / inject bank flops
  (the only logic is a 2:1 write enable). Outputs are bank, launch, serial_rr, tap or synchroniser flops. io_flop_at_pins
  (4 columns) places them at the faces. A wrapper stage on the seam would collapse the banked windows. Reset is landed in
  3 stages (one 3:4 epoch; reset_landing.json).
2 Reach: PASS. The longest face-to-face path is 216 um (one tile height), under 405 um.
3 Fanout: PASS. Bank write and read selects are per-bridge counters. The bank and launch data flops have no reset, so
  there is no bridge_rst_n fan-out.
4 Depth: PASS. A 2:1 mux sits between flops. The gate on the old outline measured depth 138 ps (q) / 220 ps (s).
  There is no combinational path from input to output.
5 Storage: PASS. Banks are 2-deep per bridge bit (a seam, not a delay line). There are no runtime-indexed arrays over 2 kb.
6 Floorplan: aspect 2:1 PASS. No macros. One full-width std-cell band. Pins on full faces at <= 6/um PASS.
  Utilisation WAIVED (pin-bound). The seam has 2 banks per bridge bit, which is needed for the coordinator's banked 3:4
  windows (req 4q/2q, ret 2q/4q, inj 3q/7q). It needs >= 391 um of face at 6/um, and <= 2:1 then forces 432 x 216.
  This tile has 3527 pins and 1,153 um2 (2,286 flops) synthesized. A 40-60 % outline cannot carry them: about 1,150 (q) / 1,660 (s) pins
  fit at 6/um. Fully meeting this item needs a hierarchy change (COORD / H-D4G): fold q's bank flops into the clk_ctl
  S band of the slice and s into the VM-bank / LG-tap neighbour, so the seam becomes internal.
7 Clock: PASS. One root per half (clk_ctl). The old q outline measured TT spread 79.1 / FF 75.2 ps. Seam arcs are die-level
  3:4 arcs with static windows, and die STA owns them. io_hold_margin is 0.03.
8 Schedule: PASS. The seam is static (no credits). Edge deltas are unchanged from TW3-PGSTREAM: ij +1 serial, pg_fault
  +2 serial, reset release +1 epoch, already given to H-D4G. The rotation changes only the slot geometry (H-D4G / TW5-HBM-DIE).
