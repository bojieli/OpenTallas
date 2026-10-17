#!/bin/bash
# Source-only q3h2 diagnostic smoke. OT_RELAY_SKIP removes physical relay planning;
# never use its cut, stage or cost outputs as routed/native qualification.
set -u
cd "$(dirname "$0")/../.." || exit 9
O=${1:?usage: q3h_diagnostic_smoke.sh ABSOLUTE_OUTDIR}
L=$O.log
D=results/arch/qwen_split_compute_1014
env OT_RELAY_SKIP=1 OT_TP8_SPLIT=compute OT_SPLIT_B2=1 OT_SPLIT_B2_PHYSICAL_TRIAL=1 OT_SPLIT_B2_COMPACT_SELECTOR=1 \
 OT_SPLIT_Q3H=1 OT_SU_VM_CHANNEL_UM=43.2 OT_SPLIT_Q3H_CONTRACT=${CONTRACT:-$D/dieplan2_1016/q3h_cluster_contract_cb.json} OT_SPLIT_Q3H_GRID=$D/dieplan2_1016/q3h2_grid.json OT_SPLIT_XCOL_WH=129.6,920.16 OT_SPLIT_Q3H_HTREE=${HTREE:-} \
 OT_RELAY_REACH_UM=${REACH:-373} OT_RELAY_REACH_OK=${REACH_OK:-363} \
 OT_SPLIT_HOMES=$D/dieplan2_1016/q3h2-homes.json OT_SPLIT_HOMES_REBASE=1 OT_SPLIT_VM_WH=4872.024,3239.384 OT_SPLIT_PHY_NFACE=1 \
 OT_SPLIT_SYSFACE_XY=17921.52,13865.04 OT_SPLIT_TILE_GRANT=$D/dieplan2_1016/proxy_t1166_a0_held_grant.json \
 OT_SPLIT_PIN_GRANT=$D/dieplan2_1016/q2o2d_grant.json OT_SPLIT_BW_SPREAD=1 OT_SPLIT_TREE_HOSTS=dp OT_RESET_GATE=warn \
 OT_PIN_ALIGN_GATE=warn OT_SPLIT_ALIGN_BAND_WORDS=0 OT_RELAY_DUMP=$O.dump.json OT_RELAY_COLLISION_JSON=$O.collision.json \
 OT_RELAY_SITE_FAILURE=$O.site_failure.json PYTHONDONTWRITEBYTECODE=1 python3 tools/qwen_tp8/relay_data_run.py "$O" --case > "$L" 2>&1
rc=$?
echo "rc=$rc" >> "$L"
exit "$rc"
