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

## Update ~13:05 PST (COORD lepe request done)
- Published (intel2): /srv/opentallas-scratch2/claude/lockup-station-1130-rows/ = rows_{s81,qwen_compute,qwen_kvsys,s81_head}.json,
  rows_s81_index.json (S81 J6 set), specs lepe/t39/lep/fe2. Working copies on epyc7 .../lockup-station-1130-meas/.
- lepe proof6/r2 census: 10,237 cross-tap pairs, lepe_spec.json latches 5,271 (14 latches trial). main 751c11e016 (no generic/reset-cell regs).
- Rows: needs_route flag for slots whose line crosses a core (main 814120525d).
- Open: t39 proof result (waiters bfwogbx13/be3vjvn5i die with this session; re-check proof_t39/gen/ot_s81sl_leaf__t39/pregrt_ff_hold.log);
  stop the unit (ot-run --cancel lockup-station-1130-meas/proof_t39) after the pregrt read unless GRT is wanted.

## Update ~14:10 PST (FABLE-CLOSURE-1315 items 1-5)
- (1) proof_t39 is NOT to be cancelled after pre-GRT: let GOAL=grt run through GRT it10 for congestion A/B
  (baseline hit the 20k marker cap at GRT it 5/10/15). Read gen/ot_s81sl_leaf__t39 pregrt_ff_hold.log, hold_gate.log, GRT log
  overflow/markers at it5/it10. It was in CTS at 13:30.
- (2) main 887cb2d06a: zl_netlist_lockup.tcl = post-synth DLL lockup (POST_SYNTH_TCL face_keep_release.tcl hook, plan
  clock.zl_lockup.<T>.netlist regexes, DFFH launch->capture through BUF/INV/HB only); kits with the list run LEC on 1_synth_odb.v.
  lec.py bb_free_out (latch fed by black-box output stub = wire) + test_lec_bbo_lockup.py; push in flight / landed after 887cb2d06a.
  Measured on proof t39 synth DB (epyc7 meas/nlt): 1,583 latches in ~51 s; LEC EQUIVALENT 81,040 points (gold 131 RTL latches + gate 1,583 netlist).
  The RTL-only proof kit would have been UNPROVEN without the lec fix (gold latch after u_l.lec_bbo_o).
- (3) SRAM-wrapper captures -> tap_group row (census.tap_group.re, one tap per wrapper), never latched.
- (4) Coverage on capture ends: t39 22,958/23,153; lepe 7,462/10,237 (+1,602 tap_group); hd_lep 40,335/44,659 (+3,854 tap_group);
  slw_fe_v2 40,936/41,091 but 0 cross-tap hold ends pre-repair -> no QC latch rows. Exact violating-end coverage:
  OT_PREGRT_OPEN_BEFORE=1 writes pregrt_ff_hold_open_before.tsv; station_rule derive --hold-ends.
- (5) lepe roq/rop excluded (--exclude). New-form specs: intel2 /srv/opentallas-scratch2/claude/lockup-station-1130-rows/*_spec_nl.json
  (spec = hops + netlist; plan key clock.zl_lockup.<T>).
