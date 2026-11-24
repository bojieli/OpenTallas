# QC-OPEN-COLL handoff (FAMILY lane under QC-ALLFIX; split from QC-ALLFIX-COLL 11-23 19:24 PST)
Job: coll_core rows of lanes/ALLFIX-QC.tsv: (1) coll_core 80 CLK-open reset copies (tools row main 32027184aff), (2) rc107 g_pf W hotspot, (3) rc109 shr_p_rx_i setup -97. All three are read from ONE coll_core GRT probe.
- Coll types byte-identical C4 = compose A f418c1b290f3 = C1b 62ce8aba0292 (checked partition_types, placement, 126 ports, 56 lanes, latency, tap_offset): epyc7 QC-ALLFIX-COLL/rows/colldiff_open.py. So ROW-REBASED onto C1b = no plan delta, PRE = C1b PRE.
- Probe: intel2 ~/coord/autopilot/private_specs/QC-OPEN-COLL/qwen_compute_coll_core_1123193232 (run-item pid 3805534 on intel2, launched 19:4x, OT_BIND_RT=0), gen epyc8 on cA tree+bind, hosts [epyc11], tools_rt c66090747375, goal grt.
  private-spec --rt c660 refused by hash guard (reset_tree.py vs bind rt 7f184148a02e; diff = OT_REPO_ROOT path only), so tools_rt patched in spec; semantic toolskew replay at run-item decides.
- GRT read to do: CLK-open count (expect 0), 5_1_grt.odb setup/hold, u_rrl_26 23-copy D net (-521 pre-repair at CTS), g_pf W hotspot, shr_p_rx_i path; full-cause census fe8a2a5.

## 20:0x PST
- Attempt 1 (1123193232): kit_topology FAIL: coll_core io_collective__fault or_groups[0].regs_um != row regs_um (26.622 vs 16.2). Plan bug in C4/A/C1b.
- Row ORGRP-SYNC: epyc7/epyc8 QC-OPEN-COLL/rows/orgrp_row.py; C1b 62ce8aba0292 -> 7f750a9a8e6e, A f418 -> 1e0c326f08ec. PRE on C1b+row = base (1 inherited ROWS). Posted ROW-REBASED.
- Attempt 2 (1123194440): bare plan copy failed gen (plan-relative feed/regions). Attempt 3 (1123200325, pid 497287 intel2): private fork epyc8 QC-OPEN-COLL/treeA + ORGRP plan, bind cA (--allow-bind-stale), c660, hosts epyc11.
- Killed stale coll_ftc V2 waiter pid 589366 on epyc8 (kit dead since 11-22 04:49).

## 23:50 PST
- Probe alive: epyc8 coll_core_1123200311, GRT stage, pregrt_ff_hold.tcl 72 min (PID 3404293, single thread). CTS db: 0 of 83795 DFF CLK-open; 206 copies, 206 clocked, 0 same-xy. GRT script: epyc8 QC-OPEN-COLL/grtread (clkopen.tcl, clones.tcl, cts.sh; mount the kit results dir read-only, run by ot-run).
- Not a gate: spec tools_rt/hosts set by hand, --allow-bind-stale; plan 1e0c has no strict bind. Semantic toolskew OK.
- C1e b6211ae9de47 still lacks ORGRP-SYNC (posted ACTION to QC-ALLFIX); applied cleanly = fdfd6e012c39.
- G0 C1b = C1b+row: FAIL 3, su_c types only. Next: read 5_1_grt.odb setup/hold/CLK-open + full-cause census fe8a2a5, incl rc107 g_pf hotspot and rc109 shr_p_rx_i.

## 11-24 00:3x PST
- OWNERS-SWEEP: claimed none of the 8 st_a rows; cbf_q00_s2 not mine (asked COORD to name QC-ALLFIX or QC-V4). Matcher ruling relayed to QC-CB-PROBE (acked).
- C1g 96cce77c1e2f contains ORGRP-SYNC. GRT waiter = ot-wait PID 1838076 epyc8 (6 h).
- CTS setup census: 9 fails; -201 warm[4]->g_xf[0].red_in, -124 g_xf[0].e_out->xe0_q (~420 um). Scripts epyc8 QC-OPEN-COLL/grtread/sta.sh <4_cts|5_1_grt>, sta_wp.sh. Candidate: move g_xf[0] or +1 stage each way; not built.
- Seats: 4/49748 unmatched, 1 station missing unexplained.
