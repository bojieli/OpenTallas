# FABLE-FIX-S81-BKSEL handoff (dsdv_bksel_q) — 2026-11-17 00:55 PST

## State: SIGNED and exported
- Signed record: epyc2 `/srv/opentallas-scratch2/claude/fable-fix-bksel/fx6/hei_fable/eco3/i1` (signoff/signoff.json, generated 2026-11-16 22:26 PST).
  R-MINIMAL: DRC 0, antenna 0, routed TT setup -41.23 (4 endpoints, worst r1_d_l[369] latch -> c1_p[369]), FF hold +10.04 (0 violators, all paths).
  Clock geometry diff 0 (1718 nets, 30700 instances), PIN_AUDIT 1803/1803, slew advisory 41/38 (same as fx6).
- Archives (sha256 verified on both, SHA256SUMS in the dir): rtx-pro `/home/ubuntu/signed-export-1114/s81/dsdv_bksel_q/`,
  AGIdock `/archive/opentallas-signed-1114/s81/dsdv_bksel_q/`. 6_final.odb 424,214,146 B sha ac34039bf1b1...bb3993; signoff.json sha 3a374028043f...1bc2dc.
  Contents: 6_final.{odb,def,sdc,spef,v}, dsdv_bksel_q.lef, _tc.lib, _BC.lib, signoff.json, view/ (export_view.py, complete, pins sha 19651cb7...),
  eco/ (plans, inserted-cell lists, drivers, base and eco2 NOT SIGNED records, placement_eco.png, geom_review.json). INDEX.tsv row appended on both.
- LEC: source LEC of fx6 is EQUIVALENT (45318 points, kit lec_run.log, copied as eco/lec_source_fx6*). Routed LEC of the ECO netlist NOT run (advisory; ECO adds 215 buffers only).

## What it was (measured)
- fx6 routed: DRC 0, TT -41.23, FF hold -16.09 / 51. Census on 6_final.odb + SPEF (hei_fable/census): NOT reset removal
  (ot_rrs c6 -> sq835 is +12.17). 46 of 51 = hist-bank macro inputs of u_hf.g_bank[3] (i_dg/i_en, worst -5.8), 3 oq D, 2 t_o_f D
  (-16.09 = oq[183] -> t_o_f[183], leaf skew 64 ps). 212 internal pins under +10, 138 on u_hf.g_bank[3] (landing ~15 ps short).
- Fix = hold-ONLY route-keep ECO (run_hei_fable.sh): PRD pass from 5_2_route.odb with every other repair off (no pre-GRT
  repair_design, no hook repair_design / setup repair, no kit fx_repair), explicit plan via OT_PRD_HOLD_PLAN.
  eco2: 213 HB4 at 212 pins (140 macro inputs), displacement 0, 186 nets ripped, DRT 0 -> TT -41.23, FF -4.11 / 2.
  eco3 (from eco2): 2 HB4 at u_hf.g_bank[3] gsel[8]/[9] -> FF +10.04. SIGNED.

## Tool findings (for HOLD-FLOW-R)
1. hold_eco_internal planner skips macro input pins (capture_pin = D/RESETN/SETN/wd_in*); the inserter handles them. Here 46/51 failing endpoints were macro pins.
2. rt dd34c34ececf hold_eco_internal_insert.tcl refuses two-mode sessions ("HB4 source is not unique", cost eco, route_rc 2); the S81-TYPES-R copy (sha1 288be9c0) fixes it and is not on main.
3. Sibling sinks: padding 7 of 8 sinks of a net shortens the re-routed net, the unpadded sink lost 14 ps (+10.3 -> -4.1). Plan per net: pad every capture sink or none.
4. In-pass "OT_HOLD_MM after repair FF hold -45.25" after the insert is an estimate artefact; do not judge on it.
5. eco_loop/prd on this kit re-runs kit fx_repair after the hook (prd_post_grt_chain.tcl): Codex eco_hold_codex1116 added 128+147+772+458 buffers after rip selection. Not usable.

## Other forms
- fx6/eco_hold_codex1116 (E2 unit 4187300): not a hold-only ECO, never sign from it; S81-CORES-R may stop it.
- fx7 (E8 unit 3489035): physically finished, kit STA FF hold -10.96 / 72; superseded, may be stopped.
- fx8 (E8 unit 174106, native ETM CTS balance): at GRT. Optional structural successor (closes g_bank[3] hold by skew, removes the pad column); not needed for the count.
- COORD GEOM read on eco2: ISSUES (about 140 pads in the hf g_bank[2]/[3] channel). Advisory; numbers above. If a clock row event comes:
  early tap ~15-20 ps on u_hf.g_bank[3], 76 ps on u_hc.g_bank[0]. Channel widening would re-shape the core: not done.

## Next (nobody blocked)
- Die side: bind/STA can take the view at the archive path. Optional: routed LEC on eco3 6_final.v; adopt fx8 only if it signs with fewer pads.
