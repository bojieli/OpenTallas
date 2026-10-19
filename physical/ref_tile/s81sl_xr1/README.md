# s81sl_xr1 (ot_s81sl_xr1): S81 slice control-plane sub-leaf

Generated kit (`tools/ref_tile/ref_tile.py gen spec.json`). History of the structure is in `spec.json` `structural_change`.

## Route record

- `s81sl_xr1-s81sl_xr1-1dd564c6f`: EARLY_FAIL_SETUP, TT -611 ps at 9,303 endpoints. This is the only failed route.
- Path classes of that route (`cl/early_fail.json`):
  - reg->reg `sid_c -> sw_d[240]`, -674 ps at 770 ps. The path is logic-dominated (cell 1,021 ps, wire 312 ps, fanout 32): a pin flop drove a 1.1k-bit source select, which drove 5x1024 unpacker enables, all in one cycle. That is a **depth** failure.
  - reg->out `c_d[679] -> cfg_d[39]`, -404 ps. Synthesis had folded equal-D port copies, so one flop drove pins on two faces. That is a **fanout/reach** failure.
- Already fixed:
  - XR2 added the classify stage (+1 cycle) and kept port registers.
  - XR3 made single copies, fanned out in the slice glue.
  - XR4 added 16 k-means clock roots.
  - HOURLY/XR1 added pin_reg_split for `fault`.
- km16 `--cts` gate @c0a1bbe0c (ot-pve1, collected 10-19) was WARN with 0 fails:
  - pin-flop spread: TT 44.0 ps, FF 39.1 ps;
  - setup reg->reg: +54.8 ps;
  - hold: +26.4 ps;
  - trial GRT overflow: 0.
  - Log: `results/rtl/s81_slice_1018/xr4/gate_km16_c0a1bbe0c.log`.

## XR5 (S81-SAFE-FIX/XR1, 10-19): SAFE-DESIGN CHECKLIST

| # | item | result |
|---|------|--------|
| 1 | pin registers + reset landing | **fixed**. Every input lands in a flop and every output leaves a flop, in the RTL (source-registered; recipe pin_regs off with a reason). pin_reg_split clones the sticky `fault` launch flop. `reset_landing` is now on with 2 stages: `rst_n -> __ot_rl0 -> __ot_rl1 -> ot_rst_relay`. |
| 2 | reach <= 405 um per cycle | PASS. The outline is 311x395 um. Pin flops sit at the faces, and the core mass sits beside the W face (sw_d / ud). |
| 3 | fanout <= ~32 per register in critical cones | **fixed**. KEPT copies are registered from each master's next state: `rwe_c` 160 (ud word enables, was 1,036 loads per bit), `rwr_c` 40 + `un_c` 160 (sw_d select and 4:1 row-pair mux, was ~512), `pkw_c` 32 (pk pair writes, was 256), `cis_c` 35 (ci_r select, was 1,103), `tg1_c` 2 (x_eps/x_scale, was 65), `lov_c` 40 (lo_v input-flop copies, was 256). The x_s word select is now a registered one-hot (`eoh` 15 / `poh` 5; el/ekd/pi drove 480/160/160 loads). Keep is a wire attribute (`ot_keep_regs.tcl`), so it does not depend on paramod names. The gate's flop count must rise by about 490 over 16,241. |
| 4 | depth <= ~600 ps / stage | PASS. Textbook depth is 288 ps. The XR2 classify stage registers the selects before the wide writes. |
| 5 | storage > 2 kb in SRAM | **waived**. `ud` is 5 x 1,024 b (1 kb per leaf, under the 2 kb threshold): each is a one-shot row-pair staging register, written whole in one cycle and read in 4 beats through the kept one-hot / copied selects. A 1,024-b one-cycle write port is no SRAM shape. The 4:1 read select uses `un_c` copies. |
| 6 | floorplan | **waived (util)**. The tile is pin-bound: 7,651 signal pins at <= 5.95 pins/um on full faces (E 2,214 / W 2,070 / N 1,708 / S 1,659). Synthesis area is ~8.1 k um2. 50 % util would mean ~127x127 um, which needs ~15 pins/um. 40-60 % needs fewer slice-seam bits, which is an architecture change and a coordinator call. There are no macros. One std-cell band covers the whole core. Aspect is 1.27. |
| 7 | clock | PASS (km16 gate): 16 k-means regional roots. Pin-flop spread is TT 44.0 / FF 39.1 ps. Insertion is TT 496 / FF 409 ps, matched by parent compensation. `io_hold_margin_ns` is now 0.03 (was 0.025). |
| 8 | static schedule | PASS. There are no credits or backpressure, and XR5 adds 0 data cycles. Reset assert/release grows by +2 cycles (landing), a scheduled constant. The XR2 classify stage (+1 cycle on CTL / RD / lo / V / SC) is handed to MU-DIE-S81 INBOX 10-19. |

Benches (Verilator 5.050, ot-epyc6, `results/rtl/s81_slice_1019/xr5`):
- `xr_bench` base: PASS for hb 0/1 x seeds 1-4.
- Mutants hops / row / porder / nocol: all FAIL, as expected. Their witnesses are committed.
- `slice_eng` / `slice_lep` compositions (bench source lists fixed for the cap_tr/cap_rt split and ot_hdc_delay_rf): receipts in `results/rtl/s81_slice_1019/xr5_slice` (outside the gate-consumed paths).
