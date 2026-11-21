# LOCKUP-STATION-R2 handoff (Opus, started 2026-11-20 19:40 PST; succeeds LOCKUP-STATION-1130)

Task: FABLE-CLOSURE-1930 lever 2 (hold by construction on stage chains, all dies): lockup latch only on cross-tap
zero-logic pairs, seam latch on output ports, prove on one S81 + one QC kit (hold ends + setup at CTS, before/after),
post rows to S81-J6-ASSEMBLY / QC-PLAN-R7 / KV-PLAN-R2 ONLY after a proof whose TNS is not worse than baseline (COORD 20:0x).

## State
- HOLD posted 20:0x to the three die lanes: no lockup rows until a passing proof.
- Cause of proof2 TNS CONFIRMED (epyc7 /srv/opentallas-scratch2/claude/lockup-station-r2/sta, cls.tcl/clsmin.tcl, *_max/_min.tsv):
  p2 4_cts TT setup violators: latch->capture 4,257 ends -227k (of -241k); u_fl_nl -> u_ft_ft*_o 3,674 ends -195k; seam u_fl_po -> ft*_o 394 ends -22k.
  By start-end distance: 250-400 um = 3,738 ends; < 200 um = 231 ends at -10..-80. Leaf mode puts the latch AT the launch flop, so
  the whole hop wire sits on the T/2 leg. Baseline hold on 300-350 um hops: 1,565 ends mean -25 ps (cheap); short hops are the deep ones.
- Code (lane clone intel1 /srv/opentallas-scratch2/claude/lockup-station-r2, commit f59ecc9a6f, NOT pushed yet -- push after proof4 CTS log shows bypass counts):
  clock.zl_lockup.<T>.auto/exclude/same_tap/max_um; zl_netlist "!re" excludes; clock_taps.tcl ct_hl_drop/ct_hl_bypass
  (OT_HOP_LATCH_SAME_TAP=bypass, OT_HOP_LATCH_MAX_UM, default 200 from gen); tests test_station_rule.py pass.
- proof4 S81 t39 (epyc7 .../lockup-station-r2/proof4_t39, launch.sh, run.log, GOAL=grt): proof2 kit (9 seam latches, leaf, lec fix)
  + auto netlist latches (proof3 synth inserted 28,649) + same-tap/far bypass 200 um. Read: CTS log "OT_CLOCK_TAPS hop latches:" bypass
  counts, tt_setup_keep.log, pregrt_ff_hold.log class before/after + hold_cells (base 14,251 xtap / 47,483 cells / TT -354.63 tns -16.4k).
  proof3_t39 = cancelled (no distance filter); delete via ot-delete when convenient.
- QC proof sle_ctl__cl67434795 (intel1 /srv/opentallas-scratch3/claude/lockup-station-r2/qc_sle_ctl, launch.sh, queued): inputs from
  ot-jobs/sle_ctl__cl67434795-route-key-cardinal-4137646-1795153811/work (post-refresh files) + leaf + auto + bypass 200.
  Baseline (same work dir pregrt_ff_hold.log): before cross_tap 3,039 / same_tap 199 / port_in 2; hold_cells 48,100; TT -1.82 / -1.82.
- Open: seam port latches cost -22k setup on t39 (u_fl_po -> ft*_o); if proof4 TNS still > baseline, drop seams on ports whose
  baseline setup slack < T/2 or keep seams off. KV: no kit proof yet (no CTS kit on D26/D27).

## Update (COORD after 22:xx)
- COORD accepted: proof4 leaf form is not proof1 (latches parked through tap solve + CTS, then on the launch flop leaf net).
- proof4 CTS: 28,649 netlist latches -> 6,281 bypassed same tap, 16,240 bypassed far (>200 um), 8,943 kept, all hung on launch leaf.
- scope bug fixed (ct_hl_drop took ct_hlmax via global; clock_taps is sourced in a proc) -> clone a8f34806c0 (amended, unpushed); proof4 resumed from cts (resume.json).
- Targets now: S81-J6-ASSEMBLY, QC-PLAN-R8 (was R7), KV-PLAN-R3 (was R2). KV: any lockup form goes to D28 after a proof (D27c dropped r5 rows).

## STAND-DOWN state (LOCKUP-STATION-R2, context ~340k) -- successor reads proof6 + QC2
Code (lane clone intel1 /srv/opentallas-scratch2/claude/lockup-station-r2, ot-push-main in flight at stand-down; see post for sha):
- a8f34806c0 auto form: clock.zl_lockup.<T>.{auto,exclude,same_tap,max_um}; zl_netlist "!re" excludes (reset relays, sram);
  clock_taps.tcl ct_hl_drop/ct_hl_bypass: latch removed when launch+all captures same tap or capture > OT_HOP_LATCH_MAX_UM (gen default 200).
- a9b2739489 dont_touch on netlist latches -> FAILED at synth (ODB-0369, proof5 dead) ; superseded by
- b28bcec799 (rebased 263c6566f6) ot_latch_restore: clock_taps (pre hop-latch passes) + hop_latch_leaf (every POST_CTS call) swap any
  u_fl_*/u_lk_nk_* DFFL* cell back to DLLx2 (resizer swapped 988 DLLx2 -> DFFLQx4 on t39 proof4 3_place; tested: 988 restored, 0 failed).
  NOT covered: swaps by later GRT-stage repair (LATCH-SWAP-0045 owns flow-wide scan / final check).
Proofs:
- proof4 t39 (epyc7 .../lockup-station-r2/proof4_t39) cross-tap<200 + leaf + 9 seams: hold before xtap 9,055/-217 (base 14,251/-275),
  same 24 (41), port_in 1,160 (1,167), port_out 6 (1,884); TT after keep -278.56 / -94.3k (base -354.63 / -16.4k) = FAIL.
  STA (sta/p4_max.tsv): seams u_fl_po->ft*_o 690 ends -57.7k; 988 swapped flops on 250-630 um hops. Bypass counts: 6,281 same, 16,240 far, 8,943 kept.
- proof5 = dead (dont_touch synth error).
- proof6 t39 RUNNING (epyc7 /srv/opentallas-scratch2/claude/lockup-station-r2/proof6_t39, launch.sh, run.log, GOAL=grt): pristine RTL
  (no seams) + auto + bypass 200 + leaf + latch restore. Read: 4_1_cts.log OT_LATCH_RESTORE / OT_CLOCK_TAPS bypass / OT_HOP_LATCH_LEAF;
  pregrt_ff_hold.log class before/after + hold_cells; tt_setup_keep.log; post-hook STA via sta/run_p4.sh pattern (cls.tcl on 4_cts_pre_tt.odb).
  S81 baseline (t39 b05c kit): pre-repair cross_tap 14,251 / port_out 1,884 / port_in 1,167 / same_tap 41; hold_cells 47,483; TT -354.63 / tns -16.4k.
- QC2 sle_ctl__cl67434795 QUEUED (intel1 /srv/opentallas-scratch3/claude/lockup-station-r2/qc_sle_ctl2, launch.sh, run.log): job-kit
  inputs + leaf + auto + bypass 200 + latch restore. Baseline (ot-jobs/sle_ctl__cl67434795-route-key-cardinal-4137646-1795153811/work):
  pre-repair cross_tap 3,039 / same_tap 199 / port_in 2; hold_cells 48,100; TT -1.82 / -1.82.
- Cleanup when convenient (ot-delete): proof3_t39, proof5_t39, qc_sle_ctl (cancelled), proof4 after read.
Rows: still HELD for S81-J6-ASSEMBLY, QC-PLAN-R8, KV-PLAN-R3 (KV -> D28) until a proof is no worse than baseline on TNS and hold.
Seams: drop from the form (cost -57.7k setup on t39); port_out hold then stays at baseline.
