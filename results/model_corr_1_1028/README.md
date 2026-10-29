# MODEL-CORR-1 (2026-10-28): spice correlation suite of the shared die clock model

Lane MODEL-CORR-1, branch `claude/model-corr-1-1028`. Tool `tools/die_plan/model_corr.py`, golden
`tools/die_plan/model_corr_golden.json`, fast test `tools/die_plan/test_model_corr.py`. The test lives in tools/die_plan, so it
runs in the die_plan chunks ROOT-MERGE already runs. It reads stored numbers only: no spice, no docker, 0.4 s.

Rule freeze 12.14: this checks the existing model against measured truth. It adds no design gate and changes no model number.

## 1. Reference set (fixed and versioned: `model_corr.CASES`, deck sha256 in the golden)

| case | cell | wire | taps (stages) | form |
|---|---|---|---|---|
| buf_ndr450_d50 | BUFx24 | NDR, 450 um | 5 / 20 / 50 | chain |
| inv_ndr250_d50 | CKINVDCx16 | NDR, 250 um | 5 / 20 / 50 | chain (odd tap = inverted) |
| inv_ndr150_d50 | CKINVDCx16 | NDR, 150 um | 5 / 20 / 50 | chain |
| inv2_ndr200_d50 | CKINVDCx16 | NDR, 200 um | 6 / 20 / 50 | even (pair) taps |
| buf_1x450_d20 | BUFx24 | 1x (default) | 5 / 20 | chain |
| inv_1x250_d20 | CKINVDCx16 | 1x | 5 / 20 | chain |
| buf_legs_1_2mm | BUFx24 | NDR | ends of 1/2/1/2 mm legs (3/5 stages) | fanout-2 node (100 um side branch) at every leg end |
| inv_legs_1_2mm | CKINVDCx16 | NDR | ends of 1/2/1/2 mm legs (4/8 stages) | fanout-2 node at every leg end |

- Each case is run at TT (0.70 V, 25 C) and FF (0.77 V, 0 C), on both source edges (rise and fall, which gives pulse width) and for both STA analyses (max = late, min = early).
  That is 96 arrival rows and 48 duty rows.
- Method: CLK-INV-CAL-1/2 (`clk_inv_cal` lib, cells, RC ladders, crossings). ngspice-42 `ot-ngspice:r3`, BSIM-CMG OSDI, ASAP7 r1p7 xAct3D.
  Spice and OpenSTA (`asap7lock`, INVBUF RVT NLDM) see the same Verilog and SPEF ladders. Arrivals are referred to the root cell input.
- Model value = the OpenSTA arrival passed through the shared model's ONE calibration step. That is `die_sta_related.apply_clock_cal` once CLK-INV-CAL-2 is merged.
  On today's main it is the gate's inline `scale_clock(spice_cal_factor(corner, cell))`. Every mode in `CLOCK_CALS` is used.
- Routed-SPEF path (brief item 1): **DONE in MODEL-REFIT-BUF (section 6).** The path is the HEAD hd_tile GRT SPEF path
  clk -> h16_n_RD -> h16_n_D1 -> 16 BUFx4 delay cells -> h16_t33_drv -> clkbuf_0_h16_t33/A: 20 taps, 19 nets, all side loads as real cells.
  Inputs are pinned on intel1 with sha256: 5_1_grt.odb ef1e07b7, grt.spef 42b0b7c6.
  The xAct3D BUFx4 transient aborts after a DC operating point. Ramping VDD from 0 with `uic` converges in both corners.

## 2. Gate (fast mode, `test_model_corr.py`, 25 tests)

The test FAILS when any of these holds:
- A model/spice ratio (late or early, rise or fall, TT or FF, any mode on main) drifts more than 2 % from the golden.
- Model early is later than model late on any row.
- The duty error drifts more than 2 % of the arrival.
- The golden's raw sha256 is broken.
- A clock-cal mode on main has no golden entry.
- The generator no longer writes the golden's decks.

Two mutants prove the check is live: a 3 % change of SPICE_CLOCK_CAL_INV fails, and BUF early set above late fails.

Full mode is `model_corr.py full --work DIR --lib LIB --osdi DIR`. It runs on fleet hosts only. It regenerates the decks, re-runs OpenSTA and ngspice in docker,
and fails when fresh spice or STA numbers move more than 2 % from the golden raw rows. The script is `run_ref.sh` (intel1, about 25 min, 18 x 1 CPU).

The golden holds modes none and spice (main 410e940f4f) and spice_edge (claude/clk-inv-cal-2-1028@5202cd13fb). On main, spice_edge is skipped with a note.
After the CAL-2 merge it is checked. A copy of CAL-2 plus this suite passes 20/20, and test_clk_inv_edge passes too.

## 3. Today's model against spice (all CHECKED, own runs; row = case x corner x tap x edge)

Ratio = model / spice, with ranges over taps.

| case | spice: late rise | late fall | early rise | early fall | spice_edge: early rise / fall |
|---|---|---|---|---|---|
| buf_ndr450_d50 TT / FF | 1.001-1.007 / 1.000-1.005 | **1.025-1.034 / 1.029-1.038** | 0.987-0.993 / 0.985-0.990 | 1.010-1.019 / 1.014-1.022 | = spice |
| buf_1x450_d20 TT / FF | 1.007-1.011 / 1.000-1.003 | **1.036-1.043 / 1.036-1.043** | 0.990-0.994 / 0.983-0.986 | **1.018-1.026 / 1.017-1.025** | = spice |
| buf_legs_1_2mm TT / FF | 1.008-1.010 / 1.009-1.012 | **1.027-1.033 / 1.032-1.038** | 0.991-0.996 / 0.994-0.996 | 1.009-1.019 / 1.014-1.023 | = spice |
| inv_ndr250_d50 TT / FF | 0.988-1.012 / 0.981-0.998 | 0.990-1.012 / 0.983-0.998 | **0.886-0.908 / 0.877-0.892** | **0.888-0.908 / 0.879-0.892** | 0.973-0.997 / 0.976-0.997 (TT), 0.981-0.997 (FF) |
| inv_ndr150_d50 TT / FF | 0.983-1.001 / 0.988-1.001 | 0.988-1.001 / 0.990-1.000 | **0.865-0.882 / 0.864-0.875** | **0.870-0.882 / 0.867-0.875** | **0.950-0.969** (TT), 0.966-0.978 (FF) |
| inv2_ndr200_d50 TT / FF | 0.985-0.996 / 0.985-0.992 | 0.980-0.996 / 0.981-0.992 | **0.880-0.890 / 0.876-0.883** | **0.876-0.890 / 0.872-0.882** | 0.962-0.978 (TT), 0.975-0.987 (FF) |
| inv_1x250_d20 TT / FF | 0.985-0.996 / **0.976-0.984** | 0.986-0.994 / **0.977-0.982** | **0.874-0.885 / 0.862-0.869** | **0.876-0.884 / 0.862-0.868** | 0.960-0.972 / 0.964-0.972 |
| inv_legs_1_2mm TT / FF | 0.987-1.008 / 0.982-0.996 | 0.979-1.006 / **0.975-0.995** | **0.885-0.903 / 0.877-0.888** | **0.878-0.901 / 0.871-0.887** | 0.965-0.992 / 0.974-0.993 |

Rows outside 1 +- 2 %:
- `--clock-cal spice` (main gate): 106 rows, of which 22 late, 67 early and 17 duty.
- `spice_edge`: 79 rows, of which 22 late, 40 early and 17 duty.

The full lists are in `report_main_spice.txt` and `report_cal2_edge.txt`.

1. **Inverter early (expected; the CLK-INV-CAL-2 double count).** Under spice, early is 0.862-0.908 of spice on every inverter row (TT and FF, both edges).
   That is the liberty pin-cap range applied on top of the spice factor. spice_edge brings it to 0.950-0.997. 40 early rows stay below 0.98, all of them on the
   conservative (hold-pessimistic) side: worst inv_ndr150 TT 0.950, inv_1x250 0.960. CAL-2 chose the smaller NDR slope on purpose.
2. **NEW: the BUFx24 source-FALL edge.** SPICE_CLOCK_CAL (1.0485 / 1.0552) was fit on rise. On the fall edge the model late is 2.5-4.3 % above spice
   (setup-pessimistic), and model early is 1.0-2.6 % ABOVE spice (hold-OPTIMISTIC on fall-edge paths; buf_1x450 1.017-1.026, buf_ndr450 FF up to 1.022).
   Raw OpenSTA: late rise 0.948-0.964, late fall 0.975-0.995, so OpenSTA NLDM under-reads the BUFx24 rise by about 4.5 % but the fall by only about 1.5 %.
3. **NEW: the BUF pulse width.** On NDR450, model fall-minus-rise exceeds spice by +11.6 / +11.9 ps at 5 stages and by +138.3 / +144.6 ps at 50 stages (TT / FF).
   On 1x450 it is +93 / +101 ps at 20 stages. OpenSTA over-states the known BUF low-phase loss, so BUF duty and MPW numbers from the model are pessimistic.
   Inverter duty error is <= 2.3 ps on every row.
4. Inverter late: 0.975-1.012. Four rows are just under 0.98 (FF 1x and legs), a slightly optimistic setup on late.

The posedge-flop gate (rise edge) on BUF trees is within 2 % for late and early. Findings 2 and 3 affect only the fall edge
(negedge / latch / MPW / duty checks). They are reported to COORD; there is no model change here (rule freeze).

## 4. Paths
- intel1:/srv/opentallas-scratch2/claude/model-corr-1-1028: `ref/<case>/` (decks, dat, OpenSTA), `raw_chain.json`, `lib/` (MD5SUMS), `osdi/`,
  `hd_tile/` (pinned routed inputs + path_{TT,FF}.txt), `ref/routed_hd_tile_h16_t33/` (first deck, DC-op form), `ref_r2/routed_hd_tile_h16_t33/` (golden routed deck + dat, SHA256SUMS), `dbg/`.
- intel2:/srv/opentallas-scratch2/claude/model-corr-1-1028: golden build (`g_cal2.json`, `cal2/` = CAL-2 tools copy), and the reports.

## 5. MODEL-REFIT-BUF (opt-in `--clock-cal spice_buf_edge`, COORD 10-28)
COORD asked for a refit of finding 2: falling-edge early above spice is hold-optimistic, and HEAD samples 12 stages on the falling edge.
The new mode `spice_buf_edge` scales BUFx24 arrivals per root edge and per analysis with `SPICE_CLOCK_CAL_BUF_EDGE` in die_sta_related.py.
Inverter dies get exactly spice_edge. none, spice and spice_edge are byte-identical (their golden ratios are unchanged). The default gate stays `spice` until NUMBER-CHECK confirms.

The fit is a bound, not a slope, over all 36 BUF golden rows per corner and edge (NDR450 50-stage, 1x450 20-stage, 1-2 mm legs).
- Late factor = MAX of spice / STA-late, so model late is >= spice.
- Early factor = MIN of spice / STA-early, so model early is <= spice.

| corner | rise late | rise early | fall late | fall early |
|---|---|---|---|---|
| TT | 1.0485 (= SPICE_CLOCK_CAL; max row 1.0472) | 1.0524 | 1.0226 | 1.0224 |
| FF | 1.0552 (= SPICE_CLOCK_CAL; max row 1.0551) | 1.0593 | 1.0256 | 1.0297 |

Golden BUF rows, model / spice (CHECKED, fast suite):

| mode | rise late | rise early | fall late | fall early | BUF duty error |
|---|---|---|---|---|---|
| spice | 1.0001-1.0124 | 0.9826-0.9963 | 1.0253-1.0430 | **1.0091-1.0256** | +3.4..+144.6 ps |
| spice_buf_edge | 1.0001-1.0124 | 0.9865-1.0000 | 1.0000-1.0172 | 0.9840-1.0000 | -2.0..+26.9 ps (<= 1.1 % of the arrival) |

Under spice_buf_edge no BUF row is outside 2 %, and every BUF row keeps model late >= spice >= model early.
The remaining duty error is +18.5 ps at 50 NDR stages FF and +26.9 ps on 1x450 at 20 stages FF. It comes from the bounding rise-late factor
(rise is over-read by up to 1.2 %), and it is on the pessimistic side.
The 37 rows still outside 2 % are the same 37 inverter rows as under spice_edge, which had 79 rows (42 BUF) (report_refit_buf_edge.txt).
Tests: tools/die_plan/test_clk_buf_edge.py (6) + test_model_corr.py golden incl. the new mode.

## 6. Routed path (MODEL-REFIT-BUF): HEAD hd_tile h16 spine, GRT SPEF
The deck is generated by `model_corr.py routed`. VDD ramps 0 -> V in 50 ps with `.tran ... uic`, so no DC operating point is solved, and the source edge is at 1000 ps.
`collect_case` drops crossings before 950 ps and fails if any node is still high at that time.
Cross-check (CHECKED): a DC-op run with `rshunt=1e10 method=gear` gave the same TT crossings on all 38 rows, within 0.1 ps.
In the golden there are 76 rows (19 taps x 2 edges x TT/FF). test_model_corr adds `test_routed_path_in_golden`.

The BUFx24 chain rows are unchanged.

Raw OpenSTA vs spice on this path (spice / STA): late TT 0.994-1.021 and FF 0.974-0.999; early TT 1.011-1.046 and FF 0.995-1.031.
OpenSTA NLDM reads the BUFx4 delay cells almost exactly. It is the BUFx24 under-read that the 12.15b factor corrects, and that factor does not carry over to BUFx4.

Model / spice at the path end, clkbuf_0_h16_t33/A (CHECKED):

| mode | TT rise late / early | TT fall late / early | FF rise late / early | FF fall late / early | duty err TT / FF |
|---|---|---|---|---|---|
| none | 0.996 / 0.979 | 1.005 / 0.989 | 1.015 / 0.997 | 1.021 / 1.004 | +4.3 / +2.7 ps |
| spice | 1.045 / **1.026** | 1.054 / **1.037** | 1.071 / **1.052** | 1.078 / **1.060** | +6.9 / +3.9 ps |
| spice_buf_edge | 1.045 / **1.030** | 1.028 / **1.012** | 1.071 / **1.056** | 1.047 / **1.034** | -6.5 / -7.2 ps |

Over the 19 taps, model early is above spice in every calibrated mode:
- spice: rise early 1.003-1.026 TT and 1.024-1.052 FF.
- spice_buf_edge: rise early 1.007-1.030 TT and 1.028-1.056 FF; fall early 0.978-1.012 TT and 0.999-1.035 FF.

**NEW finding, hold-optimistic.** The one BUFx24 factor is applied to every clock cell, so on a BUFx4 delay chain the model early is up to 5.6 % (FF, about 20 ps at 350 ps) later than spice.
The model late is 3-8 % above spice there, which is pessimistic for setup.
The fix is per-master (per-cell) factors, at least BUFx4, which is about 1.0 TT and 0.99 FF from this path. It needs a BUFx4 chain bench.
That is a separate MODEL-REFIT item. This branch does not change it: rule freeze, and the default stays spice.

## 7. MODEL-REFIT-2: per-master clock factors (opt-in `--clock-cal` / `--sta-clock-cal spice_cell`)
COORD 22:47 asked for this after section 6: the BUFx24 factor does not carry over to BUFx4 delay cells.

**Census of clock masters on the live die trees (10-28, CHECKED from netlists, read-only).**
- Die-level trees of all 5 dies are CKINVDCx16 only, with one exception: KV `clk_p20` / DIE-KV-21 `clk_c` also has 89 BUFx24 tap-pad cells (1-4 per tap on the 32 PHY taps `t_phy_*__clk`). The KV gate scales those with the inverter factor.
- The HEAD hd_tile h16 spine (16 BUFx4 delay cells per tap, 276 in total, plus 28 BUFx4 in the h15 early-tap chains) is inside the hd_tile partition. It reaches the HEAD die gate only as the scalar core latency and the `--ca-ring` file, both added after `apply_clock_cal`, so no clock-cal mode scales them (raw GRT OpenSTA).
- hd_tile `fclk_out_o` has BUFx12f / BUFx6f / BUFx10 / BUFx16f / BUFx2 resizer buffers. No die-level tree has BUFx4, BUFx6f, HB* or ICG cells.

**Benches** (`model_corr.py` CASES, ramp decks):

| case | form | rows |
|---|---|---|
| `bufx4_dly2_d32` | BUFx4 delay chain as built in h16 (abutted; the SPEF nets are 0.1-0.24 fF, so 2 um 1x wire), taps 4/16/32 | 12 |
| `bufx4_1x30_d20` | BUFx4 on 30 um 1x legs with fanout-2 side loads, taps 5/20 | 8 |
| `bufx6f_1x60_d20` | BUFx6f on 60 um 1x legs, taps 5/20 | 8 |

Bench setup:
- Spice cells: BUFx4 and BUFx6f come from asap7sc7p5t_28 `CDL/xAct3D_extracted/asap7sc7p5t_28_R.sp` @ e5bd25da72. The same transform as the CLK-INV-CAL lib reproduces all 17 lib subckts byte for byte.
- Deck: VDD ramps 0 -> V with uic. `.options abstol=1e-9 vntol=1e-5` is needed: with the defaults the BUFx4 transient aborts at FF ("timestep too small, vss#branch") and stalls at TT.
- Cross-check (CHECKED): BUFx6f with default options against these options agrees within 0.003 ps on every crossing.

Raw spice / OpenSTA (CHECKED):

| bench | TT late | TT early | FF late | FF early |
|---|---|---|---|---|
| BUFx4 abutted | 0.992-1.004 | 1.002-1.017 | 0.978-0.986 | 0.988-0.997 |
| BUFx4 loaded | 1.038-1.044 | 1.049-1.057 | 1.023-1.026 | 1.035-1.038 |
| BUFx6f | 1.021-1.024 | 1.042-1.047 | 1.004-1.010 | 1.025-1.030 |

For BUFx4, OpenSTA error depends on the load: about 4 % between the abutted and the loaded form.

**Model.** `SPICE_CLOCK_CAL_CELL` in die_sta_related holds one factor per master, corner, source edge and analysis.
- Fit (`model_corr.py fit`, a test asserts the table equals the fit):
  - late = MAX spice / STA-late, early = MIN spice / STA-early, over the single-master golden rows, rounded outward.
  - A routed multi-master row that is not yet bounded lowers or raises the factor of its binding master.
- Taps:
  - A tap with masters S takes late = max over S and early = min over S. This is a stage-wise bound: sum f_i d_i lies in [min f, max f] x sum d_i.
  - The masters come from the tap's `clock_masters`, else the proof's clock netlist (ctree.v, traced from the tap port to the root, `netlist_tap_masters`), else meta `clock_masters`, else the die clock cell's master.
  - A master without a factor fails closed.
- Routed golden rows now carry `masters` (the cells between the root and the tap).

| master | TT rise late / early | TT fall late / early | FF rise late / early | FF fall late / early |
|---|---|---|---|---|
| BUFx24 | 1.0473 / 1.0222 | 1.0227 / 1.0206 | 1.0552 / 1.0073 | 1.0257 / 1.0025 |
| BUFx4 | 1.0443 / 1.0164 | 1.0388 / 1.0018 | 1.0263 / 0.9972 | 1.0240 / 0.9877 |
| BUFx6f | 1.0243 / 1.0463 | 1.0218 / 1.0417 | 1.0101 / 1.0301 | 1.0056 / 1.0250 |
| CKINVDCx16 | 0.9483 / 1.0269 | 0.9528 / 1.0274 | 0.9611 / 1.0515 | 0.9623 / 1.0520 |

BUFx24 early is below spice_buf_edge (1.0524 / 1.0593 rise) because two routed h16 rows have only BUFx24 upstream (h16_n_D1/A, h16_t33_d0/A). Their spice / STA-early is 1.037 / 1.022 TT and 1.031 / 1.007 FF: the routed BUFx24 form sits under the chain bound.

CKINVDCx16 late is a bound too: 0.9483 / 0.9611 against spice_edge 0.9324 / 0.9380, because spice_edge leaves 46 of 60 inverter rows with late below spice (min 0.975).

**Golden (CHECKED, own spice).**
- 200 raw rows, 0 rows with model late < spice or model early > spice under spice_cell.
- none, spice, spice_edge and spice_buf_edge are byte-identical on all 1032 old keys.
- h16 path end clkbuf_0_h16_t33/A, model / spice:

| mode | TT rise late / early | TT fall late / early | FF rise late / early | FF fall late / early |
|---|---|---|---|---|
| spice_buf_edge | 1.045 / 1.030 | 1.028 / 1.012 | 1.071 / 1.056 | 1.047 / 1.034 |
| spice_cell | 1.043 / 0.995 | 1.044 / 0.991 | 1.071 / 0.994 | 1.047 / 0.992 |

On the h16 path, early is now hold-safe.

**Cost of one factor per master.** All 207 rows outside 2 % are on the safe side.
- Routed late reaches 1.078 FF (setup-pessimistic) and early 0.958 TT (hold-pessimistic).
- BUFx24 chain early is 0.938-0.974 FF.
- BUFx4 loaded early is 0.954-0.962.
- Duty error is -7.2..+27.1 ps.

**Tests:** test_clk_cell_cal (10).
- The table equals the fit.
- Every golden row is bounded.
- Mutant: BUFx24 factors applied to BUFx4 FAIL, early above spice on the BUFx4 / routed rows.
- Mutant: dropping the per-tap masters on the routed rows FAILS.
- The old modes are byte-identical.
- Netlist trace of the KV tap-pad form; an unknown master fails closed.

**UNCHECKED:**
- The effect on any die gate. Default stays spice / spice_edge.
- On KV, the 32 PHY taps would take the BUFx24 late factor on their whole ~4-7 ns arrival under spice_cell (+~10 % late), which is very pessimistic.
- A delay-weighted split (tree node arrival x inverter factor + pad segment x BUFx24 factor) needs the node -> net map; this is the next step if KV adopts spice_cell.
- The h16 / h15 BUFx4 arrivals enter the HEAD gate unscaled (core latency + ca-ring). On that path spice / raw-STA-early is 0.995-1.031 FF, so raw STA early is up to 0.5 % (~2 ps) later than spice (hold-optimistic).
- Full mode (`model_corr.py full`) needs `--lib` = the MODEL-REFIT-2 lib (intel1:/srv/opentallas-scratch2/claude/model-refit2-1028/lib, cells.sp md5 fb2de1d8..., which adds BUFx4 / BUFx6f and the other BUF / HB masters).
