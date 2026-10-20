#!/bin/bash
# QW-GEN3 10-19 = successor GEN of dv2f19g2 (claude/qw-gen3-1019): + 446 QW-DIECLK2 landings (OT_SPLIT_LAND_LIST) + R2 one hard instance per region root (OT_SPLIT_REGION_ONE_HARD, all hard<->hard direct buses landed) + DC_GRID_CENTER=1 + MU-DQ-BOOTCTX (mu_ctxrx -> tt_ctlm.ctx_x) + relay table = netlist walk vs the schedule recompiled on THIS die. STAND-INS declared in results/rtl/qw_gen3_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3c1)
# QW-GEN2 10-19 = successor GEN of dv2f18dh2: claude/qw-gen2-1019 a5ea12ae2 (mu-die-qw2 4d2cb6301 + qw-dieclk bbe250fb5 regional die clock + recompiled d2d_cal_image_mu.svh C[8,3,1,10]/K[21,4,3,3] + cp-not-ln). Carries e0218f16e, 3c133b609, QW-DIEFIX hr/ROM-bind/last-k. STAND-INS declared in results/rtl/qw_gen2_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3c1)
# MU-DIE-QW2 10-19 dv2f18dh2 = RELEASE MU die GEN: claude/mu-die-qw2-1019 0d4c9808f (TXDP C [8,3,1,10] 2308076af, qw-diefix, mu-qw-b1, slicekc kc[66:59], d2duser, mu-kv-ctx, MU-DQ-DHUSER observer dhobs d9bf2ed5e driving tt_ctlm.dh_user, sys_face MU=1 (57d2bf14c), d2d r9j view, 8 landh0 e1 CLOSED views, dhuser leaf k3 record). STAND-INS (labelled): tt_ctlm_dv kit (ctlm_dv clock 0ke), qfd_sys_face view (MU 0 rs3; mu1 re-close pending), slice2_e/wh (gated, not closed), native59 (n2c, multi-context MU-D2D-OVL), dhobs d1 (gated, critical). PILOT_NOT_A_GATE.
# MU-DQ-DHUSER 10-19 dv2f18dh = claude/mu-dq-dhuser-1019 (mu-die-qw2 94d5267da + dh_user observer mu_dhobs, COORD 0kg item 2): tt_ctlm.dh_user DRIVEN, no strap
# MU-DIE-QW 10-19 dv2f18mu (multi-user release die, OT_QWEN_MU_NU=4; stand-ins labelled; PILOT_NOT_A_GATE until views close) -- was Q17-PILOT: STAND-IN pilot of dv2f17 (PILOT_NOT_A_GATE) = dv2f16 + Q-RSTGEN7 e0218f16e + rlyh0 f1 views (main a66242c97) bound by name (OT_BIND_FWD_RLYH0=1, 598620d5a) + Q-RLYFCLK 3c133b609 (chain fclk payload contract)
# DIE-QWEN-GEN16 10-19 dv2f16: dv2f15r + claude/die-qwen-gen16-1019 (lane ck pins on owner roots, reset-rep column regions, co-root tt_ctlm/native59/embed_prov, QK-LANDEN landh0 +1, Q-CLK die clock tools)
# + Q-CB16RST qfd_c_b16_dv (16 regional resets, landed crossings; contract cluster_contract_dv_cb16rst_ac8e4c483.json, die_clock16_cb16rst.json)
# Q-DIE14 10-18 dv2f15next: claude/q-die14-1018 (main 4a4c0a958 + QLB-GEN 9634b2b0d G-C1 XPF/TXDP + QLB-PROG 3fac5f0ef STAGE_ME 1 + LB2-QWEN-C 2092dfebe) with the dv2f14bhd flags: CLOSED rst_rep 12.96x6.48 slot, landing channels D2D_DY 259.2 / SYSFACE_DX 129.6, LAND_CROSS d2d_rom,sys_face, LAND_PLAN = dv2f14bg chain land_plan.json
# dv2f14bhd = dv2f14bhc + CLOSED qfd_rst_rep/_p8 (OT_RST_REP_VIEW=closed, d5a922c32) + a9f90ad8f hold-budget tap fail-closed
# Q-DIE13 10-18 dv2f14bhd: dv2f14bg + landing channels (d2d_rom/ucie_kv/bumps +259.2 um N, sys_face +129.6 um E), LAND_CROSS on, LAND_PLAN from dv2f14bg chain
# LANDFIX-SQ 10-18 dv2f14bhd: dv2f14bn + claude/landfix-q-1018 (FDI + reset + pad-bump lanes forwarded; landing MCP = E_sta)
# Q-DIE11b 10-18 dv2f14b: exact tree HEAD (see SOURCE_COMMIT; = seam kept 129.6, f4862c038 + square landing frames OT_SPLIT_FWD_LAND_SHAPE=square + sys_face rs3 view frame + TT head h16c + cluster 2445.12 outline on 2462.4 pitch + 16 centre-fed regional clocks per cluster)
# Q-DIE11 10-18 dv2f14: exact tree f4862c038 (q-die11 = q-die10 + main + slice/cluster pin windows + tile grant _rr + forwarded half-cycle lanes/landings (rising hop 0, landing frames) + io_collective PHY face clocks). Was: dv2f12 plan
# W/E faces (M4) from the 17.28-um inter-cluster gaps) + cluster/slice abstracts obstruct M1-M8 only (OT_SPLIT_DV_OBS_TOP=8 OT_SPLIT_DV_SLICE_GAP_UM=${SGAP:-129.6} OT_SPLIT_DV_COLUMN_GAP_UM=86.4 OT_SPLIT_DV_SLICE_OBS_TOP=5 OT_SPLIT_DV_PIN_WINDOW_UM=9.6 OT_SPLIT_FWD_LANES=1;
# dv2f10 PDN-0006: die VDD M8 blocked by the M9 OBS).  Gates HARD (relay, per-bit reach 405).
# Q-DIEPLAN7 10-17 dv2f10: dv2f9 + d2d_rom / ucie_kv MX (closed qfd_d2d_static has M3+M5 vertical pins: no legal origin under MY/R180), links re-planned in GEN
# dv2f9 GEN (Q-DIEPLAN6 10-17): dv2f8 + re-ported W-column masters bound (native59 dv_service, tt_ctlm_dv, sys_face G8,
# embedding provider closed view) + seam chain lane (OT_SPLIT_DV_SEAM_LANE=1). Gates HARD (relay, per-bit reach 405).
# q3h model: OT_SPLIT_Q3H (q3h4 grid / CB contract) + OT_SPLIT_DV (Q-DV model). Reach 405 / per-bit 405 (owner 0cl),
# BFS budget 60k. $1 = "" FULL GEN -> ../out ; "skip" relay-skip smoke -> ../out_$TAG
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f19g3c1
cd $S/src || exit 9
D=results/arch/qwen_split_compute_1014
O=../out; L=../out.log; X=
[ "$1" = skip ] && { O=../out_${TAG:-skip}; L=../out_${TAG:-skip}.log; X="OT_RELAY_SKIP=1"; }
G=; [ "${GATE:-hard}" = warn ] && G="OT_RELAY_GATE=warn"
env $X $G OT_QWEN_MU_NU=${MU_NU:-4} OT_SPLIT_LAND_LIST=${LAND_LIST-$S/src/results/arch/qw_dieclk2_1019/landing_list.json} OT_SPLIT_REGION_ONE_HARD=${ONE_HARD:-1} OT_SPLIT_RESET_RELEASE=${RESET_RELEASE:?need source-pinned reset release projection JSON} OT_RST_REP_VIEW=closed OT_DIE_RELAY_STAGES_OUT=$S/out/relay_stages.json OT_DIE_RELAY_STAGES_PLAN_ID=dv2f19g3c1-qwgen3 OT_SPLIT_CK_COROOT=${CK_COROOT-tt_ctlm,native59,embed_prov} OT_TP8_SPLIT=compute OT_SPLIT_B2=1 OT_SPLIT_B2_PHYSICAL_TRIAL=1 OT_SPLIT_B2_COMPACT_SELECTOR=1 \
 OT_SPLIT_Q3H=1 OT_SU_VM_CHANNEL_UM=43.2 OT_SPLIT_Q3H_CONTRACT=$D/dieplan2_1016/q3h_cluster_contract_cb.json OT_SPLIT_Q3H_GRID=$D/dieplan2_1016/q3h4_grid.json OT_SPLIT_XCOL_WH=129.6,920.16 \
 OT_SPLIT_PHY_TALL=1 OT_SPLIT_DV_RSI_AT_RS=1 OT_RELAY_WORST_BIT=ordered OT_SPLIT_DV_SEAM_LANE=1 OT_SPLIT_DV_ORIENT=${D2D_ORIENT:-d2d_rom=MX,ucie_kv=MX} OT_SPLIT_DV_D2D_DX=${D2D_DX:-0} OT_SPLIT_DV_FACES=rtl/qwen_dv/qfd_dv_slice2_faces.json OT_SPLIT_DV=$D/dieplan2_1016/dv2r8f7r_qdv_p2462.json OT_SPLIT_DV_CLUSTER_CENTRE_CLOCKS=$D/dieplan2_1016/die_clock16_cb16rst.json OT_SPLIT_DV_CLUSTER_CLOCK_AT=${CLUSTER_CLOCK_AT:-face} OT_SPLIT_DV_CONTRACT=$D/dieplan2_1016/cluster_contract_dv_cb16rst_ac8e4c483.json OT_SPLIT_DV_OBS_TOP=8 OT_SPLIT_DV_SLICE_GAP_UM=${SGAP:-129.6} OT_SPLIT_DV_COLUMN_GAP_UM=86.4 OT_SPLIT_DV_SLICE_OBS_TOP=5 OT_SPLIT_DV_PIN_WINDOW_UM=9.6 OT_SPLIT_FWD_LANES=1 OT_SPLIT_FWD_LANES_FDI=1 OT_SPLIT_FWD_LANES_RST=1 OT_SPLIT_FWD_LANES_BUMP=1 OT_SPLIT_LAND_CROSS=${LAND_CROSS-d2d_rom,sys_face} OT_SPLIT_DV_D2D_DY=259.2 OT_SPLIT_DV_SYSFACE_DX=129.6 OT_SPLIT_LAND_PLAN=${LAND_PLAN-} OT_SPLIT_FWD_LAND_SHAPE=${LAND_SHAPE:-ns} \
 OT_PIN_BIT_REACH_UM=${BITREACH:-405} OT_RELAY_REACH_UM=${REACH:-405} OT_RELAY_REACH_OK=${REACH_OK:-395} OT_RELAY_BFS_MAX=${BFS:-60000} \
 OT_SPLIT_HOMES=$D/dieplan2_1016/q3h4-homes.json OT_SPLIT_HOMES_REBASE=1 OT_SPLIT_VM_WH=4872.024,3239.384 OT_SPLIT_PHY_NFACE=1 \
 OT_SPLIT_SYSFACE_XY=17921.52,13865.04 OT_SPLIT_TILE_GRANT=$D/dieplan2_1016/proxy_t1166_a0r_held_grant_rr.json \
 OT_SPLIT_PIN_GRANT=$D/dieplan2_1016/q2o2d_grant.json OT_SPLIT_BW_SPREAD=1 OT_SPLIT_TREE_HOSTS=dp OT_RESET_GATE=warn \
 OT_PIN_ALIGN_GATE=warn OT_SPLIT_ALIGN_BAND_WORDS=0 OT_RELAY_DUMP=$O.dump.json OT_RELAY_COLLISION_JSON=$O.collision.json \
 OT_RELAY_SITE_FAILURE=$O.site_failure.json OT_RELAY_TRACE=${TRACE:-1} PYTHONDONTWRITEBYTECODE=1 python3 tools/qwen_tp8/relay_data_run.py $O --case > $L 2>&1
rc=$?; echo "rc=$rc" >> $L; exit $rc
