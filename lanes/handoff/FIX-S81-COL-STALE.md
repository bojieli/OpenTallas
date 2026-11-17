# FIX-S81-COL-STALE handoff (Opus; started 2026-11-16 19:3x PST)

Owns the 203 S81 types that STALE listed as unowned (59-62 h): 202 col_h9/h10 `__pv*` variants + ot_s81sl_leaf__t40__cl86ea32b3__sid5S.
Work dir: intel2 /srv/opentallas-scratch2/claude/fix-s81-col-stale (cls.py classifier, edit_holds.py, items/wave lists, repo = own clone).
Lists: lanes/handoff/FIX-S81-COL-STALE-class.tsv (per item), FIX-S81-COL-STALE-lever2.tsv (76, for S81-DIE-R2).
Owner rows: autopilot/COORD-ROUTED-OWNERS.tsv (203 exact rows -> FIX-S81-COL-STALE).

## What DEDUP is
kit_wave.py WF-1 (DEDUP_DEFAULT s81 col_h*): col `__pv<hash>` kits of one base are byte-identical; the first member claims the kit
identity (autopilot/kit_identity.json), later members get status DEDUP and are credited when the owner signs. The 56 DEDUP + 3
DEDUP-WAIT rows are leftovers of the 11-14 plan line (owner rows since CANCELLED/SUPERSEDED). DEDUP is NOT what blocks them.

## Cause (all 202 col)
Every col item is held by a hold record (die s81 hold_records):
- s81-mig-001-k1-k2-k1-k4 + s81-mig-005-k5-k6-k2-k2 (col-wave1: h9_r1, h9_r2, h10_r2) -> 126 items
- s81-mig-001-k1-k2-k1-k3 + s81-mig-005-k5-k6-k2-k1 (col-wave2: h9_r0_p1..p6, h10_r0_p1, h10_r0_p4, h10_r1) -> 76 items
Release was event_adopt:B6gF2s4 + result:FABLE-FIX-S81-COLTAP:col-waveN + lint_clean:s81. Two terms could never be met:
(a) event_adopt matches only the die `event` (sha 3fa87b84b18) or the plan file basename (plan_h2_2249.json); plan_event
B6gF2s4tapfix1 is not looked at, and the regex has a no-suffix lookahead. Same class for every S81 event_adopt:B6gF2s* term
(e.g. s81-mig-024-k1 event_adopt:B6gF2s3, which holds the leaf t40 sid5S item and the whole dsdv/gunit/leaf set).
(b) FABLE-FIX-S81-COLTAP is Fable-limited, last RESULT 14:15, no col-wave PASS ever.
Not blocking: route hold s81-route-tree-01 (tree_ready met in the wave: TREE-SWITCH log), only_items (all 216 col in), hold_items {}.

## Done
19:4x: the 4 records now release on result:S81-TYPES-R2:col-wave1|col-wave2 + lint_clean:s81 (old terms kept in
prev_release_fix_s81_col_stale). Edited under kit_wave.lock, committed via coord-commit.sh.

## Release conditions (who posts PASS)
- col-wave1 (126): S81-TYPES-R2 posts "RESULT [S81-TYPES-R2 -> ...] col-wave1 PASS" when a wave1 pilot signs off on a src tree carrying
  c0ddf60 (relay regex, merged), 430397fe1b0 (pair_skew psambig, col GRT-policy crash, READY not merged) and fe26ef60b15 (relay
  fail-closed, READY not merged), and the wave's s81 src has them (current src_s81_pin_3c913dbdfb23_f2s4_cohort_d3 has the OLD
  RELAY_MID_RE [.] -> needs a src refresh).
- col-wave2 (76): lever 2. S81-DIE-R2 relay rows (hop <= 405 um, legal sites for NOFIT groups, per-bit istations, bs mirror site)
  in an adopted event, then S81-TYPES-R2 col-wave2 PASS.
On release the wave relaunches them; DEDUP collapses each base to its distinct kits.

## Next
1. Watch merges of 430397fe1b0 / fe26ef60b15 and the s81 src refresh; nudge MERGE-QUEUE / FLEET-OPS-R.
2. When col-wave1 releases: watch launches (log.txt KIT-WAVE ... col_h9_r1/r2/h10_r2), DEDUP claims, failures by class.
3. Sign-off -> export AGIdock + rtx-pro.
4. Leaf t40 sid5S: die-wide s81-mig-024-k1 (event_adopt:B6gF2s3 unmatchable) -> DIE-S81-R2 / HOLDGEN.

## Codex park at Claude reset — 2026-11-16 19:50 PST
- r414 exact source-event retypes APPLIED under kit_wave.lock and pushed: s81-mig-024-k1, s81-mig-003-k3-k4, s81-mig-002-k2-k3-k1, s81-mig-006-k6-k7-k2 now event_adopt:3fa87b84b18. Every original lint/svc-ready term unchanged; old release arrays retained. Receipt lanes/handoff/FIX-S81-COL-STALE-source-carry-1116.json. Commits 055a501f2a95734d3b0facca75a49a2bdb59a0b5 and 48b40827302a46a0c8f78986f0d6d78d07dd0ef1.
- Generic source fix published claude/fix-s81-col-stale-plan-event-1116 @cca8efdc426cd227b25f7bf3bfa147a540a14da3: plan_event becomes a current adopted identity in validation and both release evaluators. Exact token/explicit trailing-star semantics retained; previous/planned identities never release. Focused37/37 PASS. Normal gate client2070076 remains RUNNING, no terminal record or approval; log intel2 /srv/opentallas-scratch2/claude/fix-s81-col-stale/gate_cca8efdc.log. Do not start duplicate.
- Existing full clone checkout PID1916996 remains active inherited fetch, preserved. Source fix built via private draft-index/commit-tree in same clone to avoid touching its active index. Draft4 source/test files and three helper symlinks in ../draft. Own write-tree lazy fetch was stopped exact own PIDs2020347/2019972; private-index write-tree --missing-ok completed, no inherited process stopped.
- mig007 missing-view hold remains: coll_e view gates.json view_completefalse / LOCAL_PASS_NEEDS_PARENT, TT+30.31 FF+0.02 LEC equivalent archived; lnland signed. Root owns R-MINIMAL sufficiency decision.
- QC equal11 st_b administrative split NOT APPLIED. Root/QC requested after Kf atomic switch; current still S4q6d last read. Rowproof has11 equal st_b,11 fw and3 su_c differ internal_stations. Preserve latter14 and all other S4q8/S4q6e holds until qualified. QC informed park.
- KV3 obsolete source/port holds remain pending HG2c strictbind/R8/LAT proof: pc-sysc-01, mig004-k11, mig007-k12; KV worker owns qualification, no guessed successor matching.
- Future S81 C4 adopt must explicitly carry qualified source terms to new current identity or they rehold; no generic history bypass added. No new job or edit after park except this handoff.

## 2026-11-16 20:0x PST (COORD resume)
- plan_event fix: claude/fix-s81-col-stale-plan-event-1116 @cca8efdc426cd227b25f7bf3bfa147a540a14da3 (Codex-built, reviewed by me: adopted_events() = event, plan_event, plan stem; prev/planned never release). Normal gate GREEN 140/140 on main 12fbf476346 (~/merge-queue/gates/cca8efdc...json). READY posted.
- r414 (Codex) retyped mig024-k1/mig003/mig002/mig006 to event_adopt:3fa87b84b18; mig007-k7-k8 kept (coll_e view incomplete).
- Audit of all live hold records: lanes/handoff/FIX-S81-COL-STALE-hold-audit.tsv (script intel2 W/audit.py).
- QC: added qwen_compute-kf-clock-l2-1116 (27 uncovered clock types, event_adopt:S4q9l2* + lint_clean) and qwen_compute-kf-face-m-1116 (slw_fw_v3, coll_ftc, event_adopt:S4q9m* + lint_clean), bound to plan 9982b4d5, carry; planned_events += S4q9l2, S4q9l2d, S4q9m. Prefix * so the l2d / m_r plan names also release.
- Next: D4 S81 src publication (Codex left STOP marker tools-converge/s81/d4col_1116/STOP; resume from candidate/finish.py), then col-wave1 pilot with S81-TYPES-R2.
