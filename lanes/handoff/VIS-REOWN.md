# VIS-REOWN handoff (11-24 08:2x PST)
Job: past-SLA VIS-COVERAGE rows -> PROBE-THROUGH (COORD 08:04 ruling 2), fast review, promote to verdict.
Done:
- main bb319d88249e: lbl_gate ALLOWED += PROBE-THROUGH (+ test); deployed rt 4c29a21f8f22 all hosts 08:15.
- hub ea8f9ff4: 186 DRAFT -> PROBE-THROUGH (HEAD 1, KV 47, QC 39, S81 99).
- hub 3ab10282: verdict prefixes [VIS-REOWN ...]: FAIL-STRUCT CONFIRMED 158, NO-RENDER 25 (S81 svc x16 + serdes x2, KV 7), CENSUS-COVERED 3 (cbf_q11, slw_su_l1 x2).
- hub 9accf1eb: 104 PRE-PASS (all >30 h) -> PROBE-THROUGH by intent (iqf__t1/seqhost__t1 included).
Renders viewed: leaf lanech_before_after + j8 sheet0 (J9 LANECH reduces, does not clear lane junctions t39/t21/t52/t65), kv3_pv_v3 d28 place (tap blob y560-600, 13 over-cap taps), coll_core pkit4 (48-um g_xf slit hotspot), hd_lep0N w11.
Next: PROBE-PASS only on a clean probe census (hotspot_census check --probe); watch probe kits reach place/GRT; NO-RENDER rows reviewed on their 3_place.

## 09:1x COORD 08:55: probe kits feed VISUAL-QUEUE + census verdicts
- Code: tools/autopilot/probe_visual.py + kit_wave.visual_queue_publish hook + test_probe_visual.py (clone intel2 /srv/opentallas-scratch2/claude/vis-reown/clone, commit 8264bd2adb; push log vis-reown/tmp/push2.log).
- Census: intel2 cron */10 runs /srv/opentallas-scratch2/claude/vis-reown/census_sweep.py scan launch judge promote (state census/state.json, log census/sweep.log). It launches only kits from 11-24 or later; skips E8/E10; promote sets VIS-COVERAGE PROBE-PASS/FAIL and posts.
- Reviewed renders: kv3_pv A5t3 OK, cbf_q01 ISSUES (central tap pile), slw_st_a_v2 cl9f076 OK.
