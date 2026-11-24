# FABLE-OPEN-S81-A (Fable) handoff
Scope: S81 OPEN ledger items rc35, rc37, x6, x14. Deadline: ROWS-READY to S81-J9-ASSEMBLY-R6 by 14:30 PST 11-23 (PRE-clean 15:30, compose < 17:00, cut 18:00).

## rc35 (slice C hold cells) - 11:05
- Cause measured (posts 605a593, 8122d4a): 33.6k hold cells of lepe_nh_mus_C__t1 (kit intel2 kw43 .../a9ed808a98d/private/FAM-S81-LEPE-4/dsdv_slice_lepe_nh_mus_C__t1_1122022123) pad self-loops 5.3k + same-leaf pairs 8.4k + same-tap other leaf 2.7k + cross-tap 15.3k; 14k sit in x384-480 y192-480. Driver: uniform rr 30 ps family pass.
- Row HOLD-SAMELEAF-1: main 91c75df2289 (clone intel1 /srv/opentallas-scratch2/claude/fable-open-s81-a/clone, commit a60dd155ce): tools/die_plan/hold_same_leaf.tcl, pregrt_ff_hold.py (same_leaf_on/same_leaf_text), hold_guard_grt.tcl hook, test_hold_same_leaf.py. Switch: gen env OT_HOLD_SAME_LEAF=1 (off = byte-identical).
- What-if STA (intel2 fable-open-s81-a/wf3/whatif.log): rr ends < 30 ps 34,806 -> 16,245; exact SDC restore. NOTE Codex's 07:58 "0.41%" line came from a get_cells bug in my first draft; corrected.
- Replay (gate): intel2 unit oth-ubuntu-176977-1795460000, dir fable-open-s81-a/replay1 (pregrt_ff_hold.log; kit's own tcl + scope via PG.same_leaf_text; DB copy of 4_cts_pre_tt.odb). Started 10:53, ~3 h. Read: hold cells vs 44,612, wns >= 5, setup vs -784.9, FALLBACK none; then geom dump + tmp/holdcells.py for pocket count.
- Then: ROWS-READY to ASSEMBLY (die_gen_env OT_HOLD_SAME_LEAF=1 + tools sha >= 91c75df2289) + FIX-LEDGER; cross-tap residue (12.3k ends) = REASONED onto tap rows, read at first J9 C probe CTS.
- GRT-stage wrapper is unit-tested with tclsh mocks only (no real GRT session run yet): say so in the packet.

## rc37 / x6 / x14
Workers (subagents) resumed 10:50 with Codex's 07:30-08:59 results (posts under this lane name): x14 private source de45a42c85cd ready for PRE; x6 plan 0e32aea4d155 MISC10c seats 22/22 face buses max 291.5 um; rc37 per-class STA recovered, lpc pad rank seating in progress, data intel1 fable-open-s81-a/rc37/. Their returns go into ROWS-READY / REASONED posts.

## 11:15 COORD note
- x6: covered by SEQHOST-VLG-STN-1 in MISC gate 10c (plan 0e32aea4d155, PRE PASS, strict bind running); 9 legs +45..+51 ps at place (epyc9 fable-open-s81-a/sta/j8wave_place.log); accepted by FABLE-RC-ALL. Left: 10c bind, LATCHECK, placed re-scan -> then ledger GATED.
- rc35: COORD/FABLE-RC-ALL ask: classify the ~3,250 internal ends < 0 (cross-tap / cross-leaf / IO) + row per class; post by 14:30 with the replay. Dump running intel2 fable-open-s81-a/wf4 (neg_ends.tsv, unit oth-ubuntu-453014).

## 15:55 state
- rc35: HOLD-SAMELEAF-1 replay PASS (44,612 -> 26,247 cells; replay1/pregrt_ff_hold.log); in B1 overlay + env. SLICEC-TAPPAIR-CAP-1 ops epyc10 fable-open-s81-a/tprow/ops_tpcap.json af658d95d0f9, PRE PASS on Wave A, old-value ok on B2 a6e153d98ff6; no built kit. Lockup row epyc10 fable-open-s81-a/lk/row ops 69a5599765ce (worker aa2277e). ROWS-READY posted 15:55.
- x14 (worker af62b67: epyc10 fable-open-s81-a/x14row, gate_1517), rc37 (worker a97bce3: LP-PROFILE-1, probes done), lockup worker: all resumed 15:45, final posts due 16:40. x6 REASONED accepted.

## 16:10 state (after COORD rulings 16:0x)
- rc35: HOLD-SAMELEAF-1 in B1 (replay PASS). SLICEC-TAPPAIR-CAP-1 ops epyc10 fable-open-s81-a/tprow/ops_tpcap.json af658d95d0f9 -> FIRST same-day amendment (COORD). Lockup row (epyc10 fable-open-s81-a/lk/row ops_rc35lk.json 69a5599765ce) HELD as fallback: use only if the first J9 C kit CTS still shows cross_tap ends < 0 (line "OT_PREGRT_FF_HOLD class before ... cross_tap N"; baseline 3,228). Also read on that kit: "OT_HOLD_SAME_LEAF installed" at GRT and no restore error (GRT wrapper is mock-tested only).
- rc37: NOT GATED. Priced pair for dsdv_slice_lepe_mu_LP__t2 only -> first amendment: ops epyc10 fable-open-s81-a/rc37/LP-PROFILE-1b-rc37-ops.json 631181597c49 (verilog_defines RIP1 -> RIP3 + ROS3); LK1 price lanes/handoff/FABLE-OPEN-S81-A-rc37-lk1_wavea_lp_profile1b.json e49ee45a5ca1 (ri 1->3 edges, ro/t_host/t_kd/mu_c 0->3, credit round trip 10 unchanged; tool epyc7 fam-lepe4/j9/token_lk1_1123/lep_model.py). Probe: 438 ends WNS -265.9 at RIP1 -> 54 ends, none in the traverse classes at RIP3+ROS3 (rc37/cen2_muR1 vs cen2_muF2). One-op PRE on B1 v3 tail ae3101241d6b: epyc10 fable-open-s81-a/rc37/b1pre (plan 301aa03b2751, pre_b1_1b.log) launched 16:08. Open: strict bind/LATCHECK not run; reset root_r->group_r (R1 tap_reset_split copies unbuffered) and lpad_lpc classes open (hub 08d58c7); lepw_mu_LP t2 / lepw_mus_LP t2 REASONED past the cut: the RIP3+ROS3 profile is NOT sufficient there (lepw_mus probe WNS -347 -> -677), priced rows to draft for the next event.
- x14: REASONED (COORD accepted). S81-LPR-FOREST on main 538684029b; ops epyc10 fable-open-s81-a/x14row/S81-LPR-FOREST-ops.json f7fb40b63c1c (11 serdes types, define OT_S81_LPR_FOREST, 0 cycles). Benches PASS, PRE 0 findings, scoped strict bind serdes__t14 0 errors (gate_1517). Not in B1. Next: after the first full bind that carries it, build serdes__t14 kit --goal cts and read the lpr_syn path (was -311.83) + LATCHECK.
- x6: closes on B1 strict/LAT + seqhost probe (SEQHOST row byte-identical in B1; no 10c dependency).
- Workers: rc37 a97bce3 (done), x14 af62b67, lockup aa2277e, x6 aa5427d.
- rc37 one-op PRE on B1 tail ae3101241d6b: PASS findings 0 (epyc10 fable-open-s81-a/rc37/b1pre/pre_b1_1b.log, plan 301aa03b2751), posted 16:05.
