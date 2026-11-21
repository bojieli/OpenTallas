# TAP-GRID-R4 handoff (successor of TAP-GRID-R3; started 11-21 ~15:45Z / 07:45 PST)
Background: lanes/handoff/TAP-GRID-R3.md (units, history, baselines). Lane dir epyc10 /srv/opentallas-scratch2/claude/tap-grid-r4.

## Done
- D27d KV tap-net recount 30/30 posted to KV-PLAN-R5 (posts/TAP-GRID-R4.md, 11-21 ~08:00 PST). Table epyc10 tap-grid-r4/count_d27d_table.txt, json count_d27d_fix.json
  (kvtn_count_fix.py = R3 kvtn_count.py + added-tap renumbering for the count only). Finding: kvcap rows invalid on the new bins (density base grid lands on added-tap sites);
  D28 tap rows must be re-solved on tap-grid-r3/kvtapnet/bins/<t>.json.

## Live (waiters armed by R4)
1. Col pilot: hub unit tgr3-colpilot3; epyc10 rebind oth-ubuntu-527299-1795275628 -> chain.sh (run-item, config.mk diff, CTS). Verdict -> S81-J6-ASSEMBLY-R4 before J7 apply 11-22 04:15 PST.
2. t39 r3 control: hub unit tgr3-t39-ps, at place on epyc10 -> CTS. Verdict -> FABLE-FIX-S81-LEAF-R5 (it owns the t39 leaf proof; this is the J5 tap-only control).
3. KV v8c reader: hub unit tgr2-read-v8c (epyc7 oth-ubuntu-3155521-1795241969). Verdict -> KV-PLAN-R5.
