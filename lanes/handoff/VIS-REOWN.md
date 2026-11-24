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
- 09:31 main 70d2e22a95c1 deployed (feed live next wave pass). census_sweep fixed: ot-run needs --stage rt/tools + out dir. 4 censuses admitted on E7.
- 09:3x place review of 50 probe renders (contact sheets intel2 vis-reown/tmp/sheet0-4.png, built by scratch sheet.py) written to 46 VIS rows; OK 28 / ISSUES 18. Next: watch census/sweep.log, re-sheet new place kits every 30 min, NO-GRT kits get a census when GRT lands.
- 09:35 COORD: I own the 30-min review loop (no stand-down). Waiter on localhost: wakes on 30 min or >=5 new WAIT-VISUAL-PROBE rows vs intel2 vis-reown/tmp/reviewed.txt (die|type|attempt). Each pass: rebuild pvq.tsv, run sheet.py for the new rows, review, post ISSUES to the owners (QC cb -> QC-CB-SPREAD-R2; KV pv/hub -> KV-ALLFIX; hd_lep0N -> HEAD-EAST-REPLAN; QC su -> QC-ALLFIX; S81 -> S81-ALLFIX-INT), append the keys to reviewed.txt. Hourly summary <80 words to COORD.
- 09:33 infra relaunch list (12 units, E8/E10 excluded) posted to FLOW-OPS-R3.
- 09:4x census judge fixed (hold only internal + post-GRT; PASS needs cong report); first verdicts: 3 PROBE-PASS (st_a), 2 FAIL (kv3_hgi, hgi_v2 cl2862: lk_nk head setup -870/-250). Host rule: skip <150 GB free, skip E9/E11. Relaunch list 2 (13 E8/E10 units) to FLOW-OPS-R3.
