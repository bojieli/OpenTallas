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
- Routed-SPEF path (brief item 1): **OPEN.** The extraction is done: `model_corr.py routed`, `dump_path.tcl`, and the HEAD hd_tile GRT SPEF path
  clk -> h16_n_RD -> h16_n_D1 -> 16 BUFx4 delay cells -> h16_t33_drv -> clkbuf_0_h16_t33/A, 20 taps, 19 nets, all side loads as real cells.
  Inputs are pinned on intel1 with sha256: 5_1_grt.odb ef1e07b7, grt.spef 42b0b7c6. The spice run fails because the xAct3D **BUFx4** cell
  (nc-vdroop-1027 lib) does not start its transient in ngspice r3 ("timestep too small" at the dummy-gate node x1.n_m0_g). This is reproduced on a 3-cell BUFx4 chain with KLU, SPARSE, gear and rshunt.
  BUFx24 and CKINVDCx16 run cleanly. A path with BUFx24/CKINVDCx16 only would need a different built tree (QC t10 has no SPEF; die trees are GRT-in-OpenROAD).

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
  `hd_tile/` (pinned routed inputs + path_{TT,FF}.txt), `ref/routed_hd_tile_h16_t33/` (deck that does not converge), `dbg/`.
- intel2:/srv/opentallas-scratch2/claude/model-corr-1-1028: golden build (`g_cal2.json`, `cal2/` = CAL-2 tools copy), and the reports.
