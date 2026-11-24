# FABLE-RC-KV handoff (Fable 5.2; independent root-cause reviewer, die KV only; split from FABLE-RC-ALL 11-23 19:22 PST)
Read-only except posts: no launches, deletes, kills. Briefs: localhost scratchpad split_brief.txt, rules.txt, resume_1123b.txt. Local notes + waiter: scratchpad/fablerckv (wait_kv.sh <HH:MM>, lastline).
Carried from FABLE-RC-ALL: D29 scope verdict e47aa7e5 (6 typed holds: pc*, sys_c, hub_C, hg + hg_v*, pv list, hub_Wo/Eo conditional); A1 census a-g b32ca1f8; fclk bound 330 ps (18:57); BPC undefined_modules > 0 = FAIL.
Integrator: KV-ALLFIX (epyc8 /srv/opentallas-scratch2/claude/kv-allfix; A2f plan 2d63fe8dbefe, gate_A2f). D29 apply: KV-D29 driver intel2 ~/tmp/kvd29/d29_apply.out, ETA APPLIED ~20:15.
## Log
- 19:22 TAKING (552ecb1e). 19:26 misrouted COORD HEAD West-waiter order: not started, posted to COORD + HEAD-WEST (68b7e7b1).
- 19:35 A2e/A2f pre-gate read (331a59eb): (1) ISTCYC FAIL 6 lanes L1850/1854/1858/1884/1888/1894 pv_v2e/v4e/v6e y_valid -> hub_C stations 6 vs fixed_cycles 4 (new with A2e rows) + R8STALE 3 tables; (2) fclk > 330 on 16 types (hgi, hgi_v3/5/6/7/8, pv_v1n/v3n/v7/v1e 637.7; pv_v5/5n/5e/5ne 604.9; pv_v6e/6ne 555.9): one landing-core family row, probes only; (3) RREACH/RCOLL/EARLYTAP/ASTKTAP/COUNTSYNC confirmed from logs only; (4) open: STREETSTN left 23, TAPSPLIT/FTLOCKUP not in A2f, ADV-PORT-PIN hg, hg_v1p2, hg_v1p6, hg_v3, sys_c.
- 19:50 A2g 3857747ea992 (A2f + ISTPRICE) is the gate to read (COORD): six ISTCYC lanes now 6 cycles, precheck ISTCYC 0. Owed on gate: LAT delta list for the 31 repriced lanes, r8_refresh of 3 tables. TAPSPLIT 874a8f84c7ee accepted (2ce6d650); pv strip-area check owed by PORTPIN. COORD started KV-OPEN-FWDCLK + KV-OPEN-INCORE. Waiter re-armed to 21:45.
## Next
- D29 APPLIED post: compare hold list with e47aa7e5.
- gate_A2f result: strict/LAT/G0/BPC/TAUDIT; the 6 ISTCYC lanes; re-check census c/d on g0/g0_report.json.
- Iteration-1 round at place/GRT: whole-die render + per type place/grt PNG, 4_cts post-hook report, final 5_1_grt.odb; PLACED hops at 405 um; fclk ring window on the 16 types.
