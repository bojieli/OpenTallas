# hcoll_gq_issue_k4b_1019 (LEAD3-HBM/L2H-GQ4 10-19) -- GQ issue leaf (H.STA.BLK.3 / 16.5), structural redesign after k3

Branch claude/l2h-gq-k4-1019 (base k3 20e80f464 + tools/ref_tile, tools/closure_loop, physical/common_flow from origin/main).
k4 and k4b are PARALLEL variants of the same RTL + macro arrangement (k4 = checklist outline, k4b = k3 outline + balanced CTS).
Bind the first that closes under the checklist; cancel the other.

## Why (k3 FAIL, gate_result on claude/l2h-gq-k3-1019 0649bc0cf)
- trial GRT overflow 206 after 13,984 s (30 extra iterations, then the incremental re-route after repair_design ran > 2.5 h).
  All 168 overflow markers sit in aq0's column: in the 45 um gaps between stacked SRAMs and on its E pin face
  (x 85..187, y 53..154). Placed density: the logic mass sat in the centre channel and INSIDE the inter-macro gaps
  (cells pulled toward the 10 pins/um SRAM faces), while the E third of the tile was nearly empty. Total M2-M5 usage was only 22%:
  local pin-escape + gap crowding, not global demand. repair_design: 2,149 slew violations, 3,091 buffers (small).
- clock: TT/FF pin-flop spread 99.1/86.6 ps > 80 (3,649 boundary flops on four faces of a 475 x 389 tile, one root).
- depth: u_aq0.u_scale s2_pp0 -> s3_floor_q 768 ps / 21 levels (textbook), placement TT reg->reg -51.4 ps (s3_th[11]):
  the stage-3 decision mux waited for the 48-bit product carry chain.

## Change (structural)
- RTL OT_GQ_S2TOP (ot_hgi_coll_aq_scale13r.sv): product[47] = A >= ceil(2^47/B) = A[23] & A[22] & (inv6 | A[21]) for the
  two coefficient significands (0xAAAAAB, 0x924925), exact for every 24-bit A. Registered at stage 2 in 11 kept copies
  (one per 8-bit decision chunk); stage 3 selects d47/d46 from the registered copy. Same 5 edges, same numerics.
- Floorplan: each quantiser's 4 SRAMs form ONE abutted N-S stack (abutted_stack: pitch 41.088 = array + one M4 track, no
  pins on N/S faces), base origin on the 43.2 lattice (aq0 x=86.4 R0, aq1 x=302.4 MY). No narrow inter-macro gaps; the
  corridors above/below the stacks are full-width and macro-free. aq1 mirrored so both BUSY faces (rd_out 256 + wd 137)
  face outward (W and E channels, empty in k3) and the centre channel sees only the light faces (wd 119 + tied mask).
  Pin-face halo 16.2 -> 21.6 um; W channel 64.8 / centre 78 / E 56.4 um beyond the halos.
- Outline: 475.2 x 388.8 (k3 outline, aspect 1.22), stacks y 129.6..293.9, corridors S 129.6 um / N 94.9 um; fill 27%.
- Clock: k2 clock leaves + -balance_levels (k3 at this outline measured TT/FF pin-flop spread 99.1/86.6 ps).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input captured at the pin / every output a flop Q (RTL stage table); reset_landing 2 stages, rst_n x4 face copies, relay split <= 32.
2 Reach: PASS -- logic beside its stack; k3 textbook reach_worst 93.9 um; the gate long-wire / reg->reg report rechecks (no single-cycle wire > 405 um).
3 Fanout: PASS -- K census (all 24,548 register outputs <= 32 loads incl. reset); new S2TOP regs: 11 kept top copies x 8 selects, one 4-bit kept input reg (1 load each).
4 Depth: FIXED -- the 768 ps / 21-level s2 -> s3 decision path is gone (registered top bit); remaining stages measured at the gate (TT setup >= 0 required).
5 Storage: PASS -- 1024-bit x 9-edge element lines in 8 x ot_sram_1r1w_128x256 rings (no flop arrays).
6 Floorplan: FIXED -- macros on the lattice in two abutted stacks, busy faces toward wide channels, no facing busy faces, full-width corridors, one std-cell band,
  aspect <= 2. Utilisation WAIVED below 40% (fill_reason pin_bound): the outline is set by the SRAM pin faces, not std area (denser 33.6% versions stalled in GRT).
7 Clock: single source root with short local leaves (source-owned regional roots need backend support that does not exist yet:
  results/rtl/gqissue_sram_1019/ctl_fan32_1019/regional_clock_model.md); pin-flop spread <= 80 ps TT+FF is checked at this gate; io_hold_margin 0.03.
8 Schedule: PASS -- static; 0 added edges (S2TOP keeps the 13-edge AQ latency, II 1; COLLQ schedule check conflicts=0).

## Evidence (Verilator 5.050, fleet ot-run, source bcf14141b)
- results/rtl/gqissue_sram_1019/k4_s2top/: s2top_pos.log (SCALE13R_EQ PASS checks=2097152; AQ_TREE13_EXACT_PASS blocks1024 latency13 II1),
  s2top_mutk_fail.log (OT_GQ_MUT_S2TOP_K: SCALE13R_EQ FAIL errors=129317), aq_control_mutants.log (EC/SHIFT/SCALE/SCALE_DATA/S2TOP_K rejected),
  collq_full.log (OT_GQ_FAN32=1 OT_GQ_S2TOP=1 run_coll_gq_bench.sh: COLLQ positive + 4 faults + AQ13 + SCALE13R + m1..m7,kq1).
