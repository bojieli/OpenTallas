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
TT pair g_prog[1].g_r.u_hi_wd/q[*] -> SRAM g_prog[1].u_hi: signed -85.16 (sign convention UNCHECKED: read as capture SRAM clock earlier than the write-data
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
-> PASS (clock frozen, geometry diff clean). 
ROUTED (unit oth-ubuntu-3964208-1793298688 exit 1 = signoff verdict, route rc 0, 11:31-11:46 PDT; CHECKED kit_ffh10/
signoff/signoff.json, copy `signoff.json` here): **NOT SIGNED, one FAIL left**:
- TT setup **+243.04** PASS | **FF hold -4.12 / 7 endpoints, TNS -13.53** FAIL (sdc frame -93.58 = raw IO, not the gate;
  FF vclk reference measured pin-flop mean 370.49, 1392 samples)
- related-pair skew TT/FF **78.41 / 70.86 PASS** (<=80; cand-2 85.16/75.72). Worst TT max-side pair still
  u_hi_wd/q[164] -> SRAM g_prog[1].u_hi, now 76.16 (signed -76.16); min side pcap[815] -> p_q[303] 78.41
- DRV slew TT/FF **0/0** PASS (cand-2 TT 3), cap 0, fanout PASS | DRC 0, antenna 0 (DRT 0 violations) | PG PASS |
  **timing_modes PASS** (cand-2 FAIL) | sdc_lint PASS, face_guard PASS, clock endpoint coverage PASS
- Worst hold path (signoff/ff/sta.log): u_twd0/q[446] (SE branch leaf, CLK 351.25) -> hold11186 BUFx2 -> _467_ INV ->
  g_prog[0].g_r.u_hi_wd/q[190] (Elo branch leaf, CLK 377.02): zero-logic-class reg->reg, launch 25.8 ps earlier than
  capture; arrival 409.68 vs required 413.79 (25 ps uncertainty + 12.10 lib hold).
- GRT->routed hold loss on this route: converge +6.32 (selected RC) -> routed -4.12 = **10.44 ps** (> the 10-ps margin).
  The ORFS GRT repair reached +10.01 on its RC, ot_final_ff_converge re-measured +6.32 on the kit RC file and passes at
  >= 0 (it does not re-impose the margin).

## 85.2-ps pair: now 78.41/70.86, inside the 80-ps gate
The routed pair is inside 80 ps after this route (no tree change); the early-tap balance item is therefore NOT needed for
the gate on this DB (information: 76.16 TT on the same u_hi_wd -> u_hi pair, 1.6 ps headroom on the min side 78.41).
