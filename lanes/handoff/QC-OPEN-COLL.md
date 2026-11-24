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

## 11-24 00:3x PST
- OWNERS-SWEEP: claimed none of the 8 st_a rows; cbf_q00_s2 not mine (asked COORD to name QC-ALLFIX or QC-V4). Relayed matcher ruling to QC-CB-PROBE (acked).
- C1g 96cce77c1e2f contains ORGRP-SYNC. GRT waiter = ot-wait PID 1838076 epyc8 (6 h).
- CTS setup census: 9 fails; -201 warm[4]->g_xf[0].red_in, -124 g_xf[0].e_out->xe0_q (~420 um). Scripts epyc8 QC-OPEN-COLL/grtread/sta.sh <4_cts|5_1_grt>, sta_wp.sh. Candidate: move g_xf[0] or +1 stage each way; not built.
- Seats: 4/49748 unmatched, 1 station missing unexplained.

## 11-24 01:20 PST (resumed after limit)
- Probe unit (spec qwen_compute_coll_core_1123200325, epyc8 a6fbadf5d121, openroad 3404293) is still in pregrt_ff_hold pass 2, using CPU. Not cancelled, per FABLE. The GRT waiter is ot-wait 1838076.
- Tap census at CTS (epyc8 QC-OPEN-COLL/grtread/tapgeo.ot, tapsinks.ot): 17 raw taps are slower than 285 ps.
  - Distance causes only t100 (205 far sinks at 762,1298), t99 (33 far at 692,1072) and t126 (26 far at 749,1522).
  - The rest have every sink within 230 um but are slow from depth and sink count (900-1000 sinks).
- Row TAP-SPLIT, ETA posted 01:20: draft + PRE 02:45, strict + LATCHECK 03:30, CTS replay 04:30. Build on C1g 96cce77c1e2f (strict passed).
  - Order: (1) taps: add taps and lower tap_max_sinks; (2) red_in launch tap; (3) xe0_q seat; (4) macro shift.

## 11-24 03:47 PST
- PROBE GRT landed 03:25 (epyc8 kit coll_core_1123200311). Reset copies are closed at GRT: 0 open of 83,795. Flow GRT metrics: setup -127.04/-10370 (172 ep), hold -122.8 (3 port_in ep), design violations 0. Census posted 03:35. Reads are in epyc8 QC-OPEN-COLL/grtread: sta_g*, sta_d*, sta_e*, sta_f*, locs*.
- Row 1 TAP-SPLIT = plan ee5985b3b659 (C1g + 117 added taps), in epyc2 /srv/opentallas-scratch3/claude/QC-OPEN-COLL/tapsplit/.
  - PRE: inherited ROWS-NO-PROOF only.
  - Strict bind is running: epyc2 cG/bindG.ot (unit oth-ubuntu-2428865-1795519500).
  - Tree: epyc2 scratch3 QC-OPEN-COLL/cG/tree, forked from C1g. Helpers: QC-OPEN-COLL/helpers (bind_cG.sh, bindrun_allfix.sh, rr).
- Rows 2-4: seats plan c22ba88a5fd4 (pf_q[374], xe0_q, warm[4]) in epyc2 rows/plan_tapsplit_seats.json. Strict runs after ee59.
- Row A: s_rd_q[35]/[36] replication. Waiting on the FABLE form ruling (asked 03:47).
- epyc7: ot-delete of the partial forks is running (pid 2192564).

## 11-24 05:25 PST
- ROW-READY posted for C1i. Plan 2007f2313324 = C1g + TAP-SPLIT + seats + TDREP replicas. RTL overlay is in epyc2 scratch3 QC-OPEN-COLL/rowA/overlay (ot_coll_tp8_static.sv 3065906f35b8).
  - Gates: strict 0 errors, LATCHECK 1922/1922 (cG2).
  - LEC pos 52859/52859 and neg failing on 2 bits, both on epyc10 scratch2 QC-OPEN-COLL/rowA_lec.
- TAP-SPLIT alone (ee5985b3b659) also passed strict (cG).
- Open: push the RTL to main, or have QC-ALLFIX carry it as an overlay (asked). Next: probe on 2007f2313324 and the 9-endpoint list at CTS/GRT.
- The epyc2 tree cG/tree now holds the row-A RTL plus plan 2007f2313324; cG2/tree is a symlink to it.
