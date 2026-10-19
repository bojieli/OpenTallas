#!/bin/bash
# dv2f9 GEN (Q-DIEPLAN6 10-17): dv2f8 + re-ported W-column masters bound (native59 dv_service, tt_ctlm_dv, sys_face G8,
# embedding provider closed view) + seam chain lane (OT_SPLIT_DV_SEAM_LANE=1). Gates HARD (relay, per-bit reach 405).
# q3h model: OT_SPLIT_Q3H (q3h4 grid / CB contract) + OT_SPLIT_DV (Q-DV model). Reach 405 / per-bit 405 (owner 0cl),
# BFS budget 60k. $1 = "" FULL GEN -> ../out ; "skip" relay-skip smoke -> ../out_$TAG
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f9
cd $S/src || exit 9
D=results/arch/qwen_split_compute_1014
O=../out; L=../out.log; X=
[ "$1" = skip ] && { O=../out_${TAG:-skip}; L=../out_${TAG:-skip}.log; X="OT_RELAY_SKIP=1"; }
G=; [ "${GATE:-hard}" = warn ] && G="OT_RELAY_GATE=warn"
env $X $G OT_DIE_RELAY_STAGES_OUT=$S/out/relay_stages.json OT_DIE_RELAY_STAGES_PLAN_ID=dv2f9-qdieplan6 OT_TP8_SPLIT=compute OT_SPLIT_B2=1 OT_SPLIT_B2_PHYSICAL_TRIAL=1 OT_SPLIT_B2_COMPACT_SELECTOR=1 \
 OT_SPLIT_Q3H=1 OT_SU_VM_CHANNEL_UM=43.2 OT_SPLIT_Q3H_CONTRACT=$D/dieplan2_1016/q3h_cluster_contract_cb.json OT_SPLIT_Q3H_GRID=$D/dieplan2_1016/q3h4_grid.json OT_SPLIT_XCOL_WH=129.6,920.16 \
 OT_SPLIT_PHY_TALL=1 OT_SPLIT_DV_RSI_AT_RS=1 OT_RELAY_WORST_BIT=ordered OT_SPLIT_DV_SEAM_LANE=1 OT_SPLIT_DV_FACES=rtl/qwen_dv/qfd_dv_slice2_faces.json OT_SPLIT_DV=$D/dieplan2_1016/dv2r8f7_qdv_cf19dc85c.json OT_SPLIT_DV_CONTRACT=$D/dieplan2_1016/cluster_contract_dv_0fd5cb773.json \
 OT_PIN_BIT_REACH_UM=${BITREACH:-405} OT_RELAY_REACH_UM=${REACH:-405} OT_RELAY_REACH_OK=${REACH_OK:-395} OT_RELAY_BFS_MAX=${BFS:-60000} \
 OT_SPLIT_HOMES=$D/dieplan2_1016/q3h4-homes.json OT_SPLIT_HOMES_REBASE=1 OT_SPLIT_VM_WH=4872.024,3239.384 OT_SPLIT_PHY_NFACE=1 \
 OT_SPLIT_SYSFACE_XY=17921.52,13865.04 OT_SPLIT_TILE_GRANT=$D/dieplan2_1016/proxy_t1166_a0r_held_grant.json \
 OT_SPLIT_PIN_GRANT=$D/dieplan2_1016/q2o2d_grant.json OT_SPLIT_BW_SPREAD=1 OT_SPLIT_TREE_HOSTS=dp OT_RESET_GATE=warn \
 OT_PIN_ALIGN_GATE=warn OT_SPLIT_ALIGN_BAND_WORDS=0 OT_RELAY_DUMP=$O.dump.json OT_RELAY_COLLISION_JSON=$O.collision.json \
 OT_RELAY_SITE_FAILURE=$O.site_failure.json OT_RELAY_TRACE=${TRACE:-1} PYTHONDONTWRITEBYTECODE=1 python3 tools/qwen_tp8/relay_data_run.py $O --case > $L 2>&1
rc=$?; echo "rc=$rc" >> $L; exit $rc
