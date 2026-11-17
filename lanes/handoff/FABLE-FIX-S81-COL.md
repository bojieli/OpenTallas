# FABLE-FIX-S81-COL handoff (restarted 2026-11-16 21:15 PST as lever 1 of FABLE-CLOSURE-STRATEGY 21:40)

Owns closure of the S81 col family (216 plan types: h9_r1 60, h9_r2 60, h10_r2 12 = col-wave1; h9_r0_p1..p6, h10_r0_p1/p4, h10_r1 = col-wave2).
Gates: DRC 0, routed TT >= -42, internal FF hold >= 0. Directs S81-TYPES-R2 (kits, tree) and FIX-S81-COL-STALE (holds, wave release).

## Where things are
- epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-col/: an/ (cong.py congestion.rpt binning, ist_rows.py station-row rewrite),
  pg1/ (h9_r2 PG-cap route proof), ir1/ (h9_r1 station-row proof). Each has its own run_kit.sh copy + flow_tag.
- intel2 ~/fable-fix-s81-col/: ot-run client logs pg1_h9_r2_route.log, ir1_h9_r1_route.log.
- Source kits (S81-TYPES-R2, do not touch): epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s4tapfix1/{gen,gen_rm3}.
- How a private restart is made: rsync the kit without the stages to redo, restore signoff.py / signoff_profile.py, `touch -r` config.mk
  to the source kit's mtime (RESYNTH-GUARD), `ot-run --mem 64 --threads 16 --dir W --hosts epyc8 -- bash W/run_kit.sh W/<kit> route 64 16`.

## Root causes (21:2x, MEASURED)
1. col_h10_r2 gen/: sign-off STA ran; TT setup -172.57 / 102 endpoints (u_t7/so[1:0] -> ist_frame_int_o0_0 q[383:382], site class),
   internal FF hold -4.83 / 10 (reset removal), DRC 0. The session then died in pair-skew (psambig, old pair_skew.tcl). Not signable.
   rm3 (per-bit sites for q[382:383]) is the h10_r2 candidate: in detail route since 21:26 (client of S81-TYPES-R2).
2. col_h9_r2 DRT-0255: class A (FABLE-PD-DRT-1350). Net clknet_leaf_70_clk_t18_regs, box (326.04,130.53)-(330.03,134.52), end at
   (330.030,132.192) on M6 = first track above the M6 PG pair (VSS 131.424-131.712, VDD 131.808-132.096). Die-phase PG was present
   (M7 offset 8.448). The private gen/ kits had no OT_PGCAP (C3b capacity cut); wave die_gen_env has OT_PGCAP=1.
   Proof pg1 = same kit from 4_cts + pg_pair_cap hook only (GRT log: OT_PGCAP region adjustments M7 331 M5 664 M6 564).
3. col_h9_r1 GRT-0116: 898 overflowing gcells, all in x 600-800, y 1200-1227 (north strip, 61 um between the e8 macro row and the edge).
   istations.tcl packs each 1,167-flop frame_int_o0 rank at one point (1069 / 757 / 445, y 1226.88) = a 147 x 9 um triangle with
   bits in arbitrary order; lpad_frame_int_i0 (321 b) ranks at 639 / 983 share the strip. CTS timing fine (worst -20.1).
   Proof ir1 = ordered rows: 117 ten-bit groups per rank over x +-90 um, same y, same rank centres (ist_rows.py), + OT_PGCAP.

## Decision table
- pg1 routes DRC 0 -> OT_PGCAP is the h9_r2 fix; the D4/D5 wave kit already has it. Sign-off pg1 (TT / FF) and, if it passes, export.
- ir1 GRT 0 overflow -> station-row form goes into kit_istations.py as the default for a rank wider than 256 bits on an N/S face
  (S81-TYPES-R2 implements; plan rows unchanged, no cycles). If ir1 still overflows: read congestion.rpt with an/cong.py; next form =
  lpad_i0 ranks moved 20 um inward and o0 rows +-140 um.
- col-wave1 PASS is posted by S81-TYPES-R2 only after a wave pilot (D4/D5 kit) signs; FIX-S81-COL-STALE then releases in waves
  (h10_r2 12 first, then h9_r2 60, then h9_r1 60 after the row form is in the tree).
- col-wave2 (76 types): relay depth in the col RTL generator for the 10 non-row groups + C4 rows (strategy lever 1 items 5-6).

## Export
AGIdock /archive/opentallas-signed-1114/s81/<type> and rtx-pro /home/ubuntu/signed-export-1114/s81/<type>, INDEX.tsv row under flock.

---
# History (previous run, 11-15 23:00 to 11-16 01:4x)
# FABLE-FIX-S81-COL handoff

Owner of S81 col closure (216 types), pilot col_h9_r2__t1__clce45cab5__pv7a260fc0. Gates: DRC 0, TT setup >= -42, FF non-port hold >= 0, bind + LATCHECK.

## Where things are
- epyc7 /srv/opentallas-scratch3/claude/fable-fix-s81-col/an: analysis scripts (mk.sh census, srv.sh STA session, cts_sta.sh CTS-stage STA, cls.py / prs.py classifiers) and outputs (pv7a260fc0b = routed pilot census; cts_old, cts_x1.. = CTS-stage reads).
- epyc7 .../fable-fix-s81-col/x1, x2, x3: private copies of the routed pilot kit up to 3_place, CTS re-run only (x1_prep.sh, x2.sh). Nothing in a wave kit was touched.
- epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-col/wt: clone, branch claude/fable-fix-s81-col-1116 (commit 2db85d029e = seam-write trace fix + 2 tests; not pushed, not gated yet).
- Review: lanes/FABLE-PD-S81-F2r.md (posted 23:00 11-15).

## Findings (routed pilot, TT, 1,387 failing endpoints, all classed)
1. Edge chain n23 -> bout_frame_int_o0: 66, -267. F2r stations close it.
2. Half-cycle reset relays u_rrl: 25, -240 (-319 on a sibling). Fix: type key reset_relay_full (exists in gen_phys).
3. ROM rd_out -> cfg7_seq q*: about 830, -169. ROM clk pin 270-370 ps after the s pin. Fix: ROM pin lead 255 ps (core_latency row), address side has +348.
4. lpl_*_r -> t6_payload: 380, -242. Cause: glue tap trees 247..876 vs target 450. Cause of the depth: OT_TAP_GROUP_RE (lpad group on one tap), tap pair affinity and the 1,500 cap pass hang sinks on far taps. With plain nearest-tap every register is <= 247 um from its tap.
5. Reset copies u_d7_6_Y: 74, -151.
6. go_tag IFN half cycle: 4, -120. IFN = 0 halves (S81-GOTAG-SETUP) have no live build.

## Proof so far (CTS stage, placement RC, signal cap x1.45, same method on both)
- baseline kit: WNS -380.6, 1,476 endpoints. X1 (no OT_TAP_GROUP_RE, no OT_TAP_PAIR_AFFINITY, cap 3000, ROM lead 255): WNS -217.0, 138 endpoints; tap means 387..518 (was 247..744). The 138 = edge chain 67, reset relays about 40, reset copies 18, go_tag 8, element -> s ef 5.
- Open in X1: tap-root padding also delays the cores on that tap (s pin 248 instead of 179; ROM pins 225-385 instead of 195). X2 / X3 test OT_TAP_CORE_ETAP=1.

## Next
1. Read X2 / X3. Pick the core form.
2. When the F2r bind passes: generate the r2 kit from run/b/B6gF2r (bind.py kit-rtl + gen.py phys, wave die_gen_env + item env) into epyc10 fable-fix-s81-col/f2s, apply: reset_relay_full, config.mk tap keys, ROM lead, signal RC x1.45 for repair. Run run_kit.sh to route via ot-run, read at sign-off.
3. Turn the kit edits into plan rows / tool changes on the branch (clock.core_pin_lead_ps, tap keys per col type, reset_relay_full rows), gate with /srv/opentallas-scratch2/claude/mq-gate/ot-gate-remote, post READY, rows to DIE-S81-92.
4. Reset copies (class 5) and go_tag (class 6) need their own fix; read them first on the F2r kit.

## 00:30 11-16 update
- X3 result (CTS, same method): setup 1,476 -> 144 endpoints (WNS -380.6 -> -199.8), FF hold non-port 1,712 -> 108 (WNS -137.8 -> -70.6), tap means 387..481. Posted 23:5x.
- F2r bind 0 / LATCHECK 873/873. Seam-write fix is DIE-S81-92 branch claude/s81-relay-seamw-1115 (r248); my commit 2db85d029e is a duplicate, do not READY it.
- PILOT RUNNING: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-col/f2s2/gen/col_h9_r2__t1__clce45cab5__pv7a260fc0, run_kit.sh route 64 GB 16 cpus via ot-run (client log: localhost scratchpad f2s2_route.log; kit log run_route.log). Built by f2s_gen.sh from plan ev/B6gF2r.json + tree run/b/B6gF2r/src (NOT main-based: no OT_TT_SETUP_REPAIR, no die phase; r249 asks for a main tree, none existed at 00:00). Post-gen kit edits: no OT_TAP_GROUP_RE / OT_TAP_PAIR_AFFINITY, OT_TAP_MAX_SINKS 3000, OT_TAP_CORE_ETAP 1 SRC tree, ROM clk lead 255 in core_latency.txt, reset_relay_full applied to rtl/bind_cells.sv.
- A plan edit of the type (f2s_plan.py) fails kit_topology with KIT_TOPOLOGY_BIND_STALE: type keys must come as a plan event from DIE-S81-92, not a private plan copy.
- Read at: 4_1_cts.log OT_TAP_BALANCE done line; then sign-off (signoff/signoff.json). Use an/mk.sh + cls.py for the census.
- If it misses: go_tag (IFN half cycle; IFN0 halves hwC/heC stopped at OT_HOLD_STRUCTURAL FF -152/-164 on 2,7xx inputs, no owner), reset copies u_d7_6_Y, element sh_free -> s ef nets (need TT repair = main tree).
- To do for the family: plan rows (reset_relay_full true, drop clock.tap_group + tap_pair_affinity, tap_max_sinks 3000) to DIE-S81-92; tool change on a NEW branch from main: type key for ROM clock lead (core_latency row) and OT_TAP_CORE_ETAP export.

## 00:5x 11-16: specs for S81-COL-CLK-IMPL
- lanes/FABLE-FIX-S81-COL-SPECS.md: Spec 0 exact kit diffs + keys of the four-part clock form; Spec 1 reset copies (two-level copy tree); Spec 2 go_tag; Spec 3 IFN=0 halves (shallow face-flop clock + stop removed).
- f2s2 pilot (F2r tree) is timing evidence only (core-phase PG, may stop at DRT-0255). The pilot that counts = main-based S81 tree + IMPL branch.

## 01:2x 11-16: F2r pilot read at CTS; flat tap window is the next blocker
- f2s2 (F2r plan + four-part form) 4_1_cts: tap means 348..478, 5 of 79 core pins outside +/-20, no empty tap; clk_t1 and clk_t2 at the 3000 cap.
- Same CTS read (an/cts_sta.sh, an/ffh.sh on epyc10 fable-fix-s81-col/an; SDC dirs ks = kit SDC, ks0 = kit SDC without the -early/-late lines):
  - kit SDC (F2a/F2r: flat 165 ps window on all 26 grid ports and on the core taps): TT setup 6,543 endpoints WNS -340.6; FF hold 6,261.
  - window 0: TT setup 26 endpoints WNS -175.6 (go_tag 4, element sh_free/bank_free -> s ef 4 at -119, reset copies 3 at -59, rest >= -8.5); FF hold 518 at -121.5 (pre-repair).
  - edge chain and reset relays: 0 endpoints in both. ROM read -3..-5 at window 0: consider lead 300 (address side had +348 at lead 0).
- So col needs measured per-port window rows on the new tap trees (S81-TAPROWS method) or the offsets form back; with 165 flat no layout passes. Posted 01:2x.
- The wave kit attempt_2 of pv7a260fc0 on epyc7 (routed baseline) was cleaned up; my census outputs in epyc7 scratch3 fable-fix-s81-col/an remain; STA preambles copied to epyc10 fable-fix-s81-col/ks.
- f2s2 keeps routing (client log localhost scratchpad f2s2_route.log; kit run_route.log). Its repair runs against the 165 window: read DRC and the station hops from it, not WNS.

## 01:4x 11-16: tasks from COORD (r268)
1. Review S81-COL-CLK-IMPL per-port window rows when posted, against: window 0 -> 26 setup endpoints, 165 flat -> 6,543; estimate pass below about 40 ps.
2. F2s structural review (r199 style, lanes/FABLE-PD-S81-F2s.md) in parallel with its bind. Check also: ring_place ff on S81 bands >= 256 bits (lever 1) reaches the col wide rings (lpad_frame_int_i0 1,168 bits x 4 ranks, bin/bout frame_int 1,168 / 322, lpl_*_r/w).
3. Countable pilot: r2 from the S81 tree REBUILT AFTER claude/s81-col-clk-1116 merges (NOT kw45/src_s81_pin_e594a73db756: no clock.core_pin_lead_ps), plan F2s, clock form from plan keys (no post-gen kit edits), die-phase PDN + TT repair present (check pdn.tcl offset 8.448 and tt_setup_repair in the kit), run_kit.sh route via ot-run, sign-off, export. Gen recipe = epyc10 fable-fix-s81-col/f2s_gen.sh with SRC/B/PLAN switched and the post-gen block removed.
- Hub watcher (localhost background task) fires on IMPL / DIE-S81-92 COMPOSED / TOOLS-CONVERGE S81 posts; re-arm after a restart.

## CODEX handback — owner hand-back order 2026-11-17 05:03 PST
PARKED immediately; no new physical/source launch after the order. Preserve running jobs.

- **PG3 h9r2 base FAIL**, E8 `fable-fix-s81-col/pg3/col_h9_r2__t1__clce45cab5__pv7a260fc0/signoff/signoff.json`: DRC2/ANT0, routed TT -39.25 (inside floor), internalFF57 at -7.61 (52 D,5 RESET), allFF -13.66 includes107 input-port paths. Two M5 shorts are unrelated net155735 down-vias INSIDE t6, exact boxes in failure_probe1117/drc_net_geometry.json. Earlier preliminary route-clean inference was wrong; final report is authoritative.
- **ONE actual data correction LIVE** E8 unit `oth-ubuntu-3114257-1794919204`, intel2 client709739, log `~/fable-fix-s81-col/pg3_hold_m5_mm2_1117_r2.log`; sibling E8 `fable-fix-s81-col/pg3_hold_m5_mm2_1117`, driver `run_pg3_hold1117_mm2.sh`. Actual78 HB4 inserted at57 failing+21 same-net sibling captures, min measured TT room689.89 vs132.8 max HB4 price. Temporary pin-free t6 M5 interior obstruction plus exact net155735 forced rip;0 cycles; no globalDRV/setup repair. Routed-SPEF basis, clock freeze preserved2024 wired nets and137662 kept data wires; last stage DRT iteration0. Review image/record in sibling results/geom_review,0 signal-pin intersections. NEXT final DRC/TT/internalFF and clock geometry; sign/export only on PASS. No col-wave PASS.
- Initial stage failed missing SDK clock_family; first physical attempt failed KIT_MODES because single-mode over2corners; next attempt failed missing MM runtime before repair. All failed directories/records retained. Current MM2 carries complete exact7fe681 SDK, actual MM runtime+config, and is the only actual78cell ECO. No source/base kit mutation. Own9 byte-identical obsolete seed/SPEF copies retired after SHA/inode/nlink/mount checks,6,031,413,909 B freed; retained source PG3 originals and all unique objects/logs/failures. Receipt `fable-fix-s81-col/own_failedstage_duplicate_retirement1117.json`.
- **ir1 h9r1 LIVE**, E8 unit4035869-1794905163/container2d8ed421844b, `fable-fix-s81-col/ir1/col_h9_r1__t1__cl49d7a23e__pv047ea3b3`; log intel2 `~/fable-fix-s81-col/ir1_h9_r1_route.log`. Last DRT iteration10 about3587. Iter5 markers4273:2305 atx1100-1150/y580-600,1103 aty160-180,585 aty560-580. Internal hot spots, not north strip. IMPORTANT this evidence kit still OLD `[.]u_y_` regex, so it is not the correct current vehicle; only19groups/2519relayFF. Current[._] form must be measured before rejecting the family. POLY also warns lpl6..9 hops652..729um; fallback0 alone does not gate these POLY warnings.
- **ir2 minimum geometry preview PREPARED ONLY**, NOT launched/placed/routed: archive394,181,787 B at E8 `fable-fix-s81-col/ir2_preview1117.tar.gz`, copied to E9 `/srv/opentallas-scratch2/claude/ir2_preview1117.tar.gz`; current relay_mid helper copied E9 `/srv/opentallas-scratch2/claude/ir2_current_relay_mid.tcl`. Archive has unchanged RTL/macros and completed stages through3_2 only. RootS81 authorized newregex[._]+PGCAP+POLY+orderedrows+currentNOFIT0 on output sibling; first apply helper on3_2 for planned-position/hop preview, render/LOOK BEFORE actualPLACE, and actualplacedLOOK before route. Do not run an obvious >405um form; price source stages if true long groups remain. No ir2 extraction or CAD launch happened before hand-back.
- **h10a h10r2 LIVE**, E8 unit915170-1794908647/containerf586d78ea5ad, `fable-fix-s81-col/h10a/col_h10_r2__t1__cl1f5d6c2a__pv0c1de895`; log `~/fable-fix-s81-col/h10a_h10_r2_route.log`. Long max-wire repair at21000/115096, CPU verified active PID1534533; preserve, not hung from flat logs. Old rm3 line closed DRT0255 withoutPGCAP; no more ECO there.
- **P1 source conflict RESOLVED** manually preserving current main instance/plan identity plus opt-in cohort/profile selection: `claude/s81-colrelay-depth-1116@7fe6814e51008ac9040a2bae845929b86f5e717f`, normal GREEN46/46. Root approval requested/handled by root merge lane. Source-only, not production adoption. Original52f merge conflict was frame_schedule_asb/lower_xs; baseline failures are dense_split2 xs_stage_map `(0,0)` fixture and missing selected rf3r source in old asbuilt manifest, both reproduced on main; no reruns. P1 exact6type expected rows+66 affected lanes delivered E10 formB_hi3/P1_expected_rows_vs_C4R3_1117.json.
- **NEW h9P2 source proposal COMMITTED/PUSHED** same existing branch `@cd90e102f72ce5ec81f23a1ac008a347537a4d42`,14 NEW files only, no existing source edits. Sole normal gate owned MERGE-OPS client942177 (ask that lane for terminal); no extra component job needed. Model before source in results/s81_colrelay_h9p2_1117, transformer tools/s81_dv/frame_colrelay_h9p2.py, minimum mechanism test test_frame_colrelay_h9p2.py. Default off `COLRELAY_H9P2`. Add writer6/7/8+so1 one stage and ALL4 XO276b chunks one stage for coherent1104b word. Geometric lowerbound alone missed writer7 and XO1; those are needed for data coherence.
- Actual minimum native full-frame trace on current C4 source29define set: baseline70414FF -> corrected72091 (+1670 data+7 reset), root/FP32 reduction order/word counts unchanged. Eight stations e5/e6/e7/e9/e10/e11/e12/e14 get coherent data/go/cfg/tag+1; other stations0; XO+1. Native corrected profile PASS89changedinterfaces. V1 mixed q1/e1 vs data/control was FAIL and preserved in rejected_v1_alignment.json. Mechanism4000edges/30resetbursts, default and sliced styles PASS; bypass mutants caughtcycle6 both. Compact source-pinned results committed; full diagnostics E7 `fable-fix-s81-coltap/h9p2_native1117/{before,after_v3}` and component_v3_1117. Completed jobs, no auxiliaries left live.
- P2 producer expected-before12type rows/cohort map delivered beside E10 C4 candidate `formB_hi3/H9P2_expected_rows_vs_C4R3_1117.json` and `H9P2_frame_cohort_map1117.json`; also committed copies. Total20124 FF if12replicas. NOT applied. Next fresh producer source/parameter event+counted bind/LAT, exact calendars/golden/token price, legal fullshape GEN/review, then physical+production throughput. IFN0 signed HE/HW are complementary (same outlines/pins do not solve parent NOFIT); if selected together, re-extract profile on that same IFN0 source. Never reuse old C3 profile or blanket+4 lane metadata.
- Proposed independent wave1 hold split remains NOT APPLIED at intel2 `~/fable-fix-s81-col/hold_split_wave1_proposed_1117.json`; preserves137 original keys+lint, separate family results col-h10r2/col-h9r2/col-h9r1 and additional h9r1-rows source result. No wave release results posted. All236 item_env POLY already staged earlier; PGCAP die-wide remains. No new OWNER? item.
