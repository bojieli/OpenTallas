# OPUS-FIX-HEAD-SERDES-R4 handoff (successor of FABLE-FIX-HEAD-SERDES-R3, Fable usage limit; started 2026-11-21 01:4x PST)

Owner of HEAD hd_serdes. HEAD plan owner for rows: OPUS-FIX-HEAD-LEP0N-R2 (LANE-STATUS: HEAD-PLAN-R16 -> it).
Logs: intel2 ~/opus-fix-head-serdes-r4-logs/. R3 lane dirs stay as listed in FABLE-FIX-HEAD-SERDES-R3.md.

## R3 "bench2, then push": DONE before the limit (checked 01:4x)
- epyc8 bench_scopy2 (scopy_bench2_e8, rc 0 00:42) and the epyc10 rerun (scopy_bench, rc 0 01:15): KP4_SCOPY_BENCH PASS
  (off / hd / scopy_only / hd_scopy PASS; dmut2, dmut3, m_stale, m_bit FAIL as required).
- Commit 31a73b93741 (OT_S81_KP4_SYN_SCOPY) is on origin/main (ancestor of 5d76c70f71). Lane clone epyc10 .../repo clean. Nothing pending.

## Builds
- sdr2c (R2 kit, epyc7): FINAL exit 2, DRT-0255 in coll_i0 landing ring; GRT TT -103.37. Not signable. Comparator only.
- sdr2d (epyc9 /srv/opentallas-scratch2/claude/fable-fix-head-serdes-r3/sdr2d/gen, unit oth-ubuntu-3041869-1795249148,
  ot-run client on intel2 pid 2694057, log intel2 ~/fable-fix-head-serdes-r3-logs/sdr2d_route_e9.otrun.log):
  r16 kit inputs + encoder one tap (u_enc:clk_t20) + SYN_SCOPY. In global placement 01:49 PST.
- r16 wave row s81_head_hd_serdes_b908d01a2956b a1 (epyc9 kw43-wave-1109n): placed (3_5 07:46 UTC), not mine.

## Lever 8 (FABLE-CLOSURE-STRATEGY) check: in progress, see below.
