# DIE-QC-34 PROG QC-020 candidate 2: PG hook + ONE route (GEOM-58 PASS-COND 2026-10-29 09:37)

Input: intel2 `/srv/opentallas-scratch2/claude/codex-qc-prog-native-0858/native_pin_reach.odb` sha256 6a2f8b4994ba...
(CHECKED; = archived s8b 5_2_route.odb 9fe17a8c with 354 FFs moved, max 98.77 um). Native outline 259.2 x 354.24,
S clock entry (35.292, 0.042). Kit: intel2 `/srv/opentallas-scratch2/claude/die-qc-34-kits/prog/kit` = the Codex
PG-repair kit copy (`codex-qc-prog-pg-0830/kit`, config.mk of `kq_qfd_dv_s8x_prog_pd40a0`) + the files in this dir.
The original s8b kit hooks (post_grt_s5.tcl, mscts_*.tcl, drv.tcl, io/pdn) are gone (kit dir deleted), so the route
uses plain ORFS GRT/DRT stages from a prepared 4_cts.odb; `cf/rc_cal.tcl` (OT_RC_CAL 0.8,0.9, same as the kit) copied from
the same-family epyc2 `codex-qc-cores-0815/prog_l2h3_route2/cf/rc_cal.tcl` (md5 288424b1).

## Steps (`run_prog_route.sh`, ONE ot-run unit)
1. `prep_prog.tcl`: existing protected-instance PG hook (`pg_connect.tcl`, byte-identical to main
   tools/die_plan/pg_connect.tcl except the header line): `ot_pg_connect_all` -> 108 protected ot_ms_* spine buffers
   rebound (as Codex 08:30), `ot_pg_require_bound` 0 open of 59,604 PG terms (CHECKED prep.log). The 5_2-stage open
   census is 23,962 (not the 6_final 216: ORFS binds post-DRT cells only at 5_3 global_connect; the same hook binds all).
   Then ALL old non-special routing removed (23,932 nets, 333 CLOCK-typed) so the moved FFs and their leaves are
   re-routed; cells/placement/PG metal unchanged. 29,802 insts, 4,278 DFF.
2. ORFS `do-grt`: PRE hook `pre_grt_leaf.tcl` = normal leaf repair (`repair_clock_nets`, DPL, PG bind + 0-open check);
   `GLOBAL_ROUTE_ARGS = -congestion_iterations 50`; ORFS global_route errors on any remaining overflow (= stop, no DRT);
   ORFS incremental repair_design/repair_timing on GRT RC (SKIP_INCREMENTAL_REPAIR=0); POST hook `post_grt_pg.tcl`
   = PG bind + 0-open check.
3. `do-5_2_route ... do-6_report do-generate_abstract` (no GDS merge: SRAM GDS absent), then main
   `tools/die_plan/signoff.py run --corners tt,ff` (main copies of signoff.py + helpers in the kit).
No clock ECO, no trims/pads, no skew targets.

## Results so far
(2026-10-29 10:47 PDT; CHECKED from kit/prep.log + kit/run_route.log)

- Unit `oth-ubuntu-1922493-1793294835` (intel2 = ot-run localhost; client intel2 `~/dqc34k/prog_route.otrun.log`), started 10:27.
- PG hook: 108 protected rebound, 0 open / 59,604 PG terms (prep); 0 open / 59,604 after leaf repair; 0 open / 65,464
  after the GRT-stage repair (post_grt).
- Leaf repair: `repair_clock_nets` (max wire 218 um) inserted 0 cells (worst moved-sink leaf ~100 um < 218).
  Placement-estimate clock skew 149.85 ps (report_clock_skew, raw, INFO only; the gate is the routed related-pair skew).
- **GRT PASS condition 1: 0 overflow** on every layer (M2 12.86 %, M3 17.63 %, M4 4.69 %, M5 9.14 % usage; Max H/V/Total
  0/0/0), 23,932 nets, WL 518,526 um, converged at extra iteration 4 of the configured 50 (FastRoute stops when overflow
  reaches 0); the W column is inside "Total 0". No congestion*.rpt written at all (incl. the post-repair incremental
  GRT after the hold buffers), i.e. 0 congested gcells. 
- GRT-stage repair (ORFS default, MCMM tc+bc): 2,930 hold buffers (repair_timing 716 s), then post-GRT setup +263.97 ps,
  hold +4.07 ps (MCMM worst), slew 0 (GRT RC, UNCHECKED vs routed).
- DRT: 0 violations (6th stubborn-tiles iteration); route + fill + report + abstract rc 0, 10:27 -> 10:54 PDT.
- **ROUTED SIGNOFF (main signoff.py, `kit/signoff/signoff.json`, CHECKED): NOT SIGNED.**
  TT setup +232.12 | FF hold -7.09 ps / 11 endpoints, TNS -35.6 (sdc -20.94; vclk pin-flop mean 371.38) |
  related-pair skew TT/FF 85.16/75.72 (limit 80; worst launch g_prog[1].g_r.u_hi_wd/q[164] -> capture SRAM g_prog[1].u_hi,
  CRPR 0.42; TT hold pair 85.5 pcap[815] -> p_q[303]; p99 raw 79.33 TT) | spread info 62.11/61.56 | DRC 0, antenna 0 |
  DRV TT slew 3, cap 0 | sdc_lint PASS, face_guard PASS | timing_modes FAIL = kit binding mismatch config.mk
  OT_VCLK_FF 363.43 vs sdc_lint insertion_ff_ps 381.14 (pre-existing in the copied s8b kit).
- Reading: the geometry fix holds (GRT 0, DRT 0, setup +232). Remaining FAILs: (a) FF hold -7.09/11 - the GRT-stage
  repair here is the ORFS MCMM default at margin 5 (the lost s8b kit had an FF-frame hold step); (b) TT pair 85.2 is a
  write-data FF -> SRAM capture pair (macro insertion class), 5.2 ps over; (c) slew 3; (d) the vclk binding mismatch.

Collected 10:59 (above). Original collect list: `kit/run_route.log` (DRT per-iteration violation count; final `5_2_route.json` DRC), `kit/signoff.log` +
`kit/signoff/signoff.json` (TT setup, FF hold, related-pair skew TT/FF = the routed clock check for the 354 moved
sinks, DRV, DRC). If signoff.py errors on a missing kit helper, rerun it with the command at the end of
`run_prog_route.sh`. Gate: routed gates decide (GEOM-58 cond. 3); then routed LEC + PG census on 6_final.


## Next step (DEFAULT, one route)
Same prepped 4_cts.odb, GRT stage with the kit's FF-frame hold repair (OT_VCLK_FF rebound to the measured 381.14 so
timing_modes binds, hold margin 15 on FF only, as the FLOW FF-only form), plus the FLOW repair_design for the 3 TT slew
nets; the 85.2-ps write-data -> SRAM pair goes to the macro early-tap balance (12.3 v5.0) owner, not a clock ECO.
