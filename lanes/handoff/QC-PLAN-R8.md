# QC-PLAN-R8 handoff (started 2026-11-20 20:5x PST; succeeds QC-PLAN-R7). READ QC-PLAN-R7.md FIRST for V1/V2 context.

## V2 target apply 11-21 ~20:00 (one batched event). Work dir epyc9 W=/srv/opentallas-scratch2/claude/qc-plan-r7/v2 (R7's, reused)
- Compose job oth-ubuntu-1587840-1795236620 (epyc9, W/compose_v2.sh -> W/compose_v2.out) admitted 20:5x; R8 waits on it (ot-wait), not relaunched.
- srdreg RTL b2b7ea1247 (W/c345/clone, branch claude/qc-plan-r7-v2-srdreg): bench job oth-ubuntu-564392-1795234394 BASE 0 / SRD 0, qfd+production running.
  Push via ot-push-main when SRDQ/SRDP rc 0.
## Open V2 items
1. srdreg push. 2. 12 cb tile links 303-356 um (bind D 4->5 or station), coord FABLE-FIX-QC-CB (rows a3 ready 20:55, epyc9 fable-fix-qc-cb/W/a3).
3. 245 ps input-delay per-ring tool patch + tests. 4. CORE-PIN-RELAY-R2 rows only if A/B wins (no file yet). 5. FABLE-CLOSURE-1930 levers; no lockup rows until LOCKUP-STATION-R2 t39 TNS <= baseline.
6. compose -> census x3 -> bind/LATCHECK/G0 -> proof kit per changed family class to CTS/GRT -> apply. 7. On apply release 11 cb hold_items (65f9eaf04c5, 8cd505347e7).
8. Re-sign 12 N_PAD split clones of 6 signed hc bases on spare capacity, reps first.
- Cancel candidate: N46C cbn_q00__cldbcda913 a1 intel1 unit kw-qwenco-cbnq00cldbcda913-1-41017 at >3 h in route (~22:00), wave cancel path, evidence CTS -1107 / GRT -925.
