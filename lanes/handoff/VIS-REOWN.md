# VIS-REOWN handoff (11-24 08:2x PST)
Job: past-SLA VIS-COVERAGE rows -> PROBE-THROUGH (COORD 08:04 ruling 2), fast review, promote to verdict.
Done:
- main bb319d88249e: lbl_gate ALLOWED += PROBE-THROUGH (+ test); deployed rt 4c29a21f8f22 all hosts 08:15.
- hub ea8f9ff4: 186 DRAFT -> PROBE-THROUGH (HEAD 1, KV 47, QC 39, S81 99).
- hub 3ab10282: verdict prefixes [VIS-REOWN ...]: FAIL-STRUCT CONFIRMED 158, NO-RENDER 25 (S81 svc x16 + serdes x2, KV 7), CENSUS-COVERED 3 (cbf_q11, slw_su_l1 x2).
- hub 9accf1eb: 104 PRE-PASS (all >30 h) -> PROBE-THROUGH by intent (iqf__t1/seqhost__t1 included).
Renders viewed: leaf lanech_before_after + j8 sheet0 (J9 LANECH reduces, does not clear lane junctions t39/t21/t52/t65), kv3_pv_v3 d28 place (tap blob y560-600, 13 over-cap taps), coll_core pkit4 (48-um g_xf slit hotspot), hd_lep0N w11.
Next: PROBE-PASS only on a clean probe census (hotspot_census check --probe); watch probe kits reach place/GRT; NO-RENDER rows reviewed on their 3_place.
