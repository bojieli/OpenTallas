# CLK-INV-CAL-1 (2026-10-28): inverter clock (CKINVDCx16) calibration of the shared die clock model

Owner lane CLK-INV-CAL-1. Branch `claude/clk-inv-cal-1-1028`. Shared tools: `tools/die_plan/{die_sta_related,count_align_plan,trial_tap_arrivals,clk_inv_cal}.py`,
`tools/s81_head/landed_phase_ocv.py`, `tools/die_plan/clk_aocv_table_g021.json` (classes **Ainv / Ainv2** added, A/B/g/droop/net rows and the stored grids unchanged).

## 1. Estimate (written before the build)

- The trial9/10 inverter trees were timed with the BUFx24 model: class A (s_cell 3.885 %, cell share 0.533, mu_cell 53.4 ps) applied
  per CKINVDCx16 and SPICE_CLOCK_CAL 1.0485/1.0552. Per inverter (~42 ps/stage at rep 250) that gives random 3 sigma ~2.6 sqrt(N) ps.
- CKINVDCx16 is 56 parallel 3-fin devices per cell (no small first stage like BUFx24), so s_cell should be lower (~2-3 %).
  Expected random term 1.5-2.0 sqrt(N) ps, so 10-25 % less clock OCV on the inverter trees. Counting pairs as BUF stages
  (NUMBER-CHECK sensitivity) costs about 2 ps on the min crossing.
- Spice factor: a 1 % change shifts crossing d by a few ps (0.01 x |Delta arrival| of 300-1000 ps). Any change must be planned again (K), not just re-margined.
- Expected impact: QC min lo stays at the quantisation floor (about 104-106 by construction), with a few ps more margin on hi. Risk: the spice factor could go either way.

## 2. Method (same as class A / OSS-CLOCK-2)

- MC (`clk_inv_cal.py mcgen/mcparse/mcfit`, the clk_aocv_mc method): ngspice r3 (`ot-ngspice:r3`), BSIM-CMG 111, ASAP7 r1p7 xAct3D cells, Pelgrom
  A_VT 1.2 mV.um per transistor (sigma_Vt 18.45 mV per 3-fin device, 56 devices per CKINVDCx16). The chain is inverting, depth 8,
  stage = cell -> NDR M8/M9 wire (45-um pi ladder) -> next cell, and stage 1 is dropped. A pulse input gives an output-rise and an output-fall delay per stage.
  Wire 250 um (QC/HEAD rep) and 150 um (KV rep), TT + FF, 200 decks per set (199 parsed). Lib regenerated with `mkcells.py` from the
  same xAct3D netlists as the class A run (`intel1:/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028/lib`).
- Spice vs OpenSTA (`clk_inv_cal.py treegen/compare`, OSS-CLOCK-2 method): comb trees (48-stage trunk, side branch of 2 stages to a sink every 8 stages)
  with identical SPEF ladders in ngspice and OpenSTA (ASAP7 INVBUF RVT NLDM). Affine fit spice = a x STA + b over both sink edges.
  The BUFx24 450-um control is run on the same bench.
- Gate rows: `clk_inv_cal.py table` takes the envelope over the wire lengths. s_cell, rho and cell_share are the max (the
  conservative side), and mu is taken from the 250-um row.

## 3. Results

AOCV rows (class Ainv = one inverter = one stage; Ainv2 = one inverter pair, for information and the planner):

| class | corner | mu_cell ps | mu_stage ps | cell_share | s_cell | sigma_stage ps (250/150) | fall-rise ps/stage (250/150) |
|---|---|---|---|---|---|---|---|
| Ainv  | TT | 21.589 | 42.056 | 0.6248 | 0.02517 | 0.543 / 0.338 | -2.82 / -1.54 |
| Ainv  | FF | 15.316 | 36.206 | 0.5367 | 0.02678 | 0.410 / 0.243 | -2.92 / -1.56 |
| Ainv2 | TT | 43.149 | 84.039 | 0.6247 | 0.01717 | 0.741 / 0.488 | -0.06 / -0.04 |
| Ainv2 | FF | 30.618 | 72.333 | 0.5369 | 0.01835 | 0.562 / 0.326 | -0.01 / -0.02 |
| A (BUFx24, unchanged) | TT / FF | 53.386 / - | 100.239 / - | 0.5326 / 0.4585 | 0.03885 / 0.03992 | 2.07 | - |

- Random 3 sigma per branch of N inverters: about 2.0 sqrt(N) ps TT on the gate row (direct MC 1.6 sqrt(N)), compared with 2.6 sqrt(N) under class A per inverter.
  rho is about 0 (lag 1/2 measured -0.07..+0.02; lag 1 0.021 TT-150 kept). Per mm the g/droop/net rows are shared.
- Fall-rise asymmetry: each inverter stage is 1.5-2.9 ps faster on its output-fall. Over a pair it cancels (<=0.06 ps per pair), so even-depth taps keep their duty cycle.
  On the 48-stage comb tree the duty shift at the sinks is spice -8.6..-0.6 ps (TT, rep 250) and -3.3..+0.1 ps (FF).
  The BUFx24 control shows +8..+137 ps over 42 stages (the known BUF low-phase loss).
- Inverters per mm on built trees: QC trial10 (inv2, rep 250, 39,086 CKINVDCx16) has 4.67/mm on legs >= 1 mm, 5.24/mm on legs of 250-1000 um,
  18.2/mm on legs < 250 um (H-tree nodes), and 9.93/mm over all 3,938 mm of wire. KV-12 kit_inv_r150 (15,048 CKINV + 136 BUFx24) has 7.30/mm on legs >= 1 mm,
  7.94/mm on legs of 250-1000 um, and 11.5/mm on legs < 250 um.
- Spice / OpenSTA (affine slope, both edges): NDR rep 250 TT **0.9207** / FF **0.9380**; NDR rep 150 TT **0.9324** / FF **0.9371**; 1x rep 250 TT 0.9333 / FF 0.9515.
  So OpenSTA NLDM is 6-8 % pessimistic for CKINVDCx16, the opposite sign to BUFx24. BUFx24 control on the same bench: rise slope 1.0537 / 1.0640 against
  SPICE_CLOCK_CAL 1.0485 / 1.0552 (+0.5 / +0.8 %, bench bias upward). **SPICE_CLOCK_CAL_INV = TT 0.9324 / FF 0.9380** (the larger NDR slope per corner).

## 4. Shared model change (one model, no fork)

- `die_sta_related.py`: `SPICE_CLOCK_CAL_INV`, `CLOCK_CELL_AOCV_CLASS = {buf: A, inv: Ainv}`, `spice_cal_factor(corner, cell)`, `detect_clock_cell`.
  Order of evidence: meta `clock_cell`, then the majority master in the proof clock netlist, then `run/clk/ctree.v` via the tap source. Default is buf.
  New flag `--clock-cell auto|buf|inv|inv2`. `sta_d_intervals` / `clock_ocv_fn` / `ca_ocv` are keyed by the cell, and the call fails closed if the table lacks the class.
  `count_align_plan` contexts, `landed_phase_ocv --clock-cell` and `trial_tap_arrivals` (meta clock_cell) also use it.
- BUF byte-identity, checked against the origin/main tools: trial8 (BUFx24) lpo, count_align_plan and die_sta_related JSON are IDENTICAL, and so is trial10 with `--clock-cell buf`
  (`byteid.out`, after the table change). Tests: 9 new (`test_clk_inv_cal.py`) plus the existing die_sta_related, count_align, clk_aocv and landed_phase tests, 101 PASS.

## 5. QC trial9 / trial10 built-arrival CA recompute (DIE-QC-11 runCA chain, my tools, auto cell = inv, ca_spice 0.9324/0.9380)

| | trial9 old (BUF model) | trial9 new (Ainv) | trial10 old | trial10 new |
|---|---|---|---|---|
| plan phase fail / min lo / min hi | 0 / 105.9 / 205.9 | 0 / 105.6 / 321.9 | 0 / 104.5 / 128.7 | 0 / 105.6 / 253.8 |
| die STA COUNT-ALIGN TT lo / hi | 105.7 / 207.0 PASS | 105.5 / 323.1 PASS | 110.6 / 129.9 PASS | 105.4 / 254.9 PASS |
| die STA COUNT-ALIGN FF lo / hi | 121.2 / 281.5 PASS | 105.5 / 390.1 PASS | 104.3 / 279.7 PASS | 106.8 / 388.8 PASS |
| ocv table max TT / FF | 306.5 / 257.3 | 272.1 / 227.7 | 306.0 / 255.6 | 272.2 / 226.6 |

The 5 NUMBER-CHECK near-floor crossings on trial9 (tool margin_lo; NUMBER-CHECK copy `ncca_inv.py` in brackets, the same plan):

| crossing | old tool | NC pairs-as-stages | new tool (Ainv, re-planned K) | NC copy, Ainv |
|---|---|---|---|---|
| coll_n__crec_rx_s0__1 / fltk__1 / fltv__1 | 105.9 | 99.5 FAIL | 137.8 | 136.4 |
| c_E4_bf_00__a22__0 | 112.5 | 97.9 FAIL | 145.4 | 140.6 |
| c_E5_bf_00__a22__0 | 113.4 | 99.8 FAIL | 146.3 | 142.4 |

- The NC copy (`ncca_inv.py` = NUMBER-CHECK-CA-1 `ncca.py` + `--inv-cal`) reproduces NUMBER-CHECK on the old plan: A 0 FAIL min 104.5; pairs 5 FAIL min 97.9.
- Old K with the inverter model gives 10 FAIL (t9) / 23 (t10). The K have to be planned with the model they are checked with, because the spice factor moves d by about 11 %.
- NC copy on the new plan: trial9 0 FAIL min 103.6. trial10: **3 FAIL min 94.5**, on sl_E4_su_c -> sl_E4_stm (x_su_c_ctl__0, su_l0/su_l1 stm; tool 105.6).
  d_lo agrees (-1089.2 vs -1088.6). The whole gap is wander: NC takes 0.05 x max unshared over all tap pairs and both corners (65.7 ps), while the tool uses 55.3 ps.
  This convention gap already existed (t10 old plan A: max |dm_lo| 14.3). It is not caused by the calibration.

## 6. Paths

intel1:/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028 (MC decks/dat `run/`, `mc_inv.json`, `inv_rows.json`, trees `tree2/`, control `tree/buf450`);
intel2:/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028 (`byteid/`, `qc/t9`, `qc/t10`, `nc/`).

## 7. CLK-INV-CAL-2: STA early/late gap = liberty pin-cap range (COORD 0c80c4558 / DIE-S81-16)

Cause. OpenSTA's min analysis loads every pin at the LOW end of its liberty `capacitance_range`. CKINVDCx16 A is 6.68-9.54 fF (rise) and 6.64-9.53 fF (fall); BUFx24 A is only 1.76-2.35 fF, on a 24x driver. With no derate, a 20-stage CKINVDCx16 chain gives max 156.6 / min 129.3 ps (-17 %), and a BUFx24 chain gives 437.0 / 431.9 ps (-1.2 %). The built trees show the same thing at every depth (QC t10 TT: tap late - early median 12.3 %, max 13.8 %). This is a load-model difference, not variation: ngspice gives one delay.

Spice vs STA on one tree path (48-stage benches, deepest sink, `spice_vs_sta_min.json`; table = Ainv/A random + net flat, no distance term):

| bench | spice | STA late | STA early | early/late | spice/late | spice/early | table +/- |
|---|---|---|---|---|---|---|---|
| inv NDR150 TT | 1263.8 | 1354.4 | 1197.1 | 0.884 | 0.933 | 1.056 | 22.9 |
| inv NDR150 FF | 1054.8 | 1124.9 | 984.7 | 0.875 | 0.938 | 1.071 | 21.2 |
| inv NDR250 TT | 2122.2 | 2301.6 | 2069.1 | 0.899 | 0.922 | 1.026 | - |
| BUF 450 TT | 4262.2 | 4044.6 | 3988.9 | 0.986 | 1.054 | 1.069 | 101.1 |

The AOCV table comes from ngspice MC, so it does NOT contain the cap range. `--clock-cal spice` multiplies late and early by the same factor (0.9324), so the gate adds the cap-range gap on top of the table. That double-counts it:

- inv NDR150 TT path, spice mode: late 1263, early 1116, gap 146.7, spread with table 192.5 ps.
- spice_edge mode: early 1226, gap 36.9, spread 82.8 ps.
- spice MC truth: +/- table = 45.8 ps.
- BUF: gap 58.5 of 260.6 ps. The BUF is left unchanged.

Fix: an opt-in in the one model, `--clock-cal spice_edge` (gate) / `--sta-clock-cal spice_edge` (planner and bind; plan == gate).

- Inverter late keys are multiplied by SPICE_CLOCK_CAL_INV (unchanged).
- Inverter early keys (tap + node, rise + fall) are multiplied by SPICE_CLOCK_CAL_INV_EARLY = TT 1.0241 / FF 1.0487. These are the smaller NDR spice/STA-min slopes, the hold-safe side. NDR150 measured 1.0550 / 1.0704.
- Early is capped at late.
- The CPPR node range is re-derived from the scaled node arrivals.
- BUF is identical to `spice`, and `spice` stays byte-identical. Tests: `tools/die_plan/test_clk_inv_edge.py`.

Built trees (die_sta_related, `--clock-cell inv`, table + shared droop + CPPR-LCA, no CA bind):

| proof | FF intra hold spice | spice_edge | neg pairs | TT intra setup |
|---|---|---|---|---|
| S81 go13 (S81 ran it with the BUF model: -1183.9) | -1049.1 | -1037.9 | 149402 -> 136022 | -508.6 -> -498.3 |
| QC t10 (proof_fall) | -249.0 | -232.3 | | 369.9 -> 387.3 |

On S81 the cap range is worth only ~11 ps at the worst pair. The worst intra pair is built skew (FF skew 1007 ps), not the model. The BUF-model fallback was worth 135 ps (-1184 -> -1049).
