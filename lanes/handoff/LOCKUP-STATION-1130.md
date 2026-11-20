# LOCKUP-STATION-1130 handoff (Opus, started 2026-11-20 ~11:20 PST)

Task: one die-agnostic station rule (count from hop length <=300 um, per-lane sites, first rank at pin, launch-side
lockup latch on cross-tap hops), tests, push main; prove on one heavy private kit through CTS (pre-route hold cells +
hold ends before/after); hand rows to S81-DIE-R4 (J6), QC-PLAN-R5 (V1), KV-PLAN-R1 (D27), HEAD-R14. Post every 2 h.

## Landed
- main 123dc80f79 (2 commits on 38cdd37cec): tools/die_plan/station_rule.py (rows / derive / apply), zl_pairs.tcl,
  kit_zl_lockup.py register form + unguarded mode + apply_kit, gen_phys.zl_lockup_spec + GEN hook, schema clock.zl_lockup,
  test_station_rule.py (12 tests incl iverilog lock-step + mutant). Lane clone intel1 /srv/opentallas-scratch2/claude/lockup-station-1130.

## Measurement (baseline, S81 leaf t39 D8i kit, epyc8 ot-jobs/ot_s81sl_leaf__t39-route-outgoing-giraffe-451430-1795159357)
- zl_pairs on 4_cts_pre_tt.odb: 29,864 zero-logic pairs, 23,153 cross-tap (ft 11,965; cst hig 4,395; ln hi 3,727; bout 669; lpad 595; ist 257 ...)
- pregrt_ff_hold.log: before cross_tap 14,281 (-275.27) / port_out 1,884 / port_in 1,167 / same_tap 41; hold_gate 17,372 ends;
  after: hold_cells 47,483, insts 344,021, 6,732 s, wns -33.54 (port_in 1,142 left).

## Proof (running)
- epyc7 /srv/opentallas-scratch2/claude/lockup-station-1130-meas/proof_t39: copy of kit-wave item gen
  (kw43-wave-1109n .../b05c98f7919/items/ot_s81sl_leaf__t39/gen), rtl = original + derived spec t39_spec180.json
  (min 180 pairs/class: 131 latches, 28,323 bits, 22,705/23,153 cross-tap pairs); original rtl kept in rtl.orig_kit.
- launch.sh -> ot-run unit oth-ubuntu-1017069-1795203655 (run_kit.sh GOAL=grt 48 GB 8 cpu). Log run.log; kit logs in gen/ot_s81sl_leaf__t39.
- Read: hold_gate.log (ends), pregrt_ff_hold.log class before/after + hold_cells; then stop the unit before GRT
  (ot-run --cancel lockup-station-1130-meas/proof_t39) unless GRT is wanted.

## Next
- Rows per die: station_rule.py rows on each live plan (ft slots) + derive specs from one CTS kit per heavy family (QC su_c, coll_core, HEAD hd_lep0N).
- Post results to the four die owners; post every 2 h.

## Update ~13:00 PST
- main cce380131d: module-scoped regs ({"reg","module"}), parameter widths, `ifdef headers skipped, unreadable modules recorded.
- Census: HEAD hd_lep0N (epyc10 civil-redfish-285021 4_cts): 44,659/54,536 pairs cross taps; pre-repair ends port_in 8,396 /
  cross_tap 7,227 / same_tap 291. derive maps 17,066; trial apply on a copy = 1,003 latches (epyc7 meas/lep_spec.json, lep_rtl_lk).
  Remaining unmapped = regs in generate blocks (scope skip) and ot_s81hd_lep_rxh_st internals.
- QC slw_fe_v2 (epyc8 outgoing-giraffe-478782): 41,091/64,562 pairs cross taps, 40,576 mapped (meas/fe2_spec.json), but its
  pre-repair census is port_in 3,558 only (window 57.8 ps): cross-tap pairs do not cost hold there. QC su_c/coll_core kits
  were cleaned; no CTS odb left to read.
- Die rows: epyc7 meas/plans/rows.sh (ot-run) -> rows_<die>.json for s81 D8i, KV D25e3, QC A4, HEAD r11b NF15f.
- Proof waiting: proof_t39 in global place at 12:4x.
