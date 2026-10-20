# hbm_sfucore_k9x -- structural successor of k9w (LEAD3-HBM/L2H-SU-FB, 2026-10-19)

Parallel variants (bind the first to close under the checklist, cancel the others): k9w (running, ep6 GPL), **k9x** (this kit),
**k9y** (fallback: k9w floorplan + the broadcast tree only).

## Why (cause of the k9s2 / k9r / k9w GPL stalls)
k9w gate ep6 ref_gate/hbm_sfucore_k9w-20261019-171616, 3_3_place_gp: routability iterations at overflow 1.17 -> 1.09
(4.0-4.1 % gcells overflowed), timing-driven repair over 424k nets, after k9s2 (congestion 1.078, +58k buffers / 39k long
wires) and k9r (GATE_STALL) on the same RTL. Flop census of its 1_2_yosys.v: 85,579 flops flat in the parent, of which
- 29,440 lane-mapper pass ring flops (16 lanes x 460 b x (3 slots + output)) + ~12k mapper capture / select / add flops:
  the mono mapper (grid BTREE=0) had **every one of the 1,022 controller broadcast bits drive 16 lane captures spread over
  all four faces of the 1.9 mm tile in one unregistered hop** from the N-face control register (a star hub, reach 1.5-2.9 mm);
- 11,296 VM-bridge metadata + 6,144 scalar-address flops: **65-deep flop shift chains** (READ_RETURN = 14 + 2 x 25) with a
  synchronous clear on every stage (safe-design item 5 violation; k9w README item 5 said PASS -- it is not).
Moving SRAM columns (k9w) cannot fix either: the wires are 16-way tile-wide nets, not pin-face channels.

## Change (RTL claude/hbm-safe-k9x-1019, opt-in params, defaults bit-identical for every other user)
- grid BTREE=3: `ot_hgi_sfu_bcast_tree4` (rtl/hbm_accel/generic/peers/ot_hgi_sfu_lane_map.sv): a four-level registered
  distribution tree of KEPT copies -- L0 2 (W+S / N+E halves), L1 4 (faces), L2 8 (lane pairs: pair sums + mapped metadata,
  lane index constant), L3 16 (lane: final add, metadata, emit, pass) -- on the mapper's own four edges. The pass payload is a
  plain delay, so its four edges are the tree levels: 13.8k flops instead of 29.4k, no per-lane ring, no star.
- bridge BRING=1: `ot_hgi_sfu_delay_sram` -- each 65-edge delay is a ring in one ot_sram_1r1w_128x256_m1_r2c2 on the same
  root (write wp, read wp - 64 every edge, registered read = last stage) + a 7-bit fill counter (output 0 until 65 edges
  after release = the cleared chain). 4 lg rings (clk_lg[g]) + 1 scalar ring (clk). -17.4k flops.
- Floorplan = k9w + lanes 5 / 13 moved x 691.2 -> 734.4 (opens a 43.2-lattice slot in the N / S lane gaps); 4 lg rings stacked at
  x 604.8, y 43.2/129.6/216/302.4 (S gap), scalar ring x 604.8 y 1555.2 (N gap). N face: compiler_control centred
  691.2-1209.6 (tree source at the tile centre), clk/rst_n/clk_lg/rst_lg_n/clk_st 1218.24-1250.64, io_word/fault
  1259.28-1749.6 (die slot pin change -> H-D4G / TW5-HBM-DIE; ports unchanged).
- Schedule: 0 edges (results/rtl/hbm_safe_k9x_1019/schedule.md); cycle-identical, proven by the lockstep bench.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins | PASS (as k9r): keep_pin_regs, OT_OFLOP_HOPS 2, every reset lands 2 stages at the face; kept reset trees <= 32 loads |
| 2 | Reach | fixed: the 1,022-bit controller broadcast is now 6 registered segments (pin reg -> quarter control -> L0 -> L1 -> L2 -> L3 -> lane leaf pin reg) from a centred N-face source: <= ~400 um per segment to the farthest lane (was one 1.5-2.9 mm hop). Gate confirms reg->reg distance |
| 3 | Fanout | fixed: every tree flop drives <= 2 next-level copies / one lane pair; copies (* keep *) + ot_keep_regs (no opt_merge fold); pass rings and their one-hot (1,381 loads -> PASS_OHREP) are gone; resets as k9r |
| 4 | Depth | PASS: tree levels are pure captures or one 24-bit add (pair sums at L2, final at L3, = mono's stages); WPIPE / WROT / drain stage as k9r |
| 5 | Storage | fixed: no runtime flop store > 2 kb; the bridge's 65-deep delay chains (2.86 kb x 4, 6.24 kb) are SRAM rings; operand storage 80 SRAMs |
| 6 | Floorplan | PASS: all 85 macros on the 43.2 lattice; 128x256 rings in lane gaps (<= ~150 used pins per macro); bands as k9w; fill ~51 %; square 1900.8 |
| 7 | Clock | as k9w: regional roots (clk, clk_pw/pe, clk_st[4:0], clk_lg[3:0], clk_map/clk_lane[15:0]); tree level k runs on the clk_map root of its first lane, rings on their lg root / clk; crossings flop-to-flop judged per pair TT/FF <= 80; io_hold_margin 0.03 |
| 8 | Schedule | PASS: static, 0 added edges (cycle-identical restructuring) |

## Evidence
- Benches ot-epyc9 Verilator 5.050 (src 11ab8d016): see results/rtl/hbm_safe_k9x_1019/bench_witness_k9x/ (r23 positive +
  mutants skip_pinreg/clkpw/nodrainpipe/gclk/wpskew/wrot/rsttree + new tree4 (lane 13 pass skips L2) / bring (rings read 1 edge early)).
- Gate: pre_route_gate --cts --remote auto (pending_results.txt, L2H-SU-FB).
