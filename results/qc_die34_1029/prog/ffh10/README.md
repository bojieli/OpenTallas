# DIE-QC-35 PROG QC-020 ffh10: ONE route, FF-frame hold repair on measured arrivals (COORD [DIE-QC-34-PARK] item 4)

Kit intel2 `/srv/opentallas-scratch2/claude/die-qc-34-kits/prog/kit_ffh10` = copy of the cand-2 kit `../kit` (results
only up to the prepped 4_cts.odb, sha256 108f1e50101bd397.. byte-identical to the cand-2 input, no re-prep; the cand-2
result in `../kit` is untouched). Tools from main 74030367304 (`tools/die_plan/kit_modes.py stage`, `final_ff_hold.tcl`,
`clk_freeze.tcl`, `clk_dump_db.tcl`, `clk_geom_diff.py`, `tools/orfs_hold_mm.{py,tcl}`, `vclk_measured_hold.tcl`).

## Changes vs cand-2 (no clock ECO, no PAD/trim, no skew target, no new check)
1. Binding repair (timing_modes FAIL of cand-2): config.mk `OT_VCLK_FF` 363.43 -> **381.14** (= sdc_lint insertion_ff_ps)
   and `OT_VCLK_TT` 471.92 -> **496.03** (= sdc_lint insertion_ps = constraint.sdc vclk latency; kit_modes stage refused
   the stale 471.92). Both were stale s8b values; constraint.sdc unchanged.
2. `kit_modes.py stage` (main): two-mode orfs_hold_mm session, scene tc = TT setup (vclk 496.03), scene BC = FF hold
   (vclk_ff.sdc 381.14), `OT_MM_MEASURED_HOLD=1` -> FF hold repaired on MEASURED pin-flop arrivals (12.19; reference
   rebind). The cand-2 GRT repair was one mode over tc+bc at the TT vclk.
3. Hold margin **10 ps** (COORD: no documented GRT->RC loss > 10): `HOLD_SLACK_MARGIN 10` (ORFS GRT repair) +
   `OT_HOLD_FF_MARGIN 10` (final step).
4. POST_GLOBAL_ROUTE `post_grt_ffh.tcl`: main `ot_final_ff_converge` (fixed-point TT setup guard / FF hold / slew+cap on
   the selected RC, clock frozen + clock-geometry diff, fails closed on no progress), then the cand-2 PG bind + 0-open check.
5. TT slew (cand-2: 3 routed violators place5204/A 338.70, place5200/A 331.34, _4070_/A 324.04 vs 320): `SLEW_MARGIN 40`
   (the QC generator post-GRT DRV value, gen_core_kit_qc post_grt_drv.tcl, "routed max-slew residue needs 40 %").

Launch (intel2 client log `~/dqc35k/prog_ffh10.otrun.log`):
`ot-run --mem 32 --threads 16 --dir KIT -- bash KIT/run_ffh10.sh KIT 16 32`; unit **oth-ubuntu-3964208-1793298688**
(started 11:31 PDT). Try 1 (oth-ubuntu-3944082) exit 9 before any stage: shell quoting of `--session "tc bc"`, fixed.

## 85.2-ps related pair (not addressed by this route)
TT pair g_prog[1].g_r.u_hi_wd/q[*] -> SRAM g_prog[1].u_hi: signed -85.16 (capture SRAM clock EARLIER than the write-data
launch flops by 85 ps; 12 pairs 85.16-85.58 raw), CRPR 0.42 (CHECKED cand-2 signoff/tt/pair_skew.tsv). The kit tree was
built with `OT_MSCTS_MACRO_EARLY = 20` (s7 "read-safe 20 ps earlier SRAM clock target"); the SRAM liberty carries no
internal insertion attribute, only clk-related setup/hold/clk->q arcs. Balancing the u_hi tap against its write-data
launch group is a tree (CTS) change from the placed DB, so it cannot be applied inside this GRT-from-4_cts route.
Next step after this route: macro tap insertion-delay balance for g_prog[*].u_hi in the CTS plan (target from the SRAM
own view arcs + measured wd-group arrival), one CTS+route.

## Results
GRT stage (CHECKED kit_ffh10/run_route.log, GRT RC): measured FF vclk bind 369.88 (1392 pin-flop samples; bound 381.14,
tol 40); two-mode before repair TT setup +265.29 / FF hold -2.10; ORFS repair at margin 10 inserted **51** hold buffers
(cand-2 single-mode repair: 2,930) -> FF hold +10.01; ot_final_ff_converge pass 0: TT +265.29 / FF +6.32 / slew 0 / cap 0
-> PASS (clock frozen, geometry diff clean). DRT + routed signoff: see below.
