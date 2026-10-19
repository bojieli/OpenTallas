# hcoll_gq_issue_k3_1019 (LEAD2-HBM/L2H-SU 10-19) -- GQ issue leaf, K source, structural floorplan redesign

Source: codex/hbm-gqissue-sram-proof-1019 @151a73129 (OT_GQ_FAN32, OT_COLLQ_SRAM) with the k2 clock leaves
(route.cts_sink 16 / 40 um, 2 levels, buffers every 40 um). Branch claude/l2h-gq-k3-1019 (base b523b57db + tools from main).
Parallel to k1/k2 (hcoll_gq_issue_k{1,2}_1019); bind the first that closes under the checklist, cancel the others.

Why (one failed gate/route = structural redesign):
- s1 gate (432 x 345.6, 8 SRAMs in a 3+3+2 grid) GRT stalled at the 14,460 s cap (GATE_GRT_RC=137); k1/k2 (same floorplan,
  only CTS changed) sat 3+ h in GRT at extra congestion iterations 24-27/30.
- Placed density map (k2 GATE_LAYOUT placed): std cells packed 40-56 % inside the 34.8 um channels between FACING SRAM
  pin faces; NE quarter empty. Each ot_sram_1r1w_128x256 face carries ~410 M4 pins over 41.04 um (10 pins/um), so every
  inner channel had two 10 pins/um faces plus the logic that serves them, on M2-M5 only (layer cap M5).
- k2 clock is fine: boundary pin-flop spread TT 76.5 / FF 67.1 <= 80 (all-pin 124/101 guidance).

Change: one 4-high SRAM column per quantiser (aq0 at x=86.4, aq1 at x=302.4; rows y=43.2/129.6/216.0/302.4, all on
the 43.2 lattice, R0). Outline 432 x 345.6 -> 475.2 x 388.8 (aspect 1.22). Channels beyond the 16.2 um pin-face
halos: W 70 um, centre 89 um, E 62 um; N/S macro faces carry no pins (45 um row gaps). Everything else = k2.

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- every input captured at the pin / every output a flop Q (RTL stage table); reset_landing 2 stages, rst_n x4 copies, relay split <=32.
2 Reach: PASS -- 475.2 x 388.8 tile; logic sits beside its SRAM column; the gate long-wire / reg->reg report confirms no single-cycle wire > 405 um.
3 Fanout: PASS -- mapped census (results/rtl/gqissue_sram_1019/ctl_fan32_1019, netlist e0716f0c) all 24,548 register outputs <=32 loads incl. reset; kept copies.
4 Depth: PASS at source -- registered one-hot selects one edge ahead, scale s3->s4 split (r4).
5 Storage: PASS -- quantiser lines in 8 x ot_sram_1r1w_128x256 SRAM rings (no flop rings).
6 Floorplan: FIXED here -- macros on the 43.2 lattice in two columns, no facing pin faces closer than 89 um, >= 62 um channel
  beyond every pin-face halo for the 10 pins/um SRAM faces; tile pin faces 2.3-3.1 pins/um (full faces); one std-cell band.
  Utilisation ~13 % std / ~30 % incl. macros: WAIVED below 40 % with reason -- the tile is SRAM-pin-face bound
  (8 x 820 macro pins), the 34.6 % version did not route in 4 h.
7 Clock: PASS -- single root on a small tile, short local leaves (16 / 40 um); k2 measured boundary spread 76.5/67.1; io_hold_margin 0.03.
8 Schedule: PASS -- static; 0 added edges vs k2 (floorplan only).
