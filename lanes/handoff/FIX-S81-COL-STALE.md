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
