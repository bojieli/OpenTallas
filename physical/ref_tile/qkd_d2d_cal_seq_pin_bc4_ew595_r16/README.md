# qkd_d2d_cal_seq_pin_bc4_ew595_r16 (KV-PROG17 10-20)

The CLOSED bc4 KV link-end calendar sequencer (module `qkd_d2d_cal_seq_pin_bc4`) re-hardened on the **ATTN_R16 pair image**
`d2d_cal_image_mu_ew595_r16.svh` (embed window 595 + the r16 attention tile: K RESULT +1 edge (TX_SHIFT) and K STATUS +213
(RETIRE_STATIC STATUS_DELAY) in every layer).  Source `qkd_d2d_cal_seq_bc4_ew595_r16.sv` = `qkd_d2d_cal_seq_bc4.sv` with only
the `include changed (tools/qwen_static_kv/gen_dcal_bc4_ew.py 595_r16; refuses an image whose TXDP / segment bases / admission
constants differ).  Netlist changes: the compile-time START table, D2D_TOKEN_PERIOD 250,368 -> 258,048, TX/RX init images.
Same ports, outline, pins (io_pins.tcl), reset landing, edges as bc4 / bc4_ew595 (generated kit files byte-identical modulo the
name).  Bound by kvsys_prep when OT_KV_ATTN_R16=1 and OT_KV_EMB_WIN=595 (default kit name).

## Benches (Verilator 5.050, fleet ot-epyc7; witnesses `results/rtl/kv_prog17_1020/`)
- `EW=595_r16 run_dcal_bc4_production.sh OUT MUT`: MUT 0 PASS; 1..5 FAIL as bc4; 7 target 11 from the base 272 image FAIL;
  **8** target 11 from the non-r16 595 image FAIL (stale boot image).
- `EW=595_r16 run_dcal_bc4.sh OUT MUT`: 600k-edge miter vs the frozen bc2 wrapper on the r16 image: PASS; 1..3 FAIL; 7 / **8**
  reference on the base / non-r16 image FAIL.

## SAFE-DESIGN CHECKLIST (owner 10-19)
1. Pins: PASS (bc4 structure): every input captured once, every output a tile register; 2-stage RTL reset landing
2. Reach: PASS: 25.92 x 34.56 um tile
3. Fanout: PASS (bc4 structure; pre-gate native census re-run by the gate on this netlist, below)
4. Depth: PASS (bc4 structure; image constants only)
5. Storage: PASS: compile-time image constants and boot words; no runtime-indexed flop arrays
6. Floorplan: PASS: bc4 outline / pins (no macros, one std-cell band, aspect 1.33)
7. Clock: PASS: S centre clock entry; TT/FF pin-flop spread checked at the --cts gate (<= 80); io_hold_margin 0.03
8. Schedule: PASS: static; the r16 per-layer tail (+214 edges/layer, token period 258,048) is compiled once in d2d_link_calendar
   (--attn-tx-shift 1 --status-delay 213) and bound on both link ends (KV target 11 + this tile; compute side LEAD9-QW)

Gate review (PNG inspection per item) is appended below after the --cts gate.

Gate (2026-10-21 00:37, exact source snapshot ff1b66d2d): WARN, zero failures. Native census maximum28, zero dynamic/reset violations; reset raw fanout1. Trial GRT overflow0, M2 use22.24%. TT/FF pin-flop spread2.0/2.0ps, setup+170ps, hold+49.3ps. The only warnings are utilisation40–42% in the existing DCAL slot. PNGs viewed: full W/E pin faces, S-centred clock, no macros, continuous standard-cell core, distributed density without isolated islands. Existing production/miter witnesses from8380bdc71 remain the behavioral basis. Proceed to route; this gate is not routed closure.
