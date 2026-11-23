# FABLE-OPEN-HEAD-QC handoff (Fable 5.2, started 11-23 05:56 PST; brief scratchpad fable_open_brief.txt)
Items: rc138 (HEAD hd_lep0N E stripe, due 10:30, gate 11:00) and x5 (QC st_a DPL-0033, V4 gate 13:00).
Lane dir: epyc7 /srv/opentallas-scratch2/claude/FABLE-OPEN-HEAD-QC (clkwall_rows.py, plan/).

## rc138 (06:3x) cause + row drafted, post 851f9ea1 to HEAD-R18
- Cause: e1_split cong.rpt: 0.83k H overflow at x810-814 y605-632 on a 3.0 x 23.5 um die_clock_tree reserved rect; H cap 17-19 vs 26-28, usage 22-24.
  clksite_reserve merge_rects merges by least wasted area -> 3 cells 10 um apart in y = one tall rect = placement blockage + M1-M2 obstruction
  (M2 = first H layer). SPLIT-1 freed only M3-M7. r18z2 (plan 23e33a4497865202): same rect now x810.8 y654.5-678.0 + two more (x825.9, x838.9)
  in the H street between C3 rx (top 645.6) and rg0 tx (725.8). hd_lep0N: 34 tall rects, 491 um wall for 123 um of cell. W: 6 rects, 45 um.
- Row LEP-CLKWALL-1: clkwall_rows.py PLAN OUT --types hd_lep0N,hd_lep0N_w (each rect taller than 5 um -> one rect per cell window; no cell moves).
  plan/rows_LEP-CLKWALL-1.json sha 4713efaa5eb4; dry apply on r18z2 OK (256->302 E, 100->106 W; gen_phys.stack_rects valid).
- Shared cause with W spec 1123040001: no (W fail = macro row on pair face, pin faces, clock entry = HEAD-R18 LEP-WPLACE-1).
- NEXT: HEAD-R18 answer (apply on its re-fork before re-gate, ETA 09:30). Read ep3 GRT (intel1 ot-jobs/hd_lep0N-place-key-cardinal-569295-1795436170/work,
  GPL since 05:00) at window x800-850 y640-705: >=50 ov -> row is required; <50 -> row still offered, item REASONED by measurement.
  If neither gate nor ep3 by 10:30 -> REASONED packet to FABLE-RC-ALL (cause + dry apply + e1 measurement).

## x5 (06:4x) ROWS-READY posted 17e05a33 (QC-V4, PRECHECK-LEDGER-R3, FABLE-RC-ALL)
- Cause: kits select diamond legalizer, ORFS global_route.tcl erased DETAIL_PLACEMENT_ARGS -> negotiation legalizer in post-repair DPL, stops with
  53-443 overlaps of repair wire buffers at 23.7 % util. Not capacity, not plan.
- A/B epyc8 .../s29q103S4Q9N46R6V3/private/FAM-QC-SLWSLE-R1: slw_st_a_v2__cl9f076a5c_1122174003 (no fix) DPL-0033 (61); _1122174301 (main f60d28bf6dc)
  diamond 168,690/168,690, 0 failures, check_placement clean, 5_1_grt.odb written.
- Tree drift: c3n_bound/launch has the fix; c3n_bound/tree and W/launch copies do not; kits also get it via place-stage flow refresh.
- V2 reruns (FIX-QC-DPL-RERUN) were cancelled by the DESIGN-FAIL watchdog at GRT overflow; not to be rerun.
- NEXT: ledger status change to GATED (or FABLE-RC-ALL REASONED accept); QC-V4 confirms drift 0 on c4; check first V4 st_a kit GRT log for OT_GRT_DPL_ARGS.
