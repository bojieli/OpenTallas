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
