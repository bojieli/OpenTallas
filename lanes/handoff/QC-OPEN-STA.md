# QC-OPEN-STA handoff (FAMILY lane under QC-ALLFIX; split from FAM-QC-HCST-R3 + QC-ALLFIX-COLL; updated 11-23 20:05 PST)

JOB: st_a re-floor row (all 11 st_a types) on C1b 62ce8aba0292; ROW-REBASED to QC-ALLFIX by 22:30; then one place/GRT probe on epyc11.
Also asked (QC-ALLFIX 19:26): rc97 parent row (BT_LAT 1->2 on u_r* region cores) -- depends on FAM-QC-HCST-R3 region harden (ETA 23:30-02:00).

Work dir: epyc8 /srv/opentallas-scratch2/claude/QC-OPEN-STA (rows/, rep/, tmp/). Base copy rows/plan_c1b.json (62ce8aba0292).
Tree fork for PRE/G0/probe: epyc11 /srv/opentallas-scratch2/claude/QC-OPEN-STA/tree (fork of kw45 snap qwen_compute_v4c4, started 19:46 from epyc8 ot-run, log epyc8 QC-OPEN-STA/fork_e11.ot).
Leftover to ot-delete: epyc8 QC-OPEN-STA/tree.forking-813798 (aborted fork, killed by me).

Pipeline (scripts in epyc8 rows/):
1. sta_floor.py macros: channels >= 10.8 (cl_rs_s1 -8.64, cl_b_hw_ctl_hc0_i/cl_b_tw_data_i -4.32, v2: cl_x_fw_ctl_i -4.32), btab SRAM stack -> y0 591.84; points on moved macros translate, others cleared. -> tmp/p1_macros.json
2. relay_chain.sh: type_relay_sites (rt 70b6) per type from its A-probe geom.tsv (10 of 11; cl67389ecd geom came later) -> rows/plan_sta_r1.json 8c5f546a95e1: 0 chains > 380 um, 0 pin cycles.
3. sta_ft.py: ft_sites.place per-bit sites for b_hw_ctl_hc* (550 bits > 405 in every probe), stations unchanged or rejected.
Residual (not placement): u_r0 -> g_btb writes 28 b (NEED-STATION, RTL: rc97 btab child), b_tw_data -> btab (REACH).

## 21:30 PST
- Final pipeline: epyc8 rows/pipe.sh (sta_floor macros on 8.64 lattice, SRAM y0 587.52 -> sta_ftbits b_hw_ctl per-bit sites -> relay_chain.sh (+firm) -> sta_clock span 290/chain 140, tap_radius kept) = plan_sta_r6 77d4fcb91680;
  then epyc7 rows/tapfix.sh (addtap --fix rename + retap OLD=C1b + tap_offset_cover fill) = plan_sta_r7; gate epyc7 gate_r7 (PRE + G0), log epyc8 QC-OPEN-STA/r7.ot.
- PRE history: r3 TAPNAME/TAPOFF (tap radius 140 + macro moves re-solve density base); r4 radius kept still TAPNAME -> tapfix. G0 r3 = base (3 su_c errors only), new WARN = G0C lattice (fixed in r6).
- Private tree: epyc7 /srv/opentallas-scratch2/claude/QC-OPEN-STA/tree + launch; A bind copy epyc7 and epyc11 QC-OPEN-STA/bindA/bind. Probe launcher intel2 /srv/opentallas-scratch2/claude/QC-OPEN-STA-probe.sh HOST ITEM.
- Leftovers to ot-delete: epyc8 QC-OPEN-STA/tree.forking-813798; epyc11 QC-OPEN-STA (bindA only, forks killed).
- rc97 parent draft: scratch rc97_parent.py (needs BT_LAT=2 views from FAM-QC-HCST-R3); only the 5 st_a_v2 types (20 u_r cores) carry BT_LAT.

## 23:08 PST
- ROW-REBASED final = plan_sta_r8 10630f5bd60c (epyc7 QC-OPEN-STA/rows/): r7 3a1e8e11bae0 + 161 slw_st_a_v2 x_fw_ctl ft sites cleared out of cl_b_hw_ctl_hc0_i (sta_floor clear no longer exempts ft/istation points inside cland bodies).
  PRE = base (1 ROWS), G0 FAIL 3 = base (su_c cws2), LAND-CAP OK. Posted 22:5x.
- Bind: bindR7 (my own r8_refresh) BAD: glue lane glue__mufl renamed -> bank_taps EMIT error; discarded. My refreshed table saved bindR7/r8_myrefresh.json.
  Tree runtime r8 table now = cA r8_final d5cb60490ce8. bindr8.sh -> bindR8/bind (log epyc8 QC-OPEN-STA/bindr8.ot).
- Next: on BIND_RC 0 run intel2 /srv/opentallas-scratch2/claude/QC-OPEN-STA-probe.sh (edit --bind-out to $D/bindR8/bind) epyc7 sle_st_a_v1__cl989804f6__cled3c1d7b; census at GRT (tap span, trees <=315, placed_scan, relay_collapse, channels).
- Deleted epyc8 tree.forking-813798 (ot-delete).

## 23:35 PST
- bindR7/bindR8 both BAD (tree lacked cC overlays). Tree now = cC overlays (bindS.sh installed 9 files from QC-ALLFIX/cC/tree); plan in tree = plan_probe_nosu 7e25fd64b4e4 (C1-noSU + st_a row, rows/compose_probe.py).
- bindS.sh -> bindS/bind (fresh elab + strict R8 loop + LATCHECK), log epyc8 QC-OPEN-STA/bindS.ot.
- Probe launcher intel2 /srv/opentallas-scratch2/claude/QC-OPEN-STA-probe.sh: set --bind-out $D/bindS/bind before running (rt 70b6).

## 23:55 PST (resumed)
- r8 on HOLD (posted): r_reach 34->42 is 8 new st_a findings (raw reset hops up to 1150 um, clfc START fan 569); cause unproven. G0 reads pre-re-pick names. Checking with rows/rreach.py (log epyc8 QC-OPEN-STA/rreach.ot).
- PRE/G0 r3..r8 ran on the bare kw45 tree: RERUN on the overlaid tree (now sha256-equal to cC in rtl/tools/runtime/bind). gate.sh installs its PLAN into tree: never run it while bindS is live.
- r6->r7 tapfix: dropped 6 added taps (cl67389ecd 1, cl18eece69 1, cled 1, clb036 1, clfc x2 1 each), tap_offset st_a rows 207 removed, 0 filled.
- Live: bindS unit oth-ubuntu-2693179-1795505578 (epyc7). tapfix.sh rm -f'd own zz_opensta_* temp plans in launch plan_of_record and tmp_r8.json in lane root (own files, but outside the tmp dir: use ot-delete there next time).

## 11-24 00:25 PST  (supersedes everything above on r8)
- COORD 00:1x: QC-OPEN-STA owns 8 DEAD-OWNER st_a rows (table posted). Order: re-floor row clears -> bind on C1g 96cce77c1e2f (epyc7 QC-ALLFIX/rows_c/c1g.json, strict running cF) -> probe the 8 on rt c660+ at goal grt.
- r1-r8 RETRACTED: SITEGRID FAIL 11/11 types, overlapping exact sites, relay_sites up to 149 flops on one point; raw reset hops up (post-re-pick result pending rep/rr_*.txt, unit oth-ubuntu-3593135-1795507956). bindS cancelled.
- r9: rows/legal.py on plan_sta_r6 -> plan_sta_r9a (log epyc8 QC-OPEN-STA/r9.ot) -> tapfix.sh -> r9 -> reset anchor/reach -> compose_probe.py onto C1g -> PRE c660 + G0 -> strict bind. Tapped-out checks: sitecheck.py, dups.py, site_grid.py, rreach.py.
- TAP_OFFSET: tapfix removes 207 st_a rows, fills 0: still open.

## 11-24 00:24 PST
- COORD: r9 = four numbers per type (SITEGRID 0, exact overlap 0, relays/point <=66, reset reach after re-pick) on 11 types with newest rt, BEFORE bind; compose on C1g only after its strict+LATCHECK (~01:20); probes on epyc10/epyc8, not epyc7/11.
- r8 re-pick measured on 4+ types: raw hops 0 after re-pick (stale names, same as C1b); rule 1 START fan on clfc not yet confirmed.
- Running: chain9.sh (local, scratch qcsta): r9a (epyc7 r9.ot) -> r9b.sh tapfix (launch7, rt 751410253108) -> plan_sta_r9 -> epyc10 gate9.sh (r9gate.py; log epyc8 QC-OPEN-STA/gate9.ot). Fork of kw45 snap to epyc10 QC-OPEN-STA/tree: unit oth-ubuntu-3569413-1795508582, log epyc8 fork10.ot. After C1g: copy cF overlay files to it.

## 11-24 00:33 PST
- r8 after re-pick, all 11 types: raw hops 0 on 9; clfc5867a6 x2 REAL regression (START fan 569, raw 550): sta_floor translate_with dragged START stages with the SRAM. r9a (809c36930236) has it too: superseded.
- r9u 13410b5bbd9e = undrag.py on r9a (START stages + >25 um collector_tree relays back to base; reset_tree_anchor fully restored on clfc x2 and clf4365a62; clf4365a62 26 tree relays nudged <=39 um). chain9.sh relaunched: r9u -> r9b.sh tapfix -> plan_sta_r9 -> epyc10 gate9.sh (r9, then C1b base). Logs epyc8 r9b.ot, gate9.ot.

## 11-24 01:12 PST
- r9 ffc276f9a6f9 GATE = base on all four (posted 01:1x): SITEGRID 0, overlap 0, relay/pt 66, reach after re-pick only fwd_source (= base; clfc +8 um). epyc8 rows/plan_sta_r9.json, rep/g9_r9 + g9_base.
- Composed on C1g 96cce77c1e2f: epyc8 rows/plan_c1g_sta.json a3043b36660b. NOT bound: waiting C1g strict + LATCHECK (QC-ALLFIX cF). Then: overlay epyc8 tree from cF/tree overlays (bindF.sh list: rows_f16/auth, rows_f16/comb, rows_b2/ov_red2, rows_b2/ov_r8, rows_c/ov_tools, + cF runtime r8) -> PRE (rt 7514) + G0 -> strict bind -> 8 probes at goal grt on epyc8/epyc10, rt >= c660.
- epyc8 tree = fresh kw45 snap fork (bare, no overlays yet); launch = rt 751410253108.

## 11-24 01:25 PST
- C1g strict PASS (QC-ALLFIX 01:15). r10 0104b4703368 = r9 + tap_offset rows re-keyed by site (rows/tapoff_rekey.py) + fill; composed on C1g = plan_c1g_sta10.json 3c17478ed804 (epyc7+epyc8 rows/).
- bindG.sh on epyc7 (log epyc8 QC-OPEN-STA/bindG.ot, out epyc7 QC-OPEN-STA/bindG/): sync tree to QC-ALLFIX/cF/tree by sha, PRE+G0 via launch7 (rt 7514), elab+strict+LATCHECK via launchG (rt c660).
- Then probes: the 8 DEAD-OWNER rows (+ cled3c1d7b, cl9f076a5c, clf4365a62) on epyc7 (tree there), goal grt, rt c66090747375 (bind rt), --bind-out QC-OPEN-STA/bindG/bind, --ab OT_TAP_ESCAPE_CLEAR_UM=0.30. Not epyc10.

## 11-24 03:08 PST
- Row plan_c1g_sta10 3c17478ed804 (r10 st_a on C1g 96cce77c1e2f). PRE rt 7514: row-only findings 0 (DEPTH x1 is base/QC-ALLFIX). G0 PASS 0/858.
- bindG.sh on epyc7 (log epyc8 QC-OPEN-STA/bindG.ot, out epyc7 QC-OPEN-STA/bindG/): strict bind + LATCHECK on rt c660 is running.
- Next: on BINDG_DONE clean, run probes of the 8 DEAD-OWNER rows + cled3c1d7b/cl9f076a5c/clf4365a62 on epyc7 at goal grt via intel2 QC-OPEN-STA-probe.sh (--bind-out bindG/bind, --rt c66090747375, OT_TAP_ESCAPE_CLEAR_UM=0.30).

## 11-24 03:3x sle_st_b_v2__clfde1249e (owned since 03:15)
- C4 kit epyc9 R6V4: GEOM BAD (GEOM-REVIEW c0614cc9); route stays held.
- C1g plan gate (rt 7514): SITEGRID 0, overlap 0, relays per point 1, reach findings 0. The plan gate does not catch the defect.
- Cause: internal_stations x_fe_o(257 bits, 3 regs), x_st_a_i(653, 4), x_hc1_i(517, 8) have NO bit_sites_um (exact sites). The placer collapses them (relay_collapse 11, r2r 492). x_st_a_i targets the r4/r5 cluster (326,444), but the worst capture is u_r7 (y~840).
- Row plan: give the 3 stations exact bank sites (kit_istations.py, as for st_a), split x_st_a_i toward r6/r7, re-check the 2 empty taps (t110, t127), legal.py + r9gate, into C1i. ETA row ~06:30.
