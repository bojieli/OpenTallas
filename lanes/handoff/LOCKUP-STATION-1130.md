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

## Update (FABLE-CLOSURE-1515, t39 regression) -- J6 rows NOT handed to S81-DIE-R4 yet
- Diagnosis (proof_t39, epyc7 meas/sta/proof_4_cts.odb.log): 26,592 latch pins hung on launch taps -> 10 taps over cap
  (clk_t41 6,122, clk_t6 15,062; baseline 3,295 / 7,040); CTS setup tns -400k vs -37k. Worst TT setup -471.15:
  u_fl_ist_leafup_o0_0/q[161] (DLATCH_N on clk_t41, opens ~970 ps down a 20-level tree) -> u_ist_leafup_o0_0/q[161].
- Tool fixes (commit 65585309b3, push in flight): OT_HOP_LATCH_LEAF (park latches pre-CTS, hop_latch_leaf.tcl hangs
  each on its launch flop's leaf post-CTS); station_rule derive --ends-only (exact violating cross-tap ends);
  kit_zl_lockup.apply_ports + station_rule seams (sender-side seam latch on buses abutted on every instance).
- Baseline pre-repair end list: epyc7 meas/sta/base_cts.odb.open_before.tsv (14,251 cross_tap; matches the kit log).
  Ends-only t39: 10,879 latched of 14,251 (rest not zero-logic). Seams: meas/plans/seams_{s81,qwen_kvsys,qwen_compute,s81_head}.json.
- proof2 (epyc7 meas/proof2, launch.sh, run.log): pristine kw_inputs-verified kit + 9 seam latches (3,808 bits) +
  10,879 netlist latches + OT_HOP_LATCH_LEAF + lec bb fix, GOAL=grt. Read: CTS log OT_CLOCK_TAPS/OT_HOP_LATCH_LEAF,
  OT_CTS_POST_TIMING, tt_setup_keep.log, pregrt_ff_hold.log class before/after + hold_cells, worst setup path, GRT it5/it10.
- proof_t39 (first proof) still in pregrt repair; read its after line for the record.
- Stop rule: no lockup spec on wave kits without re-solved taps (leaf mode); J6 only after proof2 wins.

## HANDOFF (context > 300k) -- state at FABLE-CLOSURE-1930 lever 2
Main has (ae58c0fd97): station_rule.py rows/derive(--ends-only/--hold-ends/--exclude)/seams/apply; zl_pairs.tcl;
kit_zl_lockup.py (RTL hops/regs + apply_ports seam latch); zl_netlist_lockup.tcl (post-synth, exact "=" names or regexes);
hop_latch_leaf.tcl + clock_taps.tcl/cts_post.tcl OT_HOP_LATCH_LEAF (latches parked pre-CTS, hung on launch leaf post-CTS);
gen_phys: clock.zl_lockup.<T> {hops, regs, netlist, ports, clk, leaf} hooks; lec.py bb_free_out. Lane clone intel1
/srv/opentallas-scratch2/claude/lockup-station-1130 (sparse adds done). Scratch tools: epyc7 .../lockup-station-1130-meas.
proof2 (epyc7 meas/proof2, unit via launch.sh, GOAL=grt) = pristine t39 + 9 seam latches + 10,835 ends-only netlist latches + leaf mode:
- taps: 14,629 latches parked, only baseline over-cap taps (t37/t41/t6) remain; hung on launch leaf (10,863 moved to launch flop).
- TT setup after keep: wns -294.11 tns -133.7k (baseline -354.63/-16.4k; proof1 -471.15/-320k). TNS cost = latch T/2 legs; READ meas/sta/p2_cts.odb.log worst paths.
- pre-repair hold: cross_tap 6,603 ws -335.53 (base 14,251/-275.27), port_out 5 (base 1,884), port_in 1,912 ws -44.69 (base 1,167/-33.54), same_tap 70 (41).
- still to read: pregrt after line + hold_cells (base 47,483), GRT it5/it10 markers (base 20k cap).
proof_t39 (first proof, latches on launch taps) still in pregrt repair (-31 ps at last look); read its after line for the record.
Baseline pre-repair end list: meas/sta/base_cts.odb.open_before.tsv. Seams rows: meas/plans/seams_<die>.json (also intel2 rows dir after next post).
Next (lever 2): generator applies rows by default from plan (ft_hop_lockup + zl_lockup ports) with leaf mode for every lockup type;
post rows to S81-J6-ASSEMBLY, QC-PLAN-R7, KV-PLAN-R2. Open problem: cross_tap ws worse (-335) and TT tns 8x: find the classes (likely
latch -> capture legs across far taps; consider latch at capture side for long hops = clock.ft_hop_lockup.tap capture / latch_frac).

## STAND-DOWN (COORD: LOCKUP-STATION-R2 owns lever 2)
- proof2 STA (epyc7 meas/sta/p2_cts.odb.log, 4_cts_pre_tt, placement RC): worst setup -489.52 is NOT a latch path:
  u_lpad_leafdn_i0.q[594] (clk_t2 leaf, 375 ps) -> ~1 ns repeater chain (14 BUFx16f wires) -> u_u_lf1_u_crr_rxsb/q on clk_t18
  (source latency -208 = tap window): a long-reach net present in the baseline (-424 pre-TT). Next groups -348.9 / -310.1 same launch.
  After TT keep: wns -294.11 (baseline -354.63) tns -133.7k (baseline -16.4k): the TNS gap is the open item (latch T/2 legs;
  get report_checks -group_path_count on the latch -> capture class from the TT-repaired 4_cts.odb).
- proof2 pregrt: before cross_tap 6,603 ws -335.53 / port_out 5 / port_in 1,912 -44.69 / same_tap 70; repair was at +5 ps
  at last look, after line + hold_cells + GRT it5/it10 not yet read (gen/ot_s81sl_leaf__t39/pregrt_ff_hold.log, run_grt.log).
- proof_t39 (proof1) pregrt still running (-31 ps at last look).
- Published (intel2 /srv/opentallas-scratch2/claude/lockup-station-1130-rows/): plan_lockup_<die>.json + receipt_lockup_<die>.json
  (station_rule apply rows + --seams) and seams_<die>.json for s81 (2,622 latch hops, 383 seam types / 2,134 buses),
  qwen_compute (85 / 133 / 1,644), qwen_kvsys (4 / 56 / 2,006), s81_head (192 / 26 / 86). Plans: D8i h2_2249, KV D25e3, QC A4, HEAD r11b.
- main 3e831b7084: apply --seams, OT_HOP_LATCH_LEAF also for clock.ft_hop_lockup types.
