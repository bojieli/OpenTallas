# KV-KITS lane (qwen_kvsys die re-bind + partition-type kits)

## 10-27 03:40 PDT KV-KITS-1 result
- Branch claude/kv-kits-1-1027@d0a1b4a326 (base batch-r2@2a130d7df6). die_plan := hm_r12 sha 1814a2d8 (slice@18c72cf920). Pieces: pvcal restore re-derived for the approved +1 station (4 members, landed=as-built, +0 cyc) fa89531f58; main taps.py/schema.py overlay d0a1b4a326 (batch B31 tap rules gave 20 vs plan 8 clk taps on band types -> port_bind FAIL).
- Strict re-bind b51 (intel2:/srv/opentallas-scratch2/claude/kv-kits-1-1027/b51) CHECKED own logs: 160 parts/51 types/2545 crossings/430554 bits; errors 0 unbound 0 tied 0 undriven 0 multi 0; PV calendar 944 PASS +0; R8 3813 groups 0 unequal; die taps 1920 (= CLOCK-KV mesh).
- die_port_bind (bind.py portbind wrapper passes NO strap file): input_unconnected 0, undriven 0, multi 0, port_not_in_rtl 0, width 0; input_tied 412 = exactly the 412 declared parent ID straps (strap_head*_e*_strap_{bsel,hid}, strap_astk_*_corner; CHECKED count match). output_open_ports 25 on kv3_hg/hgi_v1/v2/v4/v7 + kv3_pc/pc_v1/pc_v3 = UNRESOLVED (names not printed). Rerun with --strap-file b51_straps.json RUNNING unit oth-ubuntu-1955697-1793097526 -> collect b51/portbind_straps.log + port_bind_strict.txt. bind.py verify RUNNING oth-ubuntu-1592185-1793097279 -> collect b51/verify.log.
- NOT in this bind: 8-region landings (hm_r12 has 0 landed seams, ruling 9.9 + continuous mesh) -> ASK; KVSCTL-3 kvs_ctl port changes not landed yet -> re-bind owed when they land.
- Kits gen51 (gen.py phys, --kit-rtl from b51, gen worktree = slice branch). Place = ./run_kit.sh T place (pre-floorplan gates incl. synth LEC + face_guard). HB4 hold-demand types (COORD 03:3x): kv3_pc_v1, kv3_hgi_v7, kv3_hgi_v4, kv3_phy_v1 ordered FIRST, NOT built until CLOCK-KV-R21 posts demand (REQ in KV-CORES.md); kv3_phy_v1 is a hard PHY-macro type (no P&R kit) -> R21 demand for it must land in the PHY-macro view / neighbour glue, flag to R21.

| family | type | n | state (CHECKED unless marked) |
|---|---|---|---|
| kv3_hg | kv3_hg | 4 |  |
| kv3_hg | kv3_hg_v1 | 4 |  |
| kv3_hg | kv3_hg_v3 | 4 |  |
| kv3_hgi | kv3_hgi | 2 |  |
| kv3_hgi | kv3_hgi_v1 | 12 |  |
| kv3_hgi | kv3_hgi_v2 | 2 |  |
| kv3_hgi | kv3_hgi_v3 | 1 |  |
| kv3_hgi | kv3_hgi_v4 | 6 |  |
| kv3_hgi | kv3_hgi_v5 | 1 |  |
| kv3_hgi | kv3_hgi_v6 | 1 |  |
| kv3_hgi | kv3_hgi_v7 | 6 |  |
| kv3_hgi | kv3_hgi_v8 | 1 |  |
| kv3_hroot | kv3_hroot | 4 |  |
| kv3_hub_C | kv3_hub_C | 1 |  |
| kv3_hub_Ei | kv3_hub_Ei | 1 |  |
| kv3_hub_Eo | kv3_hub_Eo | 1 |  |
| kv3_hub_Wi | kv3_hub_Wi | 1 |  |
| kv3_hub_Wo | kv3_hub_Wo | 1 |  |
| kv3_io_cor | kv3_io_cor | 1 |  |
| kv3_io_cor | kv3_io_cor_v1 | 1 |  |
| kv3_io_ft | kv3_io_ft | 1 |  |
| kv3_io_ft | kv3_io_ft_v1 | 1 |  |
| kv3_pc | kv3_pc | 4 |  |
| kv3_pc | kv3_pc_v1 | 24 |  |
| kv3_pc | kv3_pc_v3 | 4 |  |
| kv3_phy | kv3_phy | 4 |  |
| kv3_phy | kv3_phy_v1 | 28 |  |
| kv3_pv | kv3_pv | 1 |  |
| kv3_pv | kv3_pv_v1 | 1 |  |
| kv3_pv | kv3_pv_v12 | 1 |  |
| kv3_pv | kv3_pv_v2 | 1 |  |
| kv3_pv | kv3_pv_v3 | 1 |  |
| kv3_pv | kv3_pv_v4 | 1 |  |
| kv3_pv | kv3_pv_v5 | 1 |  |
| kv3_pv | kv3_pv_v6 | 1 |  |
| kv3_pv | kv3_pv_v7 | 1 |  |
| kv3_pv | kv3_pv_v8 | 1 |  |
| kv3_sys_SD | kv3_sys_SD | 1 |  |
| kv3_sys_SD | kv3_sys_SD_v1 | 1 |  |
| kv3_sys_c | kv3_sys_c | 1 |  |
- skipped composite variants (bound by master+strap, type-reduce): kv3_pv_v1n kv3_pv_v2n kv3_pv_v3n kv3_pv_v4n kv3_pv_v5n kv3_pv_v6n kv3_hg_v1p2 kv3_hg_v1p3 kv3_hg_v1p4 kv3_hg_v1p5 kv3_hg_v1p6
- Placed (CHECKED: 3_place.odb + render viewed): kv3_io_ft, kv3_io_ft_v1, kv3_io_cor, kv3_io_cor_v1 -> GEOM REQ posted; route/sign-off only after GEOM PASS. kv3_hub_Ei still in GPL (intel1 oth-ubuntu-1817373-1793096335) -> collect gen51/kv3_hub_Ei/kv3_hub_Ei/run (intel1), render with kv-kits-1-1027/{dump.tcl,rend.py}.
- Signed off: NONE. READY-view lines: none yet.
- Blockers (root cause): (1) kv3_hroot LEC KEEP FAIL: qkd_ctrl_strip (* keep *) rs_q in u_esh.u_st is a duplicate of u_kc.rs_q (same D=rsi) -> yosys merges, netlist has BUFx2 u_kc.rs_q->u_esh.u_st.rs_q; fix = keep_hierarchy/dont-merge on the strap reset pin flop or drop the keep (RTL owner, small). (2) kv3_sys_SD/_v1 synth_odb ORD-2013: $paramod ot_qfd_serdes_112g_x6_phy (W) has no LEF master; fix codex/native-bb-1026@1b8a62a4f not on main -> ROOT-MERGE. (3) kv3_sys_c rtl_lint: rtl/lib/ot_rst_pipe.sv:49 genblock ref g_p[..].q[t] implicitly declared (COPIES>1, d2d_sfm RCP=12) -> RTL/RESET owner. (4) core views: head_eighth/ectlk/ahub/kvs_ctl/astk/qkd_hr_*/kvs_pc/pv_pair/pv_join unsigned (KV-CORES). (5) pending deltas: CLOCK-KV-R19/R21 early taps (hg/hgi), hub_Wi PHY-clock landed crossing.
