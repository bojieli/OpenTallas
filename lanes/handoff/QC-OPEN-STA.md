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
