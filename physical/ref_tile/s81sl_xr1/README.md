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

## XR6 (S81-SAFE-FIX/XR1, 10-19): re-review after the 297c9bfab --cts gate

The XR5 `--cts` gate (agidock128 s81sl_xr1-20261019-065923) was WARN with 0 fails: pin-flop spread TT 52.9 / FF 52.6 ps, trial GRT overflow 0, hold +6.8 ps. But TT reg->reg was **-110.6 ps**: `erun -> 20-term sticky-fault OR -> ot_prs_00000_ff/D` (the pin_reg_split launch copy of `fault` at the S face), 877 ps arrival, ~470 ps of it buffered wire across the outline. `fault` itself had +18.8 ps. SAFE item 4 fails, so the gate was not submitted. Path log: codex b6b163e28 `results/.../gate_recovery/xr1_paths.log`.

Fix (structural, not a squeeze): the fault terms are registered per source region (`fa` input/RD, `fb` partial/ENG collector, `fc` send/inject; KEPT), and the sticky flag ORs three flops. Fault becomes visible 1 cycle later. Fault is a sticky check and never a schedule input, so there are 0 data cycles and 0 token-rate change. A parallel fallback kit, `s81sl_xr1f` (`FOREG=1`), adds a dedicated fault output flop (+2 cycles) and drops pin_reg_split.

| # | item | XR6 |
|---|------|-----|
| 1 | pins + reset landing | PASS. Unchanged; pin_reg_split still clones `fault` (its D is now a 4-input OR of local flops). |
| 2 | reach | PASS. The `fault` D cone is one OR of 3 flops plus `fault`, so the wire to the S-face pin flop is the only long segment. |
| 3 | fanout | Unchanged from XR5 (kept copies). |
| 4 | depth | **fixed**. The 20-term fault OR is split into 3 registered region terms. Remaining gate paths are rwr_c +50 ps. |
| 5 | storage | waived as XR5. |
| 6 | floorplan | waived as XR5 (pin-bound util). |
| 7 | clock | PASS: spread TT 52.9 / FF 52.6 ps. |
| 8 | schedule | PASS: +1 fault-visibility cycle (fallback +2). This is a diagnostic flag; it is not in the token schedule. Handed to MU-DIE-S81 INBOX. |

Benches: `results/rtl/s81_slice_1019/xr6` (base hb0/1 x 4 seeds, mutants; `fb_*` / `fm_*` = FOREG 1).

## XR7 (LEAD2-S81/SLICE2, 10-19): structural fanout/reset fix after the 67954d13c census

Input: the XR6 gate was WARN (TT +23.1 ps, GRT 0, spread 56.5/55.1), but the native census found 348 FF roots and 9 comb roots with more than 32 loads. RTL 88ed31216 makes 0 data-cycle changes:
- Reset only on valid/control state. Every kept copy is reset-free: it is recomputed every edge from reset state, so it reads 0 one clock into reset. `bo_r` resets only bit 0.
- `ot_rst_relay` has 8 regions instead of 4. Each region drives at most 32 reset loads; the largest is r6, with 30.
- Kept copies sized from mapped pins per bit (~3 for enabled flops and 2:1 muxes, ~4.4 for the 4:1 unpacker read). The rule is 8 bits per copy:
  - `rwe_c` 640
  - `rwr_c` 160
  - `un_c` 320 x 2 b
  - `pkw_c` 128
  - `tg1_c` 8
  - `tg4_c` 6 (new: send-config enables)
  - `evd_c` 60 / `pvd_c` 20 (new: e_v / p_v data enables)
  - `lov_c` 80 (16 bits each)
  - `cis_c` 69 (16 bits each)
- The wide classify muxes now sit behind registered one-hot select copies. These are RD payload 1024 b, CTL body 160 b, and V/SC cix 275 b.
  - Raw stage-1 words are `eb2` / `wb2` / `vb2` (+ `bb2` for HB).
  - Select copies: `rse/rsw` 128+128, `bse/bsw` 20+20, `cvc/cse` 35+35.
  - The classifier's comb fan-out now ends only on D pins of kept copies (a buffered tree into replicated registers). The old 1,043 / 548 / 328-load comb nets drove the datapath directly.
- `eoh` / `poh` / `erun` now have lock-step kept copies (`eoh1`, `poh1`, `erx[3:0]`).

| # | item | XR7 |
|---|------|-----|
| 1 | pins + reset landing | PASS. Unchanged: 2-stage face landing, then the relay (8 regions <= 32). |
| 2 | reach | PASS (gate re-checks). Outline unchanged (pin-bound). |
| 3 | fanout | **fixed**. Yosys 0.68 + ot_keep_regs keep check: every copy survives at its exact RTL count (DFF 19,110; `results/rtl/s81_slice_1019/xr7s2/keep.txt`). Max generic DFF-Q load is 39 (`erx[0]`: x_si/x_s select). Comb classifier roots drive only kept-copy D pins (waived: a textbook buffered tree into replicas, 0 cycles). |
| 4 | depth | PASS. The selects are registered; the wide muxes are 2 levels after the stage-1 flops. |
| 5 | storage | **waived** as XR5: `ud` is 5 x 1 kb one-shot staging registers, under the 2 kb per-bank threshold. Each is written whole in a cycle and is not runtime-addressed storage. |
| 6 | floorplan | **waived (util)** as XR5: pin-bound, 7,651 pins. Std area grows about +2.3k FF; util is still < 10 %. |
| 7 | clock | gate-checked: km16 roots, spread <= 80 TT+FF, io_hold 0.03. |
| 8 | schedule | PASS. 0 data cycles; every port timing is identical (bench cycle-exact). |

Benches (Verilator 5.050, ot-epyc6, src 88ed31216, `results/rtl/s81_slice_1019/xr7s2`):
- base: PASS for hb 0/1 x seeds 1-4 (FOREG 0) and hb 0/1 x seeds 1-2 (FOREG 1).
- mutants hops / row / porder / nocol: FAIL (err 784 / 1599 / 1016, XRILL missed 1) on both FOREG builds. Witnesses are committed.
