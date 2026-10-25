# PROTO (virtual prototyping sweep, 2026-10-24 evening; rtx-pro coordinator lane agent)
Branch claude/proto-1024r (worktree rtx-pro:/home/ubuntu/wt/proto-1024r, base origin/main a11334b98). Fleet data: <host>:/srv/opentallas-scratch2/claude/proto/ (ot-run --dir, spills).
Goal: prove every partition type without a SIGNED view is routable / roughly meets timing BEFORE detailed route (no DRT).
Method (tools/die_plan/proto_sweep.py + proto_render.py, on the branch): the G2 partition probe (g2.part_probe: exact
outline + plan pins, one boundary flop per pin bit, ft station flops at regs_um / along the route, hard cores + leaves as
placement blockages + M1..obs_max OBS) + one ideal clock on every flop + plan IO budget 0.2 T + 60/25 ps uncertainty +
repair_design + GRT M2..top with the partition's own logic as capacity adjust 0.5 + STA on GRT RC (TT setup / FF hold).
SKELETON prototype: partition logic not synthesised (B2m and the KV v4 bind have no bound RTL; hard-core views mostly
unrouted), so STA covers the plan wires only (pin->reg, ft hops, repeater pitch). Classes: CLEAN / HOTSPOT / STRUCTURAL.
## Log
2026-10-24 21:48 PDT PROTO: started. Pilot (4 probes: B2m q_b000/q_su00, KV kv3_hg, QC sle_hc0) running via ot-run; then batches HBM B2m -> KV -> QC -> head -> S81.
2026-10-24 22:14 PDT PROTO: tool db96f4053 + fixes (all hard cores blocked, platform RC, repeaters -max_wire_length 450, GRT 3 congestion rounds). Two restarts: g2 left KV/QC/S81 cores unblocked; tech LEF has no RC (zero wire C). sweep3 LIVE: 281 partition probes (B2m 44, KV 44, QC 51, head 15, S81 127) via launcher epyc1:/srv/opentallas-scratch2/claude/proto/launch.sh pid 982359 (ot-run --dir, MAXJ 70), dirs <host>:/srv/opentallas-scratch2/claude/proto/sweep3/<die>/part_<type>. SKIPPED (lane live / geom FAIL): KV hub_Ei, io_cor_v1, io_ft_v1; QC coll_ftc, tt_ctlm; head hd_tile; S81 col_* x12 (g3k5 FAIL), slice_station x34 (ELEM-S81); hard types (q_sm*, PHY_N, kv3_phy*, phy_serdes*, phy_ucie_kv, phy__t1).
2026-10-24 22:14 PDT PROTO: HBM idle hard cores (placed by ELEM-HBM, never routed, no lane live) -> GRT + placement-RC STA TT/FF on copies <host>:/srv/opentallas-scratch2/claude/proto-cores/<kit>: group_rel_id, wb_kport_q, pdie_serdes (epyc3), idx_qctl, cxport_ij_q, qw_dec (intel1). Already known: dma_back_static_vp4_banks_cp MPL-0065 (cells do not fit beside the macros), su_programme_pslice_c5 DPL crash, vms_glue_nw_t GPL exit 245. idx_qctl: CTS RSZ-0060 max buffer count.

## RESULTS 2026-10-25 00:10 PDT (claude/proto-1024r@260719247; plans = origin/main a11334b98, unchanged on main since)
2026-10-25 00:10 PDT PROTO: sweep3 done for 276/281 types (5 HBM B2m types still in GRT congestion rounds = heavy overflow; table marks them). Renders + per-type JSON: claude/proto-1024r results/proto_1024/<die>/<type>.png, results/proto_1024/<die>.json, full tables results/proto_1024/TABLES.md.
METHOD (skeleton = what the plan alone fixes): exact outline + plan pins, a register on every pin bit, ft stations at plan regs_um (or g2's default straight in->out sites when the plan gives none), every hard core as placement blockage + M1-M5 obstruction, ideal clock 833 ps, IO 0.2T, 60/25 ps uncertainty, platform setRC, repair_design -max_wire_length 450 (repeaters), GRT (adjust 0.5, 3 congestion rounds), STA on GRT RC TT setup / FF hold. Partition logic NOT synthesised (B2m/KV have no bound RTL) -> a CLEAN skeleton is necessary, not sufficient.
CAUSES (what makes a type STRUCTURAL):
 (H) ft hop > 405 um: a station-to-station (or pin-to-station) leg longer than decision 12 allows; the plan has too few stations / too far apart. Timing tracks it (paths 500-870 um fail TT by 50-280 ps even with 450-um repeaters).
 (C) default station sites inside hard cores: slot has no regs_um, g2's straight in->out sites land on cores (S81 leaves/svc, QC cbf/cbn/su, KV hgi_v6-8/hub_C/hub_Wi) -> stations pile at core edges -> overflow. Plan must give station sites in channels (S81/LEAFPLAN v4 internal_stations already does this, not on main).
 (O) channel overflow: ft bundles over/around cores have only M6/M7 (M1-M5 OBS under cores, M8/M9 reserved): HBM q_b*/q_su*/q_spt0, KV hgi*/pv/pv_v2/v4/v6/v8, QC cbf_q01_s2/cbn_q01/su_l0/l1, S81 leaf t8/t18/t28/t58/t62/t67/t72 overflow 1e4-2e6; extreme TT (-400..-1735 ps) on these is detour wire from that congestion.

### HBM B2m: 44 types: CLEAN 5, NOT RUN 5, STRUCTURAL 34 (renders results/proto_1024/hbm_b2m/<type>.png)
| type (n) | class | GRT ov | TT/FF WNS ps | max ft hop um | main cause |
|---|---|---|---|---|---|
| q_b000 (2) | STRUCTURAL | 395502 | -1012.7/132.46 | 864 | 6 ft slots hop>405 (L4x3,L4x11) |
| q_b001 (2) | STRUCTURAL | 494793 | -419.68/132.44 | 864 | 7 ft slots hop>405 (L4x4,L4x10) |
| q_b002 (2) | STRUCTURAL | 83248 | -93.58/98.66 | 766 | 3 ft slots hop>405 (L64x3,L80x2); overflow on L4x9,L4x5 @[0, 117, 707, 528] |
| q_b003 (2) | STRUCTURAL | 123845 | -115.21/94.73 | 762 | 5 ft slots hop>405 (L64x4,L124x1); overflow on L4x8,L4x6 @[0, 115, 717, 529] |
| q_b010 (2) | STRUCTURAL | 718495 | -193.27/132.45 | 717 | 6 ft slots hop>405 (L116x3,L119x3); overflow on L12x4,L13x4 @[108, 370, 707, 1030] |
| q_b011 (2) | STRUCTURAL | 5797 | -221.77/132.44 | 863 | 5 ft slots hop>405 (L22x7,L13x3); overflow on L13x3,L12x3 @[2, 93, 707, 994] |
| q_b012 (2) | STRUCTURAL | 32050 | -703.52/97.48 | 825 | 4 ft slots hop>405 (L13x2,L12x2) |
| q_b013 (2) | STRUCTURAL | 759679 | -813.51/132.49 | 714 | 3 ft slots hop>405 (L13x1,L12x1); overflow on L12x1,L13x1 @[0, 0, 716, 880] |
| q_b100 (2) | STRUCTURAL | 393417 | -274.07/132.46 | 864 | 4 ft slots hop>405 (L4x1,L4x13) |
| q_b101 (2) | STRUCTURAL | 1504136 | -257.78/132.46 | 864 | 5 ft slots hop>405 (L4x2,L4x12); overflow on L19x1 @[0, 80, 708, 2073] |
| q_b102 (2) | STRUCTURAL | 1365332 | -316.19/37.8 | 824 | 9 ft slots hop>405 (L12x6,L119x1); overflow on L13x6,L22x10 @[0, 32, 704, 937] |
| q_b103 (2) | STRUCTURAL | 1417303 | -315.15/125.7 | 836 | 7 ft slots hop>405 (L19x2,L13x5); overflow on L22x9 @[0, 0, 702, 777] |
| q_b110 (2) | STRUCTURAL | 2258948 | -257.5/2.76 | 793 | 17 ft slots hop>405 (L52x2,L33x1); overflow on L38x1,L33x1 @[0, 0, 1659, 993] |
| q_b111 (2) | STRUCTURAL | 2122237 | -257.84/79.93 | 762 | 10 ft slots hop>405 (L52x1,L102x2); overflow on L38x2,L59x1 @[134, 0, 1219, 68] |
| q_b113 (2) | STRUCTURAL | 130885 | -1735.04/132.46 | 853 | 4 ft slots hop>405 (L36x2,L55x1); overflow on L36x2,L55x1 @[0, 0, 1198, 2035] |
| q_hub (2) | STRUCTURAL | 0 | 68.97/132.46 | 728 | 1 ft slots hop>405 (L56x2) |
| q_mcb (2) | STRUCTURAL | 0 | -208.62/132.43 | 864 | 3 ft slots hop>405 (L9x5,L8x5) |
| q_spb1 (2) | STRUCTURAL | 0 | 25.55/132.47 | 754 | 2 ft slots hop>405 (L117x1,L138x1) |
| q_spb2 (2) | STRUCTURAL | 816 | 2.86/132.45 | 748 | 6 ft slots hop>405 (L138x2,L117x2); overflow on L35x2 @[66, 135, 1798, 1502] |
| q_spt0 (2) | STRUCTURAL | 356393 | -144.8/132.43 | 747 | 6 ft slots hop>405 (L66x2,L79x2); overflow on L9x2,L8x2 @[104, 0, 726, 1503] |
| q_spt1 (2) | STRUCTURAL | 0 | -56.75/132.42 | 754 | 6 ft slots hop>405 (L8x3,L21x3) |
| q_spt2 (2) | STRUCTURAL | 0 | -73.56/132.42 | 768 | 6 ft slots hop>405 (L82x1,L79x4) |
| q_spu0 (2) | STRUCTURAL | 0 | -194.11/132.43 | 878 | 20 ft slots hop>405 (L9x1,L31x3) |
| q_spu1 (2) | STRUCTURAL | 0 | -172.59/132.43 | 866 | 32 ft slots hop>405 (L62x3,L49x1) |
| q_su00 (2) | STRUCTURAL | 3403 | -245.32/132.49 | 774 | 2 ft slots hop>405 (L48x1,L53x5); overflow on L53x5,L48x1 @[294, 0, 2554, 48] |
| q_su11 (2) | STRUCTURAL | 43288 | -131.36/132.44 | 748 | 4 ft slots hop>405 (L140x3,L53x1); overflow on L48x5,L53x1 @[258, 0, 1576, 293] |
| q_su20 (2) | STRUCTURAL | 0 | -48.38/90.22 | 725 | 2 ft slots hop>405 (L125x1,L106x5) |
| q_su21 (2) | STRUCTURAL | 494060 | -710.12/132.44 | 768 | 12 ft slots hop>405 (L44x1,L99x2); overflow on L32x1,L33x2 @[0, 0, 2020, 1543] |
| q_su31 (2) | STRUCTURAL | 484148 | -190.22/50.26 | 763 | 22 ft slots hop>405 (L73x3,L65x3); overflow on L42x3,L63x3 @[0, 3, 1470, 1534] |
| vsN1 (1) | STRUCTURAL | 0 | 25.55/132.47 | 754 | 2 ft slots hop>405 (L118x1,L141x1) |
| vsN2 (1) | STRUCTURAL | 0 | 25.17/132.46 | 754 | 2 ft slots hop>405 (L118x2,L141x2) |
| vsN4 (1) | STRUCTURAL | 0 | -56.76/132.42 | 754 | 6 ft slots hop>405 (L22x3,L114mx3) |
| vsN5 (1) | STRUCTURAL | 0 | -56.76/132.42 | 754 | 6 ft slots hop>405 (L22x2,L114mx2) |
| vsN6 (1) | STRUCTURAL | 0 | -207.52/132.43 | 872 | 6 ft slots hop>405 (L22mx1,L22x1) |
| q_b112 (2) | NOT RUN | - | -/- | 786 | GRT still in congestion iterations (heavy overflow) |
| q_su01 (2) | NOT RUN | - | -/- | 824 | GRT still in congestion iterations (heavy overflow) |
| q_su10 (2) | NOT RUN | - | -/- | 862 | GRT still in congestion iterations (heavy overflow) |
| q_su30 (2) | NOT RUN | - | -/- | 781 | GRT still in congestion iterations (heavy overflow) |
| root (1) | NOT RUN | - | -/- | 757 | GRT still in congestion iterations (heavy overflow) |
CLEAN: NE_io NW_io q_mca q_spb0 vsN0

### KV (qwen_kvsys): 44 types: CLEAN 3, STRUCTURAL 41 (renders results/proto_1024/kv/<type>.png)
| type (n) | class | GRT ov | TT/FF WNS ps | max ft hop um | main cause |
|---|---|---|---|---|---|
| kv3_hg (4) | STRUCTURAL | 14 | -123.17/132.45 | 694 | 3 ft slots hop>405 (ft2,ft0); overflow on ft2 @[116, 326, 128, 336] |
| kv3_hg_v1_r1 (4) | STRUCTURAL | 16 | -168.98/132.44 | 694 | 4 ft slots hop>405 (ft3,ft1); overflow on ft3 @[116, 330, 460, 337] |
| kv3_hg_v1_r2 (4) | STRUCTURAL | 16 | -168.98/132.44 | 694 | 4 ft slots hop>405 (ft3,ft1); overflow on ft3 @[116, 330, 460, 337] |
| kv3_hg_v1_r3 (4) | STRUCTURAL | 16 | -168.98/132.44 | 694 | 4 ft slots hop>405 (ft3,ft1); overflow on ft3 @[116, 330, 460, 337] |
| kv3_hg_v1_r4 (4) | STRUCTURAL | 16 | -168.98/132.44 | 694 | 4 ft slots hop>405 (ft3,ft1); overflow on ft3 @[116, 330, 460, 337] |
| kv3_hg_v1_r5 (4) | STRUCTURAL | 16 | -168.98/132.44 | 694 | 4 ft slots hop>405 (ft3,ft1); overflow on ft3 @[116, 330, 460, 337] |
| kv3_hg_v2 (4) | STRUCTURAL | 16 | -168.98/132.44 | 694 | 4 ft slots hop>405 (ft3,ft1); overflow on ft3 @[116, 330, 460, 337] |
| kv3_hg_v3 (4) | STRUCTURAL | 1 | -207.48/132.44 | 720 | 4 ft slots hop>405 (ft3,ft1) |
| kv3_hgi (2) | STRUCTURAL | 366999 | -252.6/132.45 | 733 | 7 ft slots hop>405 (ft6,ft4); overflow on ft4,ft6 @[0, 54, 1193, 887] |
| kv3_hgi_v1 (12) | STRUCTURAL | 350985 | -215.9/132.45 | 733 | 3 ft slots hop>405 (ft2,ft0); overflow on ft2 @[0, 56, 872, 479] |
| kv3_hgi_v2 (2) | STRUCTURAL | 301851 | -310.75/132.45 | 734 | 4 ft slots hop>405 (ft3,ft2); overflow on ft3 @[0, 113, 1188, 530] |
| kv3_hgi_v3 (1) | STRUCTURAL | 545420 | -280.88/132.44 | 733 | 29 ft slots hop>405 (ft27,ft4); overflow on ft4,ft27 @[0, 3, 1193, 1091] |
| kv3_hgi_v4 (6) | STRUCTURAL | 523962 | -312.06/132.44 | 733 | 25 ft slots hop>405 (ft23,ft0); overflow on ft23,ft24 @[0, 0, 872, 1092] |
| kv3_hgi_v5 (1) | STRUCTURAL | 557390 | -396.62/132.44 | 734 | 26 ft slots hop>405 (ft24,ft23); overflow on ft23,ft24 @[0, 0, 1185, 1192] |
| kv3_hgi_v6 (1) | STRUCTURAL | 683487 | -301.77/132.44 | 733 | 994 default station sites inside cores; 29 ft slots hop>405 (ft29,ft4); overflow on ft29,ft4 @[0, 0, 1188, 1201] |
| kv3_hgi_v7 (6) | STRUCTURAL | 654868 | -283.37/132.44 | 733 | 994 default station sites inside cores; 25 ft slots hop>405 (ft25,ft0); overflow on ft25,ft23 @[0, 0, 872, 1196] |
| kv3_hgi_v8 (1) | STRUCTURAL | 594208 | -308.45/48.99 | 734 | 994 default station sites inside cores; 26 ft slots hop>405 (ft26,ft25); overflow on ft26,ft25 @[0, 0, 1190, 1201] |
| kv3_hroot (4) | STRUCTURAL | 0 | 94.5/132.44 | 595 | 14 ft slots hop>405 (ft5,ft4) |
| kv3_hub_C (1) | STRUCTURAL | 235 | -1275.52/132.45 | 737 | 776 default station sites inside cores; 30 ft slots hop>405 (ft15,ft14) |
| kv3_hub_Eo (1) | STRUCTURAL | 25 | -58.41/132.44 | 724 | 28 ft slots hop>405 (ft25,ft1); overflow on ft30 @[630, 946, 651, 957] |
| kv3_hub_Wi (1) | STRUCTURAL | 80671 | -648.27/56.17 | 855 | 993 default station sites inside cores; 32 ft slots hop>405 (ft6,ft4); overflow on ft25,ft24 @[90, 423, 1132, 1080] |
| kv3_hub_Wo (1) | STRUCTURAL | 13 | -54.87/132.44 | 724 | 28 ft slots hop>405 (ft31,ft10); overflow on ft2 @[629, 948, 631, 957] |
| kv3_io_cor (1) | STRUCTURAL | 0 | 2.25/132.44 | 641 | 19 ft slots hop>405 (ft0,ft7) |
| kv3_io_ft (1) | STRUCTURAL | 0 | 28.73/132.46 | 641 | 4 ft slots hop>405 (ft0,ft1) |
| kv3_pc_v1 (20) | STRUCTURAL | 0 | 204.82/132.45 | 539 | 2 ft slots hop>405 (ft0,ft1) |
| kv3_pc_v2 (4) | STRUCTURAL | 0 | 204.82/132.45 | 539 | 2 ft slots hop>405 (ft0,ft1) |
| kv3_pc_v3 (4) | STRUCTURAL | 0 | 209.94/132.44 | 543 | 2 ft slots hop>405 (ft0,ft1) |
| kv3_pv (1) | STRUCTURAL | 347129 | -172.98/132.45 | 730 | 6 ft slots hop>405 (ft0,ft1); overflow on ft0,ft5 @[1, 0, 1899, 1304] |
| kv3_pv_v1 (1) | STRUCTURAL | 0 | 278.57/132.44 | 524 | 9 ft slots hop>405 (ft5,ft6) |
| kv3_pv_v10 (1) | STRUCTURAL | 0 | 157.94/132.44 | 525 | 25 ft slots hop>405 (ft23,ft24) |
| kv3_pv_v11 (1) | STRUCTURAL | 0 | 156.64/132.44 | 525 | 41 ft slots hop>405 (ft24,ft25) |
| kv3_pv_v12 (1) | STRUCTURAL | 0 | 154.25/132.44 | 603 | 58 ft slots hop>405 (ft26,ft25) |
| kv3_pv_v2 (2) | STRUCTURAL | 451944 | -234.5/132.44 | 733 | 27 ft slots hop>405 (ft7,ft0); overflow on ft0,ft26 @[0, 0, 1900, 1304] |
| kv3_pv_v3 (1) | STRUCTURAL | 0 | 157.94/132.44 | 525 | 25 ft slots hop>405 (ft23,ft24) |
| kv3_pv_v4 (2) | STRUCTURAL | 260600 | -197.5/132.44 | 713 | 43 ft slots hop>405 (ft8,ft6); overflow on ft0,ft42 @[0, 0, 1900, 1304] |
| kv3_pv_v5 (1) | STRUCTURAL | 0 | 156.64/132.44 | 525 | 41 ft slots hop>405 (ft24,ft25) |
| kv3_pv_v6 (2) | STRUCTURAL | 429792 | -273.38/132.44 | 728 | 59 ft slots hop>405 (ft7,ft5); overflow on ft0,ft58 @[0, 0, 1900, 1304] |
| kv3_pv_v7 (1) | STRUCTURAL | 0 | 152.18/132.44 | 577 | 57 ft slots hop>405 (ft5,ft6) |
| kv3_pv_v8 (1) | STRUCTURAL | 347129 | -172.98/132.45 | 730 | 6 ft slots hop>405 (ft0,ft1); overflow on ft0,ft5 @[1, 0, 1899, 1304] |
| kv3_pv_v9 (1) | STRUCTURAL | 0 | 278.57/132.44 | 524 | 9 ft slots hop>405 (ft5,ft6) |
| kv3_sys_c (1) | STRUCTURAL | 0 | 8.7/132.46 | 670 | 1 ft slots hop>405 (ft1) |
CLEAN: kv3_pc kv3_sys_SD kv3_sys_SD_v1

### QC (qwen_compute capacity plan): 51 types: CLEAN 8, STRUCTURAL 43 (renders results/proto_1024/qc/<type>.png)
| type (n) | class | GRT ov | TT/FF WNS ps | max ft hop um | main cause |
|---|---|---|---|---|---|
| cbf_q00_s2 (1) | STRUCTURAL | 1083 | -448.54/132.44 | 672 | 3004 default station sites inside cores; 5 ft slots hop>405 (tx_up_serdes_up,serdes_tx_valid_tx_v); overflow on rx_flit_serdes_rx @[57, 939, 549, 2307] |
| cbf_q01 (23) | STRUCTURAL | 17 | -93.4/132.49 | 608 | 1030 default station sites inside cores; 1 ft slots hop>405 (a00); overflow on a00 @[81, 274, 82, 1147] |
| cbf_q01_s2 (1) | STRUCTURAL | 316561 | -604.48/132.44 | 700 | 4292 default station sites inside cores; 6 ft slots hop>405 (rx_flit_serdes_rx,rx_v_serdes_rx_valid); overflow on rx_flit_serdes_rx,serdes_tx_tx_flit @[51, 69, 426, 2100] |
| cbn_q00 (24) | STRUCTURAL | 22 | -256.74/132.44 | 675 | 1030 default station sites inside cores; 1 ft slots hop>405 (rsf) |
| cbn_q01 (24) | STRUCTURAL | 152909 | -435.17/132.44 | 677 | 2060 default station sites inside cores; 2 ft slots hop>405 (rsf,a00); overflow on a00 @[54, 69, 256, 1231] |
| coll_core (1) | STRUCTURAL | 0 | 163.57/132.46 | 529 | 1 ft slots hop>405 (shared_fault_io_shared_fault) |
| coll_ft (3) | STRUCTURAL | 0 | 189.12/132.44 | 497 | 6 ft slots hop>405 (crec_rx_s1,crec_rx_s2) |
| coll_ftm (1) | STRUCTURAL | 0 | 25.33/132.45 | 675 | 19 ft slots hop>405 (crec_tx_s0,crec_rx_s0) |
| coll_ftn (1) | STRUCTURAL | 0 | 11.69/132.44 | 687 | 4 ft slots hop>405 (crec_tx_s0,crec_rx_s0) |
| native59 (1) | STRUCTURAL | 0 | 99.79/132.44 | 602 | 21 ft slots hop>405 (fltt,cal_program_obs_seq_program_obs) |
| sle_ctl (12) | STRUCTURAL | 0 | -31.4/132.45 | 730 | 6 ft slots hop>405 (x_st_b_fe,cws2) |
| sle_fe_v1 (3) | STRUCTURAL | 0 | 151.21/132.44 | 540 | 6 ft slots hop>405 (cws3,rsf) |
| sle_fe_v2 (2) | STRUCTURAL | 0 | 151.21/132.44 | 540 | 5 ft slots hop>405 (cws3,rsf) |
| sle_fe_v3 (1) | STRUCTURAL | 0 | 151.21/132.44 | 540 | 5 ft slots hop>405 (cws3,rsf) |
| sle_fw_v1 (3) | STRUCTURAL | 0 | 79.73/132.44 | 617 | 3 ft slots hop>405 (x_su_l1_ctl,x_su_l1_stm) |
| sle_fw_v2 (3) | STRUCTURAL | 0 | 80.11/132.44 | 617 | 4 ft slots hop>405 (x_su_l1_ctl,x_su_l1_stm) |
| sle_hc0 (6) | STRUCTURAL | 0 | -4.89/132.45 | 711 | 3 ft slots hop>405 (rsn,rsf) |
| sle_hc1 (6) | STRUCTURAL | 0 | 124.22/132.46 | 556 | 1 ft slots hop>405 (x_hc0_ctl) |
| sle_hc2 (6) | STRUCTURAL | 0 | 64.77/132.46 | 611 | 1 ft slots hop>405 (x_hc1_st_a) |
| sle_hc3 (6) | STRUCTURAL | 0 | 83.6/132.46 | 555 | 1 ft slots hop>405 (x_hc1_st_a) |
| sle_sc (6) | STRUCTURAL | 0 | 44.43/132.44 | 627 | 8 ft slots hop>405 (x_fe_stm,l9_eo_l9_wi) |
| sle_st_a (6) | STRUCTURAL | 0 | 8.39/132.45 | 678 | 3 ft slots hop>405 (cws3,x_ctl_fw) |
| sle_st_b (6) | STRUCTURAL | 0 | -118.95/132.44 | 846 | 5 ft slots hop>405 (b_hw_ctl_hc0,cws0) |
| sle_stm (6) | STRUCTURAL | 0 | -41.12/132.44 | 737 | 7 ft slots hop>405 (x_su_c_ctl,cws1) |
| sle_su_c (6) | STRUCTURAL | 3519 | -208.52/132.44 | 644 | 627 default station sites inside cores; 8 ft slots hop>405 (x_su_l0_stm,rsf); overflow on rsf @[20, 33, 1200, 431] |
| sle_su_l0 (6) | STRUCTURAL | 38828 | -56.25/132.44 | 585 | 4 ft slots hop>405 (rsn,rsf) |
| sle_su_l1 (6) | STRUCTURAL | 25563 | -35.28/132.44 | 710 | 751 default station sites inside cores; 4 ft slots hop>405 (x_ctl_fw,cws0) |
| slw_fe_v1 (3) | STRUCTURAL | 0 | -28.28/132.44 | 713 | 5 ft slots hop>405 (x_su_l0_sc,cws3) |
| slw_fe_v2 (3) | STRUCTURAL | 0 | -28.28/132.44 | 713 | 5 ft slots hop>405 (x_su_l0_sc,cws3) |
| slw_fw_v1 (3) | STRUCTURAL | 0 | 79.65/132.44 | 617 | 3 ft slots hop>405 (x_su_l1_ctl,x_su_l1_stm) |
| slw_fw_v2 (2) | STRUCTURAL | 0 | 79.65/132.44 | 617 | 3 ft slots hop>405 (x_su_l1_ctl,x_su_l1_stm) |
| slw_fw_v3 (1) | STRUCTURAL | 0 | 79.65/132.44 | 617 | 3 ft slots hop>405 (x_su_l1_ctl,x_su_l1_stm) |
| slw_hc0 (6) | STRUCTURAL | 0 | -4.89/132.45 | 711 | 3 ft slots hop>405 (rsn,rsf) |
| slw_hc1 (6) | STRUCTURAL | 0 | 124.22/132.46 | 556 | 1 ft slots hop>405 (x_hc0_ctl) |
| slw_hc2 (6) | STRUCTURAL | 0 | 64.77/132.46 | 611 | 1 ft slots hop>405 (x_hc1_st_a) |
| slw_hc3 (6) | STRUCTURAL | 0 | 83.6/132.46 | 555 | 1 ft slots hop>405 (x_hc1_st_a) |
| slw_sc (6) | STRUCTURAL | 0 | 42.4/132.44 | 627 | 7 ft slots hop>405 (x_fe_stm,x_fe_fw) |
| slw_st_a (6) | STRUCTURAL | 0 | 8.39/132.45 | 678 | 3 ft slots hop>405 (cws3,x_ctl_fw) |
| slw_st_b (6) | STRUCTURAL | 0 | -118.95/132.44 | 846 | 5 ft slots hop>405 (b_hw_ctl_hc0,cws0) |
| slw_stm (6) | STRUCTURAL | 0 | -39.7/132.45 | 737 | 6 ft slots hop>405 (x_su_c_ctl,cws1) |
| slw_su_c (6) | STRUCTURAL | 3519 | -208.52/132.44 | 644 | 627 default station sites inside cores; 8 ft slots hop>405 (x_su_l0_stm,rsf); overflow on rsf @[20, 33, 1200, 431] |
| slw_su_l0 (6) | STRUCTURAL | 38828 | -56.25/132.44 | 585 | 4 ft slots hop>405 (rsn,rsf) |
| slw_su_l1 (6) | STRUCTURAL | 25563 | -35.28/132.44 | 710 | 751 default station sites inside cores; 4 ft slots hop>405 (x_ctl_fw,cws0) |
CLEAN: cbf_q00 cbf_q11 cbn_q11 cbx_q10 coll_n coll_s coll_ucie glue

### S81 head: 15 types: CLEAN 15 (renders results/proto_1024/head/<type>.png)
| type (n) | class | GRT ov | TT/FF WNS ps | max ft hop um | main cause |
|---|---|---|---|---|---|
CLEAN: hd_ctl hd_host hd_lep0N hd_mesh hd_serdes hd_spn hd_spn_end hd_st_k5 hd_st_m hd_st_n3 hd_st_n4 hd_st_str hd_st_turn hd_turn_a hd_turn_b

### S81: 127 types: CLEAN 31, STRUCTURAL 96 (renders results/proto_1024/s81/<type>.png)
| type (n) | class | GRT ov | TT/FF WNS ps | max ft hop um | main cause |
|---|---|---|---|---|---|
| dsdv_slice_c1x_C__t1 (1) | STRUCTURAL | 0 | 82.84/132.44 | 613 | 1 ft slots hop>405 (ft0) |
| dsdv_slice_c1x_C__t2 (1) | STRUCTURAL | 0 | -81.67/132.44 | 613 | 3 ft slots hop>405 (ft0,ft1) |
| dsdv_slice_c1x_C__t3 (1) | STRUCTURAL | 0 | 46.57/132.48 | 725 | 1 ft slots hop>405 (ft0) |
| dsdv_slice_c1x_C__t4 (1) | STRUCTURAL | 0 | 56.24/132.44 | 650 | 1 ft slots hop>405 (ft0) |
| dsdv_slice_c1x_C__t5 (1) | STRUCTURAL | 0 | -46.45/132.44 | 613 | 2 ft slots hop>405 (ft0,ft1) |
| dsdv_slice_c1x_C__t6 (1) | STRUCTURAL | 0 | -49.79/132.47 | 721 | 3 ft slots hop>405 (ft0,ft2) |
| dsdv_slice_c1x_C__t8 (1) | STRUCTURAL | 5 | -448.26/132.44 | 721 | 6 ft slots hop>405 (ft0,ft5) |
| dsdv_slice_c1x_C__t9 (1) | STRUCTURAL | 18 | -376.93/132.44 | 613 | 3 ft slots hop>405 (ft0,ft1) |
| dsdv_slice_c3x_C__t1 (1) | STRUCTURAL | 0 | -49.79/132.46 | 721 | 2 ft slots hop>405 (ft1,ft0) |
| dsdv_slice_iq_C__t1 (1) | STRUCTURAL | 0 | -439.22/132.44 | 694 | 4 ft slots hop>405 (ft0,ft1) |
| dsdv_slice_kv512_C__t1 (1) | STRUCTURAL | 0 | -41.51/132.44 | 613 | 4 ft slots hop>405 (ft1,ft2) |
| dsdv_slice_lepe_mu_C__t1 (1) | STRUCTURAL | 0 | 37.9/132.48 | 662 | 1 ft slots hop>405 (ft0) |
| dsdv_slice_lepe_nh_mus_C__t1 (1) | STRUCTURAL | 0 | -264.87/132.44 | 615 | 2 ft slots hop>405 (ft1,ft0) |
| dsdv_slice_lepw_mus_C__t1 (1) | STRUCTURAL | 0 | 58.61/132.44 | 613 | 1 ft slots hop>405 (ft0) |
| eng__t1 (1) | STRUCTURAL | 1911 | 24.35/114.6 | 353 | 3069 default station sites inside cores; overflow on ft0 @[1025, 432, 1384, 1055] |
| ot_s81sl_leaf__t1 (1) | STRUCTURAL | 1405 | -136.44/78.27 | 361 | 5368 default station sites inside cores; overflow on ft5 @[304, 225, 496, 978] |
| ot_s81sl_leaf__t10 (1) | STRUCTURAL | 1230 | -60.53/78.18 | 307 | 4062 default station sites inside cores; overflow on ft7 @[307, 242, 351, 598] |
| ot_s81sl_leaf__t11 (1) | STRUCTURAL | 0 | 184.47/132.25 | 361 | 461 default station sites inside cores |
| ot_s81sl_leaf__t12 (1) | STRUCTURAL | 29 | -24.52/104.8 | 361 | 4245 default station sites inside cores |
| ot_s81sl_leaf__t13 (1) | STRUCTURAL | 6 | -93.46/99.3 | 307 | 4244 default station sites inside cores |
| ot_s81sl_leaf__t14 (1) | STRUCTURAL | 13408 | -227.48/77.22 | 378 | 6018 default station sites inside cores; overflow on ft4,ft0 @[133, 7, 1132, 589] |
| ot_s81sl_leaf__t15 (1) | STRUCTURAL | 0 | 219.87/113.18 | 307 | 1254 default station sites inside cores |
| ot_s81sl_leaf__t16 (1) | STRUCTURAL | 374 | 54.44/119.9 | 381 | 2123 default station sites inside cores; overflow on ft2 @[143, 520, 307, 978] |
| ot_s81sl_leaf__t17 (1) | STRUCTURAL | 526 | -178.88/110.0 | 307 | 5261 default station sites inside cores; overflow on ft4 @[412, 605, 449, 961] |
| ot_s81sl_leaf__t18 (1) | STRUCTURAL | 94381 | -349.56/90.46 | 361 | 10391 default station sites inside cores; overflow on ft1,ft8 @[166, 195, 1000, 691] |
| ot_s81sl_leaf__t19 (1) | STRUCTURAL | 928 | -89.9/79.2 | 307 | 3571 default station sites inside cores; overflow on ft5 @[307, 270, 349, 598] |
| ot_s81sl_leaf__t2 (1) | STRUCTURAL | 3201 | -261.17/106.79 | 307 | 5469 default station sites inside cores; overflow on ft1,ft2 @[347, 285, 779, 969] |
| ot_s81sl_leaf__t20 (1) | STRUCTURAL | 11 | 213.17/111.63 | 307 | 2679 default station sites inside cores |
| ot_s81sl_leaf__t21 (1) | STRUCTURAL | 2054 | 148.92/119.23 | 368 | 3134 default station sites inside cores; overflow on ft3 @[151, 498, 408, 901] |
| ot_s81sl_leaf__t22 (1) | STRUCTURAL | 5147 | -253.01/110.34 | 307 | 4596 default station sites inside cores; overflow on ft1,ft7 @[347, 285, 779, 952] |
| ot_s81sl_leaf__t23 (1) | STRUCTURAL | 13286 | -211.63/103.03 | 361 | 4915 default station sites inside cores; overflow on ft7,ft6 @[307, 115, 1054, 978] |
| ot_s81sl_leaf__t24 (1) | STRUCTURAL | 4948 | 158.73/101.07 | 307 | 3685 default station sites inside cores; overflow on ft4 @[303, 251, 365, 606] |
| ot_s81sl_leaf__t25 (1) | STRUCTURAL | 0 | 242.44/115.22 | 307 | 1848 default station sites inside cores |
| ot_s81sl_leaf__t26 (1) | STRUCTURAL | 0 | 186.88/113.26 | 361 | 1913 default station sites inside cores |
| ot_s81sl_leaf__t27 (1) | STRUCTURAL | 311 | 186.16/92.47 | 307 | 3996 default station sites inside cores; overflow on ft1 @[341, 296, 372, 996] |
| ot_s81sl_leaf__t28 (1) | STRUCTURAL | 491233 | -271.01/57.45 | 326 | 15380 default station sites inside cores; overflow on ft0,ft1 @[122, 20, 882, 778] |
| ot_s81sl_leaf__t29 (1) | STRUCTURAL | 31 | 7.07/109.22 | 307 | 2417 default station sites inside cores; overflow on ft2 @[163, 317, 182, 322] |
| ot_s81sl_leaf__t3 (1) | STRUCTURAL | 26618 | -224.82/88.62 | 361 | 5516 default station sites inside cores; overflow on ft0,ft1 @[195, 86, 1103, 831] |
| ot_s81sl_leaf__t30 (1) | STRUCTURAL | 0 | 240.59/126.46 | 307 | 423 default station sites inside cores |
| ot_s81sl_leaf__t31 (1) | STRUCTURAL | 887 | -29.33/79.61 | 384 | 3991 default station sites inside cores; overflow on ft2 @[310, 622, 362, 978] |
| ot_s81sl_leaf__t32 (1) | STRUCTURAL | 5214 | -249.23/109.71 | 307 | 4397 default station sites inside cores; overflow on ft2,ft4 @[347, 399, 781, 969] |
| ot_s81sl_leaf__t33 (1) | STRUCTURAL | 8837 | -149.92/92.54 | 325 | 5474 default station sites inside cores; overflow on ft6 @[278, 99, 813, 546] |
| ot_s81sl_leaf__t34 (1) | STRUCTURAL | 663 | -65.3/79.1 | 307 | 3560 default station sites inside cores; overflow on ft5 @[303, 242, 362, 598] |
| ot_s81sl_leaf__t35 (1) | STRUCTURAL | 4 | 217.92/111.41 | 307 | 2652 default station sites inside cores |
| ot_s81sl_leaf__t36 (1) | STRUCTURAL | 314 | -163.22/99.72 | 361 | 2031 default station sites inside cores; overflow on ft9,ft8 @[309, 317, 324, 465] |
| ot_s81sl_leaf__t37 (1) | STRUCTURAL | 0 | 213.06/110.15 | 307 | 3199 default station sites inside cores |
| ot_s81sl_leaf__t38 (1) | STRUCTURAL | 1410 | -235.6/110.13 | 307 | 3796 default station sites inside cores |
| ot_s81sl_leaf__t39 (1) | STRUCTURAL | 378 | 123.87/64.54 | 364 | 3795 default station sites inside cores; overflow on ft3 @[271, 209, 347, 554] |
| ot_s81sl_leaf__t4 (1) | STRUCTURAL | 149 | 220.85/109.96 | 307 | 2221 default station sites inside cores; overflow on ft5 @[315, 354, 338, 468] |
| ot_s81sl_leaf__t40 (2) | STRUCTURAL | 0 | 189.13/113.18 | 307 | 1254 default station sites inside cores |
| ot_s81sl_leaf__t41 (1) | STRUCTURAL | 0 | 195.58/82.57 | 362 | 2457 default station sites inside cores |
| ot_s81sl_leaf__t42 (1) | STRUCTURAL | 3030 | -151.94/109.92 | 307 | 3916 default station sites inside cores; overflow on ft1,ft4 @[347, 318, 769, 952] |
| ot_s81sl_leaf__t43 (1) | STRUCTURAL | 2641 | -221.56/105.28 | 307 | 3617 default station sites inside cores; overflow on ft4,ft5 @[307, 78, 724, 635] |
| ot_s81sl_leaf__t44 (1) | STRUCTURAL | 205 | 234.41/110.15 | 307 | 2138 default station sites inside cores |
| ot_s81sl_leaf__t45 (1) | STRUCTURAL | 118 | -204.02/64.21 | 337 | 4136 default station sites inside cores; overflow on ft2 @[335, 657, 384, 822] |
| ot_s81sl_leaf__t46 (1) | STRUCTURAL | 10284 | -260.72/93.72 | 307 | 4757 default station sites inside cores; overflow on ft2,ft3 @[386, 639, 800, 996] |
| ot_s81sl_leaf__t47 (1) | STRUCTURAL | 3415 | -187.27/105.82 | 361 | 4708 default station sites inside cores; overflow on ft5,ft6 @[207, 52, 876, 978] |
| ot_s81sl_leaf__t48 (1) | STRUCTURAL | 206 | 234.41/109.96 | 307 | 2138 default station sites inside cores |
| ot_s81sl_leaf__t49 (1) | STRUCTURAL | 0 | 193.15/113.18 | 307 | 1254 default station sites inside cores |
| ot_s81sl_leaf__t5 (1) | STRUCTURAL | 0 | 182.83/113.18 | 307 | 1272 default station sites inside cores |
| ot_s81sl_leaf__t50 (1) | STRUCTURAL | 0 | 185.31/126.63 | 361 | 1281 default station sites inside cores |
| ot_s81sl_leaf__t51 (1) | STRUCTURAL | 0 | 203.62/111.02 | 307 | 3149 default station sites inside cores |
| ot_s81sl_leaf__t52 (1) | STRUCTURAL | 43498 | 134.46/69.62 | 350 | 3780 default station sites inside cores; overflow on ft5,ft4 @[354, 43, 765, 348] |
| ot_s81sl_leaf__t53 (1) | STRUCTURAL | 700 | 149.81/111.7 | 307 | 3157 default station sites inside cores |
| ot_s81sl_leaf__t55 (1) | STRUCTURAL | 92 | 122.09/111.48 | 361 | 2957 default station sites inside cores; overflow on ft5,ft7 @[147, 416, 307, 685] |
| ot_s81sl_leaf__t56 (1) | STRUCTURAL | 2384 | -253.83/79.84 | 361 | 5042 default station sites inside cores; overflow on ft9,ft3 @[294, 251, 693, 978] |
| ot_s81sl_leaf__t57 (1) | STRUCTURAL | 1304 | -141.24/103.89 | 307 | 3885 default station sites inside cores; overflow on ft3,ft8 @[389, 613, 799, 1063] |
| ot_s81sl_leaf__t58 (1) | STRUCTURAL | 109242 | -89.33/71.2 | 376 | 6861 default station sites inside cores; overflow on ft7,ft0 @[61, 139, 710, 562] |
| ot_s81sl_leaf__t59 (1) | STRUCTURAL | 12 | 236.1/111.23 | 307 | 2679 default station sites inside cores |
| ot_s81sl_leaf__t6 (1) | STRUCTURAL | 0 | 186.88/96.52 | 361 | 2472 default station sites inside cores |
| ot_s81sl_leaf__t60 (1) | STRUCTURAL | 12623 | 147.28/82.92 | 368 | 3908 default station sites inside cores; overflow on ft2,ft7 @[88, 503, 416, 1142] |
| ot_s81sl_leaf__t61 (1) | STRUCTURAL | 4922 | -197.13/110.33 | 307 | 4417 default station sites inside cores; overflow on ft9,ft1 @[347, 285, 777, 969] |
| ot_s81sl_leaf__t62 (1) | STRUCTURAL | 120147 | -263.16/103.01 | 361 | 7017 default station sites inside cores; overflow on ft1,ft8 @[156, 78, 1056, 849] |
| ot_s81sl_leaf__t63 (1) | STRUCTURAL | 5299 | 132.69/101.07 | 307 | 3685 default station sites inside cores; overflow on ft4 @[208, 251, 367, 607] |
| ot_s81sl_leaf__t64 (1) | STRUCTURAL | 0 | 221.62/117.16 | 307 | 1848 default station sites inside cores |
| ot_s81sl_leaf__t65 (1) | STRUCTURAL | 878 | -218.14/93.89 | 361 | 4362 default station sites inside cores; overflow on ft4 @[378, 354, 478, 909] |
| ot_s81sl_leaf__t66 (1) | STRUCTURAL | 1641 | -173.97/98.56 | 307 | 3943 default station sites inside cores; overflow on ft2,ft10 @[388, 613, 796, 1063] |
| ot_s81sl_leaf__t67 (1) | STRUCTURAL | 124913 | -265.79/102.66 | 361 | 7092 default station sites inside cores; overflow on ft1,ft9 @[293, 52, 1054, 864] |
| ot_s81sl_leaf__t68 (1) | STRUCTURAL | 8824 | 60.48/102.0 | 307 | 3601 default station sites inside cores; overflow on ft3,ft5 @[300, 251, 375, 607] |
| ot_s81sl_leaf__t69 (1) | STRUCTURAL | 0 | 240.54/113.31 | 307 | 1866 default station sites inside cores |
| ot_s81sl_leaf__t7 (1) | STRUCTURAL | 3 | 199.97/111.59 | 307 | 3821 default station sites inside cores; overflow on ft1 @[362, 313, 371, 917] |
| ot_s81sl_leaf__t70 (1) | STRUCTURAL | 6 | 162.66/109.29 | 361 | 2147 default station sites inside cores |
| ot_s81sl_leaf__t71 (1) | STRUCTURAL | 1028 | 133.75/91.72 | 307 | 4095 default station sites inside cores; overflow on ft3,ft5 @[331, 302, 383, 996] |
| ot_s81sl_leaf__t72 (1) | STRUCTURAL | 168453 | -278.27/75.75 | 361 | 12417 default station sites inside cores; overflow on ft1,ft0 @[468, 9, 1261, 558] |
| ot_s81sl_leaf__t73 (1) | STRUCTURAL | 956 | -229.07/94.61 | 307 | 3460 default station sites inside cores; overflow on ft8 @[388, 242, 796, 600] |
| ot_s81sl_leaf__t74 (1) | STRUCTURAL | 980 | -52.3/78.11 | 307 | 4062 default station sites inside cores; overflow on ft7 @[307, 277, 360, 598] |
| ot_s81sl_leaf__t8 (1) | STRUCTURAL | 168463 | -282.2/77.79 | 361 | 12417 default station sites inside cores; overflow on ft1,ft0 @[510, 9, 1262, 558] |
| ot_s81sl_leaf__t9 (1) | STRUCTURAL | 1054 | -214.44/94.58 | 307 | 3460 default station sites inside cores; overflow on ft8 @[389, 242, 799, 602] |
| svc_hi_dsdv_svc_rs__t1 (1) | STRUCTURAL | 198 | 220.99/83.73 | 351 | 15623 default station sites inside cores; overflow on ft0,ft1 @[188, 428, 553, 2317] |
| svc_hi_dsdv_svc_rs__t3 (1) | STRUCTURAL | 0 | 163.5/132.48 | 361 | 1978 default station sites inside cores |
| svc_hi_dsdv_svc_rs__t4 (1) | STRUCTURAL | 0 | 173.05/132.48 | 361 | 1978 default station sites inside cores |
| svc_hi_dsdv_svc_rs__t5 (1) | STRUCTURAL | 0 | 165.01/99.69 | 351 | 4402 default station sites inside cores |
| svc_hi_dsdv_svc_rs__t6 (1) | STRUCTURAL | 75 | 144.22/65.99 | 351 | 15957 default station sites inside cores; overflow on ft1,ft2 @[191, 465, 380, 2329] |
| svc_lo_dsdv_svc_rs__t6 (1) | STRUCTURAL | 0 | 193.84/76.69 | 335 | 5148 default station sites inside cores |
| svc_lo_dsdv_svc_rs__t7 (1) | STRUCTURAL | 0 | 158.59/77.2 | 355 | 3100 default station sites inside cores |
| svc_lo_dsdv_svc_rs_w__t1 (1) | STRUCTURAL | 0 | 267.46/96.32 | 313 | 2694 default station sites inside cores |
CLEAN: bk_col__t1 bk_sel__t1 dsdv_slice_c1x_C__t7 dsdv_slice_lepe_mu_LP__t1 dsdv_slice_lepe_nh_mus_LP__t1 dsdv_slice_lepw_mu_C__t1 dsdv_slice_lepw_mu_LP__t1 dsdv_slice_lepw_mus_LP__t1 gunit__t1 iqf__t1 ot_s81sl_kv_leaf__t1 ot_s81sl_kv_leaf__t2 ot_s81sl_kv_leaf__t3 ot_s81sl_kv_leaf__t4 ot_s81sl_kv_leaf__t5 ot_s81sl_leaf__t54 seqhost__t1 serdes__t1 serdes__t2 serdes__t3 serdes__t4 serdes__t5 serdes__t6 svc_hi_dsdv_svc_pvso_entry__t1 svc_hi_dsdv_svc_pvso_entry__t2 svc_hi_dsdv_svc_rs__t2 svc_lo_dsdv_svc_rs__t1 svc_lo_dsdv_svc_rs__t2 svc_lo_dsdv_svc_rs__t3 svc_lo_dsdv_svc_rs__t4 svc_lo_dsdv_svc_rs__t5

### HBM idle hard cores (ELEM-HBM kits, placed but never routed; copies at <host>:/srv/opentallas-scratch2/claude/proto-cores/<kit>; ORFS to GRT + STA TT/FF on 4_cts.odb, else 3_place.odb)
| core | host | furthest stage | GRT | TT setup / FF hold WNS ps | class | why |
|---|---|---|---|---|---|---|
| ot_hbm_svc_sm_group_rel_id | epyc3 | CTS done, GRT stopped at congestion round 11/30 | congested | -584.5 / -267.1 (post-CTS, GRT not done) | STRUCTURAL | CTS repair: WNS -5921 ps, setup skew 597 ps, 37k hold violators, 58k hold buffers; clock tree / reset (stream_rst_n -> u_hbm_reset pipe) structure, not tunable |
| ot_hbm_svc_wb_kport_q | epyc3 | CTS done, GRT stopped at congestion round 3/30 | congested | -217.6 / +30.7 | STRUCTURAL | CTS WNS -2288 -> -677 ps after repair; wd_q[*] fan-in; GRT needs congestion rounds |
| ot_pdie_serdes | epyc3 | GRT FAILED (GRT-0116) | overflow 254271 (M2 40% use, M2-M5 only) | -32.6 / -389.9 | STRUCTURAL | 385k nets on a M5-capped core: too dense for 4 routing layers -> more area or M6/M7 for the core |
| ot_hbm_idx_qctl_static | intel1 | CTS FAILED RSZ-0060 (max buffer count) | - | +124.1 / +25.7 (3_place, ideal clock) | STRUCTURAL | CTS buffer explosion = huge-fanout / high-skew clock structure |
| ot_hbm_su_static_cxport_ij_q | intel1 | CTS repair stopped after ~3 h (WNS -173 ps, +9% area) | - | +226.9 / -107.7 (3_place) | HOTSPOT | sf_q DFF_PN0 setup -173 at CTS; repairable-looking, hold needs CTS |
| ot_hgi_qw_dec | intel1 | CTS repair stopped after ~3 h (WNS -169 ps) | - | +419.1 / -123.2 (3_place) | HOTSPOT | i_x[*] input-register setup -169 at CTS |
Already known from ELEM-HBM's runs: dma_back_static_vp4_banks_cp MPL-0065 (cells do not fit beside macros: outline too small = STRUCTURAL); su_programme_pslice_c5 DPL crash (tool); hfd_hgi_vms_glue_nw_t GPL exit 245 after 1 h. KV/QC/S81 core candidates (qkd_pv_join, qfd_dv_s5_su8_rst3, s8x_crh, s8_crh_rp1, S81 dsdv_bk_g/gunit_l2/l4/cfg7_seq_bfp) NOT run this pass.
2026-10-25 00:46 PDT PROTO: HBM core runs stopped (exact container names) after recording: four of them were hours from GRT end, and their state already answers the question.

## PARKED 2026-10-25 00:47 PDT
- Branch: claude/proto-1024r@260719247 (tools/die_plan/proto_sweep.py gen/collect, proto_render.py, proto_report.py; results/proto_1024/{<die>.json,<die>/<type>.png,TABLES.md,SUMMARY.md}). Worktree /home/ubuntu/wt/proto-1024r.
- Live: 4 HBM B2m probes in GRT congestion round 3/3 (heavy overflow; expect STRUCTURAL (O)): epyc1:/srv/opentallas-scratch2/claude/proto/sweep3/hbm_b2m/part_{q_b112,q_su01,q_su10,root} (ot-run --dir; containers proto-part_q_b112-4018982 on epyc2, proto-part_{q_su01-2145360,q_su10-2130727,root-2164008} on intel1; launcher pid 982359 on epyc1 exits after them). All other run data deleted (renders + JSON kept on the branch); HBM core copies deleted.
- Results: head 15/15 CLEAN. B2m 5 CLEAN / 34 STRUCTURAL / 5 pending; KV 3 CLEAN / 41 STRUCTURAL; QC 8 CLEAN / 43 STRUCTURAL; S81 31 CLEAN / 96 STRUCTURAL. Dominant causes: ft legs > 405 um (decision 12) in almost every ft-carrying B2m/KV/QC type; S81 leaf/svc slots without station sites (default sites on cores; LEAFPLAN v4 internal_stations fixes on its branch); ft channel overflow over cores (M6/M7 only) in HBM q_b*/q_su*, KV hgi*/pv*, QC cbf/cbn/su, S81 big leaves. HBM cores: 5 STRUCTURAL, 2 HOTSPOT (table above).
- Next: when the 4 probes finish: rsync epyc1 .../sweep3/hbm_b2m/part_X (skip *.odb), proto_sweep.py collect, proto_report.py --src <gen dir> to add their rows; delete the dirs. Re-run the sweep on the regenerated reach405 plans (QC ft405c, KV crossings plan, S81 LEAFPLAN v4, HBM B2n) once they land on main: gen = proto_sweep.py gen PLAN --out DIR --all --skip <live types>, then ot-run per part dir (mem = 4 + 8*area_mm2 GB, cap 256).
- Limits: skeleton only (no partition logic: B2m/KV have no bound RTL); stations placed per bit at the planned point (wide bundles cluster -> local overflow overstated); GRT adjust 0.5.
- OWNER?: none.
2026-10-25 00:59 PDT PROTO: B2m late results: q_su10 STRUCTURAL (GRT overflow 3.03M, hot bbox 83% of outline, 16 ft slots hop > 405 um worst L37x4 862 um, TT -499 ps); root killed at its 85 GB cap during GRT congestion rounds (RSS 89 GB) = STRUCTURAL (O) by the same signature. Still live: q_b112 (epyc2), q_su01 (intel1). Dirs of q_su10/root deleted.
- 2026-10-25 01:51 PDT REQUEST from QC: sweep qwen_compute re-plan claude/qc-meth-1024@a281ceb5ce (READY, dec-17 batch) -- ft over core fields
  (su_l0/l1, su_c, cb*) against M6/M7 tracks; QC re-plans any type that is not CLEAN before kits.

## CODEX notes 2026-10-25 02:43 PDT
CODEX took over proto collection/re-sweep preparation. KV channel pilot owner /root/kv_push covers hgi_v6/pv_v6 baseline+proposal (skip duplicate). Wavefront rst_o outputs missing from g2 skeleton causes PPL-0061; KV g2-only fix a2a47e1d8 ready, adopting before current-plan sweeps.
