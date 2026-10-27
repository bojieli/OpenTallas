# INFRA-FIRST-QC-R30 (2026-10-27 15:25-16:00 PDT): QC plan-event candidate on the clock basis + basis finding

## 1. Basis finding (needs a COORD ruling)
* COORD 12:48 ruled the event basis = main 68-type plan (H 26265.6). Every QC clock artefact (R24 guard51 die GRT 0/0,
  the R26 band export, the 8w remodel that passed max reach 448.524 <= 450, dry10..dry14) is on the native100 plan
  (codex/qc-bind-1027 58cc059cae candidate_guard51_native100_io.json, H 26317.44).
* CHECKED (own script, plan JSON compare): all 377 partitions match by name; 195 keep their origin, 182 (all north of the
  centre) move +51.84 um in y. The difference is the R16/R17 centre clock channel (die.channels clock_channel rect
  y 13132.8-13184.64, "die-level centre x-tree of the periodic QC top tree, no partition host") that never landed in
  main's die_plan.json. In addition, 24 of the 68 types are split into 2-4 island classes (the die_islands_um of each
  instance differ, so one type cannot carry them).
* So canonical68 has no host for the centre x-tree. The Codex canonical68 re-run (intel2 codex-qc-canonical68-1351,
  59b6db205c) confirms this: the master-plan gates FAIL (clock_entry, tree_on_islands, tree_commensurate, bay_fill, corridor_tracks, ...).
  A clock re-export on canonical68 means re-solving the top tree with no centre channel. That is a new design, not a relabel.
* Recommendation: ONE event = canonical68 + the approved centre clock channel + island class split (= the native100 geometry)
  + R3B + FT + M9 .672. The die STA gate uses declared 12.3 budgets until kits exist (12.4a), so the type split does not
  block STA. Per-class kits follow from the event.

## 2. Event candidate plan (this branch, results/qc_infra_r30/event_n100_ft_leg.json.gz, sha256 dc6f65ad...)
Input = the dry14 clock-basis plan (intel2 codex-qc-clock-r29-1351/c_dry14_band8w_m9672/plan.json, sha256 eaa09f27...):
native100 + R28 VSS clock-gap cut + PG M8 0.48@8.64 / M9 0.672@8.64 (COORD 15:24: .672 provisional).
* FT delta 2b588c310c (sha256 6bb0e5e2...), applied SLOT-WISE (compose_n100_ft.py). Only the slots the delta changes are
  replaced, and only when the class slot still equals the canonical 18c original. 7 types -> 16 classes; 27,858 changed
  bank cells. Disjoint from native100's own sle_su_l1 rsn/rsf site changes (delta touches x_st_a_fe only).
  0 outside / off-grid / macro / row-overlap errors.
* NEW: 51 changed cells overlap native100 clock die islands (coll_ftc crec_rx_s0 12 + tl_st_wi 1; sle/slw_su_c cws2 38).
  The FT packet was audited on canonical68, which has no islands. native100 ALREADY had 139 FT cells on its own islands
  (cbn_q01/_nb12d10 rsf 54, su_c cws1/cws2 56, cbf_q00_s2 serdes 9, sle_su_l1 rsn 12) -> 152 total after the delta.
* Fix (legalize_isl.py, deterministic, ledger event_n100_ft_leg_legalize.json): every island/macro-hitting FT cell moves to the nearest free
  legal site (y rows first, then +-2.16 / 4.32 um columns). 152 moved, 0 unplaceable, max displacement 3.78 um
  (58 at 0.81 um). After the fix (check_leg.py): island/macro hits 0, row overlaps 0; moved bits' max adjacent-bank hop 374.76 um (<= 405).
  Station counts, ports, lanes and cycles are unchanged. (own runs, UNCHECKED)
* G0C (check.run completeness, tools 18c, plan_dir = 18c qwen_compute incl. R3B + native100-only files such as cores/su_exact):
  event 0 E / 172 W; baseline dry14 plan 0 E / 172 W; finding sets identical (0 added, 0 removed). (own runs, CHECKED as runs)

## 3. Dry build status (clock basis, not run by R30)
dry14 (Codex unit 364213, .672 M9 + wide-PG guards, 8w band export, source cbe5946d11) ended exit 2: 1,796 plan errors,
all no_clock_track, on 1,756 nets (trend: 15,916 R28 -> 4,794 -> 4,523 -> 4,342 -> 1,796).
Classified by the failing edge's clock_spec net (layer/NDR, failing/total): M8 8w 1,431/9,431; M9 8w 178/1,742; M9 4w 124/18,262;
M8 16w 55/2,772; M9 16w 8/1,872; M8 4w 0/38. By element: trunk branches 750 (b:*), tap elbows 361+173 driver jogs, row L 288,
top-tree T 55+8, ~30 single M8 drops/jogs. 80 % = M8 8w trunks. These need the per-gap planner allotment (Codex
codex/qc-track-allotment-1027 ae347e0de/a14a3bce5 + index f57cc46b0: static replay of dry12 failures fit 374/376). No GRT/STA yet.

## 4. Adopted orphan: QC warm shared-chain canary unit499769 (epyc2) -- TERMINAL FAIL
epyc2 codex-flow-clkfreeze-qc-1351/vmr_codec_qualified: rc.txt route_finish_rc=2 at 14:56. DRT 5_2_route aborted with
"checkConnectivity break, net addr[52]" (Makefile error 245) after the HOLD_ECO (recipe ELEM-QK hold_eco b, margin 3 ps) on VMR f4k_final.
Flow-chain defect (warm ECO route), not a die-plan item -> FLOW-SHARED owner.
