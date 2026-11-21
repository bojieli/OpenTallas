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

## Lever 8 (FABLE-CLOSURE-STRATEGY) check: DONE 02:1x, ring-density half does NOT agree for hd_serdes (post a5a2402048)
- sdr2c 5_1_grt.odb, 3x3-um bins over the coll_i0 ring band: ring mean util 0.26, no bin >= 0.9; DRT-0255 box bins 0.14-0.26.
  GRT overflow 651 is all at the S pin edge (y 0-2, x 1650-1850, pma_rx / coll_o0 pins). Script epyc7
  /srv/opentallas-scratch2/claude/opus-fix-head-serdes-r4/{dens.sh,q_dens/dens.tcl}.
- Failing net guide: M4 x 1969.9-1996.7 in gcell row y 34.77-35.34 under the reserved clock-site column (x 1990.44-1992.60,
  y 34.83-57.78), one free M4 track 34.776. All 1263 reserved M1-M7 obstruction rects are off the 0.57-um gcell grid;
  20,611 guide boxes / 5,368 nets partially overlap them (epyc7 .../opus-fix-head-serdes-r4/gobs.py). Candidate only.
- No ring padding generator change. Encoder one-tap half = sdr2d.

## Waiting
- Background waiter on sdr2d 4_1_cts.odb (then check OT_CLOCK_TAPS GROUPS / OT_TAP_INSERTION clk_t20, ~11.3k sinks, target 450).
- Next on sdr2d GRT: census (R3 q12.sh / an.py / an2.py in epyc7 .../fable-fix-head-serdes-r3) -> if DRT-0255 recurs: local ECO
  of the boxed cell from 5_1_grt; if encoder still misses on logic: OT_S81_KP4_ENC_PPCYC (+1 TX ck, LATENCY post owed).

## Resume 03:4x PST (after Codex takeover 02:18-03:31; CODEX-LOG "HEAD lane handback 03:31")
- sdr2d original run (fable-fix-head-serdes-r3/sdr2d) ended at post-place PLACE-SETUP-STOP (-54999 ps, rrn_g -> rpq,
  false stop, fixed on main eda19506a55). Codex continued as sdr2d_cts_ideal: clk_t20 group 11,321 sinks skew 28.4 ps,
  CTS TT -45.88 -> +38.83 after repair, pre-GRT hold +5.00.
- WAIT sdr2d GRT: epyc9 /srv/opentallas-scratch2/claude/fable-fix-head-serdes-r3/sdr2d_cts_ideal/hd_serdes,
  unit oth-ubuntu-2994936-1795258763, hub ~/head-plan-r16/sdr2d_grt.otrun.log. Before any DRT: south coll_i0 access +
  congestion review (bins/guide scripts in epyc7 .../opus-fix-head-serdes-r4).
- WAIT hd_host_e GRT (taken from Codex): epyc8 /srv/opentallas-scratch2/claude/opus-fix-head-serdes-r4/host_e_ideal1121/hd_host_e,
  unit oth-ubuntu-3218685-1795260164, hub ~/head-plan-r16/host_e_ideal_grt.otrun.log. Before DRT: east 4.32-um macro aisle +
  southern EPC feedthrough check.
- Draft claude/head-start-reach-export-1121 (epyc10 R3 repo, uncommitted reach_rules.py + test): real r16 reach report
  running (base vs draft, rules 5) epyc10 .../opus-fix-head-serdes-r4/reach/{base,draft}.{log,json,tsv}.

## 04:1x PST (COORD corrections: visual/access reviews never block; FLOW-GRT-RESID snap; plan owner now OPUS-FIX-HEAD-LEP0N-R3)
- Chains on intel2 ~/opus-fix-head-serdes-r4-logs: chain_sdr2d.sh (pid 4140767) and chain_hoste.sh (pid 4140766) ot-wait the GRT
  unit, then launch route (goal route) on the same kit; logs chain_*.log, sdr2d_route_e9.otrun.log, host_e_route.otrun.log.
  Reviews (south coll_i0 access; east aisle / south EPC ft) run in parallel, never hold the route.
- A/B sdr2e (epyc7 /srv/opentallas-scratch2/claude/opus-fix-head-serdes-r4/sdr2e/gen): cp -a of sdr2c kit from 4_cts, 5_* moved
  to hd_serdes/pre-ab; PRE_GLOBAL_ROUTE override -> resnap_pre_grt.tcl (OT_RESERVED_SNAP 42fa174c180 lattice applied in the DB
  to reserved_sites obstructions on M3-M9, then grt_pre_nonport.tcl). Goal route, ot-run log sdr2e_route_e7.otrun.log (queued on epyc7 memory).
  Purpose: DRT-0255 proof only (sdr2c GRT TT was -103, not a sign-off candidate).
- Rows sent to OPUS-FIX-HEAD-LEP0N-R3: START reset relay stages hd_st_k5 rr_t54 (1676 um) and hd_st_m rr_t8 (1261 um) to <= 405 um.
