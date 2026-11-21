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

## D28 KV tap rows (COORD 11-21 ~08:3x PST: own the fix, <=3000/tap, private strict bind + G0, hand to KV-PLAN-R5)
- Solver epyc10 tap-grid-r4/kvtn_solve.py (grid types), kvtn_pv.py (pv density), compose_rows.py -> d28_tap_rows.json, plan_c.d28tap.json, d28_tap_report.json. All 26 types <=3000.
- Gate: epyc8 tap-grid-r4/tree (rsync --link-dest copy of kv-plan-r3/d27c/tree; plan_c.json + sink_bins/*__tapnet.json replaced by mv), script tap-grid-r4/gate_d28tap.sh,
  out tap-grid-r4/gate1/gate.out, unit oth-ubuntu-1088007-1795279214. Next: diff bind errors vs D27d r5 (27 errors, kv-plan-r3/d27c/bindgate_d27d_r5), then hand rows.
- pv halves: asked OPUS-FIX-KV-PV-R5 for split12 plan + half names/origins; clip parent bins into halves and solve.
- Col pilot: rebind PASS 16:31Z (BIND_RC 0, LATCHECK_RC 0); run-item in kit_rtl/gen. t39: place DONE, CTS waiter armed.
