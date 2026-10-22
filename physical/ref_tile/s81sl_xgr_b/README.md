# s81sl_xgr_b -- S81 end-slice u_xg master ot_s81sl_xgr (FALLBACK; S81-ELEM2-XGRING, 10-21)

Successor of s81sl_xgtxo_b (ot_s81sl_xgt_xo @ f5f35855d, native PASS 32/0/0).  Its --cts gate (ep9 PID 3256860) placed at
TT -429 ps (MAIN 3256858: -765 ps) with 6,805 failing register endpoints, all single-cycle hops of 17-26 levels over 800-1,370 um (ring-stop pin
decodes / input flops -> AND-OR -> output flops on the far face; the 24-SRAM read AND-OR -> frame register; one gd_b copy
per bank feeding both stacks), and clock pin-flop spread 84 / 86 ps > 80.  Not fixable by tool knobs (SAFE item 2 failed).

Top `ot_s81sl_xgr` (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgr.sv), SAME PORTS as ot_s81sl_xgt_xo (die binding = master swap of
u_xg):
- u_r `ot_s81sl_rstopr`: rstopt_xo + FACE flop on every input; the old input flops are now mid-tile relays (pure-wire
  hop face -> relay) and every kept select is decoded from the face flops (no pin -> select path, no input delay on logic).
- is face stage (is_v / is_d), so the issuer word keeps its relative timing to the gather beats.
- u_s `ot_s81sl_xs5`: xs4 + E2 compact lookup codes + per-bank kept one-hot copies, E3 per-bank registered read
  partials beside each bank column (kept ot_s81sl_xs5_ln lines, 32 loads each), E4 OR of 3 partials = main stage 3 + 1;
  bc_hr / lane selects / issuer fault flag aligned; S / N half-stack gather write copies gd_bs / gd_bn.
Floorplan: xg5fb map 648 x 864 unchanged (narrower W<->E crossing, stream ROMs already grouped in the N ROM column).

## Cycle delta vs ot_s81sl_xgt_xo (-> MU.S81.CAL, ring calendar)
- ring stop (line in -> line out, V fragment / assembled beat, own beat -> line, NX, dl_*, head XB egress s_0N -> ro_w):
  **+1 edge per stop** (face stage).  Per tier line of 8 stops: +8 edges per full traversal.
- slice x path (issuer word / gather beat -> xw frame word): **+2 edges** (face stage +1, xs5 read partial +1); frame word =
  production lane word + OFF - 1 (xgt_xo: OFF - 3; xg_xo: OFF - 4).  fault +2 (status only).
- All internal relative timing (gather write -> buffer read, issuer -> calendar -> stream head) unchanged (xs5_equiv).

## Benches (Verilator 5.050, ot-epyc5; logs results/rtl/s81_xgring_1021/bench)
- xgr_fb_bench (tools/s81_slice/xgr_bench.sh, top ot_s81sl_xgr): production static PQ slot lockstep at the ring
  pins, x path compared at +dextra=3 (main xg + 3), 7 positive cases + offm1 / muttiercol / mutbank / mutoff / mutwcopy /
  mutexp FAIL as expected.
- rstopr_bench (tb_s81sl_rstop_sid + tb_s81sl_rstop_xo, master swapped): sid 16 stops + egress rules + 16-stop die ring
  80/80; mutants xooff / xoall / xonoflag / tiercol FAIL.
- xs5_equiv (xs5 vs main ot_s81sl_xs + 2-edge input relay, 23 cases incl. in-flight reset + 10 fault injections) PASS;
  6 mutants (bank / off / qswap / wcopy / tpar / exp) FAIL.

## SAFE-DESIGN review (8 points, owner 10-19 / 10-21)
1 Pins: PASS -- every input pin drives exactly one face flop (io_flop_at_pins fixes it at the pin), every output leaves a
  flop at the pin (ro_* / vo / nx_* / dl_* / xw_q / fault); recipe pin_regs off (the RTL face / relay stages are the priced pin registers).
2 Reach: FIXED -- ring words cross the 648 um tile as face flop -> relay (pure wire) -> AND-OR -> output flop at the pin:
  2 registered hops (<= ~350 um each with the relay mid-tile; the MAIN kit adds a third, output relay stage);
  read data: macro -> bank partial (bank column, <= 300 um) -> OR3 -> bt_d (centre) -> lane xw_l -> xw_q at the pin;
  write data: gd_a -> per half-stack gd_bs / gd_bn beside the stack.  The --cts gate times every hop.
3 Fanout: kept copies as xgt_xo (rstopt DKS <= 30, xs4 kept helpers) + ot_s81sl_xs5_ln lines (32 data ANDs each, kept
  hierarchy so ABC cannot fold the source code onto 512 pins); per-bank one-hot copies.  Mapped native census (census.sh,
  ORFS keep-regs hook): results in results/rtl/s81_xgring_1021 (c_xgr_fb.log); the gate re-runs it (refuses > 32).
4 Depth: no hop carries more than one AND-OR level group plus wire (face hops are pure wire; xs5 E3 = line AND + 8-way
  AND-OR; E4 = OR3).  PASS by construction, timed by the gate.
5 Storage: unchanged 24 x 128x256 SRAM + 7 ROM + 6 exp SRAM macros (xs4 instance paths), rstopt 4-slot buffers.  PASS.
6 Floorplan: xg5fb map (37 macros on the lattice, split S / N stacks, macro-free centre band), unchanged; fill ~27% routing / perimeter-bound (11,914 face pins), waived-with-reason as xgtxo.
7 Clock: k-means regional roots K 16 -> 32 (clock_split_km.tcl, local tree per cluster under one balanced top tree; the
  face / output flops of each face land in their own clusters); pin-flop spread <= 80 ps TT+FF judged by the --cts gate.
8 Reset: control / valid only (rstopr ot_rst_relay leaves, xs5 regional leaves); face / relay / output stages are datapath
  reset_landing 2 stages.  PASS.
Schedule: static, no credits / backpressure; cycle deltas above handed to MU.S81.CAL.
