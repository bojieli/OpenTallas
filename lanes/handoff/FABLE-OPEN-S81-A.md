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
