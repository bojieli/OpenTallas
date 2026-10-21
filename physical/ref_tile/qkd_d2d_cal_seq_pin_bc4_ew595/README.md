# qkd_d2d_cal_seq_pin_bc4_ew595 (KV-EMBWIN16 10-20)

The CLOSED bc4 KV link-end calendar sequencer (`physical/ref_tile/qkd_d2d_cal_seq_pin_bc4`, module `qkd_d2d_cal_seq_pin_bc4`)
re-hardened on the **grown embedding window** pair image `d2d_cal_image_mu_ew595.svh` (DRIVE-KV 10-20 decision: token-run
embed window 272 -> 595 so the embedding fill meets the row header slot on the GEN9 relays, KV-CAL15 finding).  Source
`qkd_d2d_cal_seq_bc4_ew595.sv` = `qkd_d2d_cal_seq_bc4.sv` with only the `include changed (tools/qwen_static_kv/gen_dcal_bc4_ew.py;
it refuses an image whose TXDP / segment bases / admission constants differ).  What changes in the netlist: the compile-time
START table (L1..L35 +323), D2D_TOKEN_PERIOD 249,600 -> 250,368, and the TX/RX init images.  Same ports, outline, pins
(io_pins.tcl copied), reset landing, edges.  Bound by kvsys_prep when OT_KV_EMB_WIN=595 (default kit name).

## Benches (Verilator 5.050, fleet; witnesses `results/rtl/kv_embwin16_1020/`)
Both bench scripts take `EW=595`: the reference (frozen bc2 wrapper / MU pin tile) and the tb include the ew595 image via
an include override; the DUT is the ew595 source.
- `run_dcal_bc4_production.sh OUT MUT`: MUT 0 PASS; 1..5 FAIL as bc4; **7** target 11 from the BASE (272) window image on
  the ew595 tile: FAIL (stale boot image for the grown window).
- `run_dcal_bc4.sh OUT MUT`: 600k-edge miter vs the frozen bc2 wrapper on the ew595 image: PASS; 1..3 FAIL; **7** reference on
  the base window image: FAIL (mismatch).

## SAFE-DESIGN CHECKLIST (owner 10-19)
1. Pins: PASS (unchanged from bc4): RTL captures every input once, every output a tile register; 2-stage RTL reset landing
2. Reach: PASS: 25.92 x 34.56 um tile
3. Fanout: PASS (bc4 structure; pre-gate native census re-run by the gate on this netlist)
4. Depth: PASS (bc4 structure; image constants only)
5. Storage: PASS: compile-time image constants and boot words; no runtime-indexed flop arrays
6. Floorplan: PASS: bc4 outline / pins (no macros, one std-cell band, aspect 1.33)
7. Clock: PASS: S centre clock entry; TT/FF pin-flop spread checked at the --cts gate (<= 80); io_hold_margin 0.03
8. Schedule: PASS: static; the +323-edge window (token period +768 after the 768-edge alignment) is compiled once in
   d2d_link_calendar --emb-window and bound on both link ends (KV target 11 + this tile; compute side LEAD9-QW)

Gate review (PNG inspection per item) is appended below after the --cts gate.

## Gate review (--cts, 37d8f203e, gate_result.json): WARN 0 fail
- util WARN only (std 264-277 um2 in 653 um2 core = 40-42%, same as the CLOSED bc4 at this die slot outline; kept: the slot is the die's).
- PRE-GATE NATIVE CENSUS: mapped dynamic load limit32 PASS, max 28.  355 flops, depth 438 ps.
- Clock: one root (ck, 355 sinks), TT/FF insertion 93.4/70.6 ps, pin-flop spread TT 3.3 / FF 3.3 ps (<= 80).
- Trial GRT overflow 0 (M2 22.1%); placement setup WNS +156 ps, hold +49 ps.
- PNGs inspected (gate_layout/floorplan.png, density.png): no macros; W/E pins full-face centred, S clock centre with reset/reload
  beside it; one std-cell band, density even across the core (no hot spot, no island); M5 PG stripes full length.
- Checklist items 1-8 confirmed at the gate (above).
