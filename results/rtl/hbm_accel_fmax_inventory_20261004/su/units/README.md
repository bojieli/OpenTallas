# 1.2 GHz binary32 add / multiply units (hbm-fmax-su, 2026-10-04)

New files only (default-off: nothing existing is swapped or edited; a source list opts in):
- `rtl/hdc/ot_hdc_fp32_f12.sv` -- `ot_hdc_fp32_add_f12 #(CUTS)` / `ot_hdc_fp32_mul_f12 #(CUTS)`: bit- and cycle-identical
  to `ot_hdc_fp32_add_fast` / `ot_hdc_fp32_mul_fast` at their LAT; only register boundaries move, plus timing-only
  rewrites (fraction-LZC normalise, precomputed encode exponents, keep-prefix increments, adder far flags and a
  magnitude compare split at the exponent field).  Fixed tops: `_add_f12_l4`, `_add_f12_l5x` (cut after decode +
  exponent differences: for a unit with an operand multiplexer in front), `_mul_f12_l5`, `_mul_f12_l6` (cut after
  decode + fraction LZC: operand multiplexer in front).
- `rtl/hdc/ot_hdc_fastfp_lat_f12.sv` -- FILE SWAP of `ot_hdc_fastfp_lat.sv` (same module names; a source list names
  one or the other): qmul LAT 5 -> mul_f12_l5, LAT 6 -> mul_f12_l6; keep-prefix qadd LAT 4 -> add_f12_l4, LAT 5 -> add_f12_l5x.
- `rtl/test/tb_su_fp32_f12.{sv,cpp}` (equivalence bench), `rtl/test/sim_hdc_fp32_f12_dpi_tops.sv` (DPI latency stand-ins).

**2026-10-05 alert resolved (l6_alert/finding.txt): mul_f12_l6 is exact (stress classes incl. signed zeros, exact
cancellation, wide exponents, subnormal results: 0 mismatches); the DS ROM su_hcpost ML=6 failure is that lane's
fixed-L5 y*post multiplier aligned as latency ML (lockstep: 195,546 mismatches -> 0 when it follows ML).**

Exactness (`fp32_f12_eq_v6_5M_x2.log`): 2 x 5,000,000 biased random pairs (specials, subnormals, cancellation,
rounding carries), every variant {valid, err, y} equal to the fast units delayed to its LAT: 0 mismatches.

Standalone routes at 0.833 ns (ASAP7, SS setup + 60 ps, FF hold + 25 ps, IO delay 20%, ADDER_MAP off;
`tools/w18/corner_sta.py` is the authority):

| unit | LAT | SS worst / r2r (ps) | FF hold (ps) | closes |
|---|---|---|---|---|
| ot_hdc_fp32_add_f12_l4  | 4 | +41.7 / +41.7 | +9.58 | yes |
| ot_hdc_fp32_add_f12_l5x | 5 | +12.99 / +12.99 | +4.93 | yes |
| ot_hdc_fp32_mul_f12_l5  | 5 | +47.3 / +47.3 | +8.87 | yes (mul RTL unchanged since this route) |
| ot_hdc_fp32_mul_f12_l6  | 6 | +41.4 / +41.4 | +8.38 | yes |

For comparison, the existing units at 0.833 with the same flow: mul_lat LAT5 -185.5 ps, LAT4 -187.4 ps (fail).

Context caveat: in the SU lane an operand multiplexer (control decode + 3-5-way select, ~250 ps routed) sits in
front of stage 1, so the lane uses the LAT-5 adder / LAT-6 multiplier.  The SU lane closure itself (light lane
best r2r -4.8 ps at MLAT 6 / ALAT 5) is still open; see the su family closure record when it lands.

Replay (EPYC, any route): `jobs/route.sh <label> ot_hdc_fp32_add_f12_l4 --source rtl/hdc/ot_hdc_fp32_f12.sv
--source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_prefix.sv` = tools/run_abi3_physical.py --view asap7
--clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC
--hold-corners WC,BC --io-delay-fraction 0.2 --stages pnr --core-utilization 35 --place-density 0.55
--hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30, then tools/w18/corner_sta.py.
Bench: verilator --cc --exe --top-module tb_su_fp32_f12 rtl/test/tb_su_fp32_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv
rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/test/tb_su_fp32_f12.cpp; ./Vtb_su_fp32_f12 5000000 <seed>.
