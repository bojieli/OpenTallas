# FLEET-WATCH-R4 handoff (Claude Sonnet; succeeds FLEET-WATCH-R3; 2026-11-21 ~01:40 PST)
## State
- REPIN in rt/current; no KW_REPIN line in any geom.log yet (30-min path unfired).
- 3 RETRY-INFRA rows: cbx_q10__cl94a12200 bb8427559fc54 has a16 (spec only, unit.log stale AP_START); col_h9_r0_p3 pv13474472 b52f479f586b4 and dsdv c1x_C t4 b64d601170cf4 still at a3/a1 (INFRA) at 01:40; waiter w4 logs relaunch to scratchpad w4.log.
- intel1 scratch2 162 GB free 96%. du top: kw43-wave-1109n 1358G (protected), kw45 734G, ot-jobs 192G, kw43-wave-1109 175G, fam-s81-col 117G, autopilot 90G. Re-du in 1 h for growth.
## Open
- Hourly: ot-run --status, waiters pinned to hosts admitting 0 GB; fix the class.
- Stand down before 330k.
