#!/bin/bash
# QLB-GEN 10-18 dv2f14br: netlist-only compute GEN on claude/qlb-gen-1018 7c660b3f7 (= main 54aef0490 incl. q-lbgap lineage: Q-DIE13 bhd flags + Q-COLLCAL + QXF-SEAMC record bundles + QXF-LINK TXDP) + G-C1 die params; LAND_PLAN: see plan.txt
# dv2f14bhd = dv2f14bhc + CLOSED qfd_rst_rep/_p8 (OT_RST_REP_VIEW=closed, d5a922c32) + a9f90ad8f hold-budget tap fail-closed
# Q-DIE13 10-18 dv2f14bhd: dv2f14bg + landing channels (d2d_rom/ucie_kv/bumps +259.2 um N, sys_face +129.6 um E), LAND_CROSS on, LAND_PLAN from dv2f14bg chain
# LANDFIX-SQ 10-18 dv2f14bhd: dv2f14bn + claude/landfix-q-1018 (FDI + reset + pad-bump lanes forwarded; landing MCP = E_sta)
# Q-DIE11b 10-18 dv2f14b: exact tree HEAD (see SOURCE_COMMIT; = seam kept 129.6, f4862c038 + square landing frames OT_SPLIT_FWD_LAND_SHAPE=square + sys_face rs3 view frame + TT head h16c + cluster 2445.12 outline on 2462.4 pitch + 16 centre-fed regional clocks per cluster)
# Q-DIE11 10-18 dv2f14: exact tree f4862c038 (q-die11 = q-die10 + main + slice/cluster pin windows + tile grant _rr + forwarded half-cycle lanes/landings (rising hop 0, landing frames) + io_collective PHY face clocks). Was: dv2f12 plan
# W/E faces (M4) from the 17.28-um inter-cluster gaps) + cluster/slice abstracts obstruct M1-M8 only (OT_SPLIT_DV_OBS_TOP=8 OT_SPLIT_DV_SLICE_GAP_UM=${SGAP:-43.2} OT_SPLIT_DV_SLICE_OBS_TOP=5 OT_SPLIT_DV_PIN_WINDOW_UM=9.6 OT_SPLIT_FWD_LANES=1;
# dv2f10 PDN-0006: die VDD M8 blocked by the M9 OBS).  Gates HARD (relay, per-bit reach 405).
# Q-DIEPLAN7 10-17 dv2f10: dv2f9 + d2d_rom / ucie_kv MX (closed qfd_d2d_static has M3+M5 vertical pins: no legal origin under MY/R180), links re-planned in GEN
# dv2f9 GEN (Q-DIEPLAN6 10-17): dv2f8 + re-ported W-column masters bound (native59 dv_service, tt_ctlm_dv, sys_face G8,
# embedding provider closed view) + seam chain lane (OT_SPLIT_DV_SEAM_LANE=1). Gates HARD (relay, per-bit reach 405).
# q3h model: OT_SPLIT_Q3H (q3h4 grid / CB contract) + OT_SPLIT_DV (Q-DV model). Reach 405 / per-bit 405 (owner 0cl),
# BFS budget 60k. $1 = "" FULL GEN -> ../out ; "skip" relay-skip smoke -> ../out_$TAG
S=/srv/opentallas-scratch/claude/qlb-gen-1018/dv2f14br
cd $S/src || exit 9
D=results/arch/qwen_split_compute_1014
O=../out; L=../out.log; X=
[ "$1" = skip ] && { O=../out_${TAG:-skip}; L=../out_${TAG:-skip}.log; X="OT_RELAY_SKIP=1"; }
G=; [ "${GATE:-hard}" = warn ] && G="OT_RELAY_GATE=warn"
env $X $G OT_RST_REP_VIEW=closed OT_DIE_RELAY_STAGES_OUT=$S/out/relay_stages.json OT_DIE_RELAY_STAGES_PLAN_ID=dv2f14br-qlbgen OT_TP8_SPLIT=compute OT_SPLIT_B2=1 OT_SPLIT_B2_PHYSICAL_TRIAL=1 OT_SPLIT_B2_COMPACT_SELECTOR=1 \
 OT_SPLIT_Q3H=1 OT_SU_VM_CHANNEL_UM=43.2 OT_SPLIT_Q3H_CONTRACT=$D/dieplan2_1016/q3h_cluster_contract_cb.json OT_SPLIT_Q3H_GRID=$D/dieplan2_1016/q3h4_grid.json OT_SPLIT_XCOL_WH=129.6,920.16 \
 OT_SPLIT_PHY_TALL=1 OT_SPLIT_DV_RSI_AT_RS=1 OT_RELAY_WORST_BIT=ordered OT_SPLIT_DV_SEAM_LANE=1 OT_SPLIT_DV_ORIENT=${D2D_ORIENT:-d2d_rom=MX,ucie_kv=MX} OT_SPLIT_DV_D2D_DX=${D2D_DX:-0} OT_SPLIT_DV_FACES=rtl/qwen_dv/qfd_dv_slice2_faces.json OT_SPLIT_DV=$D/dieplan2_1016/dv2r8f7r_qdv_p2462.json OT_SPLIT_DV_CLUSTER_CENTRE_CLOCKS=$D/dieplan2_1016/die_clock16_6cb80af66.json OT_SPLIT_DV_CLUSTER_CLOCK_AT=${CLUSTER_CLOCK_AT:-face} OT_SPLIT_DV_CONTRACT=$D/dieplan2_1016/cluster_contract_dv_6cb80af66.json OT_SPLIT_DV_OBS_TOP=8 OT_SPLIT_DV_SLICE_GAP_UM=${SGAP:-43.2} OT_SPLIT_DV_SLICE_OBS_TOP=5 OT_SPLIT_DV_PIN_WINDOW_UM=9.6 OT_SPLIT_FWD_LANES=1 OT_SPLIT_FWD_LANES_FDI=1 OT_SPLIT_FWD_LANES_RST=1 OT_SPLIT_FWD_LANES_BUMP=1 OT_SPLIT_LAND_CROSS=${LAND_CROSS-d2d_rom,sys_face} OT_SPLIT_DV_D2D_DY=259.2 OT_SPLIT_DV_SYSFACE_DX=129.6 OT_SPLIT_LAND_PLAN=${LAND_PLAN-} OT_SPLIT_FWD_LAND_SHAPE=${LAND_SHAPE:-ns} \
 OT_PIN_BIT_REACH_UM=${BITREACH:-405} OT_RELAY_REACH_UM=${REACH:-405} OT_RELAY_REACH_OK=${REACH_OK:-395} OT_RELAY_BFS_MAX=${BFS:-60000} \
 OT_SPLIT_HOMES=$D/dieplan2_1016/q3h4-homes.json OT_SPLIT_HOMES_REBASE=1 OT_SPLIT_VM_WH=4872.024,3239.384 OT_SPLIT_PHY_NFACE=1 \
 OT_SPLIT_SYSFACE_XY=17921.52,13865.04 OT_SPLIT_TILE_GRANT=$D/dieplan2_1016/proxy_t1166_a0r_held_grant_rr.json \
 OT_SPLIT_PIN_GRANT=$D/dieplan2_1016/q2o2d_grant.json OT_SPLIT_BW_SPREAD=1 OT_SPLIT_TREE_HOSTS=dp OT_RESET_GATE=warn \
 OT_PIN_ALIGN_GATE=warn OT_SPLIT_ALIGN_BAND_WORDS=0 OT_RELAY_DUMP=$O.dump.json OT_RELAY_COLLISION_JSON=$O.collision.json \
 OT_RELAY_SITE_FAILURE=$O.site_failure.json OT_RELAY_TRACE=${TRACE:-1} PYTHONDONTWRITEBYTECODE=1 python3 tools/qwen_tp8/relay_data_run.py $O --case > $L 2>&1
rc=$?; echo "rc=$rc" >> $L; exit $rc
