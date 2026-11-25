# VIS-REOWN handoff (11-25 03:5x PST) -- ROLE CHANGED: AGGREGATION (COORD/OWNER 04:5x)
- No render review by me: FP-CONVERGE lanes + type owners self-review PLAN / post-GP / post-GRT renders (STAGE-PLATEAU VIS-QUEUE.tsv). 30-min review waiter stopped.
- I keep current: census (intel2 vis-reown/census_sweep.py, cron */10), VIS-COVERAGE (now 11 cols: col 11 stage PLAN|GP|PLACE|GRT|ROUTE|SIGNOFF|-, refreshed by vis-reown/agg.py stage --commit in the same cron), VIS-CAUSES.tsv (26 census FAILs, causes C1-C8; kv3_hgi 1124041954 back to WAIT-ROUTE per COORD).
- From lanes/FP-<die>.tsv (not yet created at 03:5x; schema proposed in my 03:5x post): fold verdicts into VIS-COVERAGE/VIS-CAUSES; flag to COORD renders with no verdict after 1 h and lane verdicts that disagree with gate results; hourly counts post.
- Verdict rule unchanged: final DRC/timing only from route/sign-off result; GP checkpoint FAIL = setup < -150 ps on placed DB / pile / hot spot / macro face on strap.
- 06:5x: agg.py merge_rows (one tag per row+source+stage, idempotent) + vq_pending (render key = kit dir + checkpoint; verdicts are separate VIS-QUEUE rows) + test_agg.py (4 tests). Census FAIL 27 (+kv3_pc_v1 r877307f5d C4, kv3_pv_v4n C9). Asked FP lanes why FP-<die>.tsv stale since 04:07-05:06.


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
- 09:4x COORD correction: E8/E10 have disk again. census_sweep now skips hosts under 150 GB free and skips E9 (over cap) and E11 (IO-bound). Relaunch list 2 sent: 13 E8/E10 units, plus list 1 E9 units moved to E10/E8/E7. E2 at 77G is skipped.
- 10:1x judge: CTS setup fails only < -300 (pre-repair); 3 near-miss FAILs reverted to PROBE-THROUGH; re-census cooldown 90 min. Verdicts: PROBE-PASS 6, FAIL kv3_hgi.
- 10:3x COORD correction: probe_visual picks by plan sha (e52463abec). Withdrawn ISSUES: sle_su_c, slw_su_l1 cla2a, pv_v12, hd_lep0N r7, serdes t13/14/16. cb renders were C1h (sha 894e6f), but the CB-1-absent claim was wrong. Re-review hd_lep0N r8 once it renders.
- 14:5x: revoked 9 PROBE-PASS (chain FAIL x8, no final DB x1); judge = chain first + final DB required; 6 PROBE-PASS stand.
- 21:0x COORD: verdicts only from route/sign-off result (judge WAIT-ROUTE state); all 8 PROBE-PASS revoked (3 FAIL, 5 PROBE-THROUGH). st_a sign-off class: DRC 72 + TT skew 320-386.

- 2026-11-25 07:5x: HOURLY posted (059d6c5a). census_sweep skips epyc9/10/11 by default (COORD temporary host ruling; VR_SKIP_HOSTS= lifts). Next hourly ~08:5x. Open: FP-<die> files stale since 04-05h, no reply; serdes__t1 plan FAIL vs PROBE-PASS asked of FP-CONVERGE-S81.
