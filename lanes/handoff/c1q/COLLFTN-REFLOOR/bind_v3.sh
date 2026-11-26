#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude
W=$D/QC-COLLFTN-REFLOOR
N=$W/tree
R=$D/rt/afdd397cad26
Q=physical/die_plan/qwen_compute
A=$Q/qc_start_1106/runtime/asbuilt_c1p_1125.json
C=$N/$Q/plan_of_record/zz_c1q_collftn_refloor_1125.json
BIN=$W/bind_v3
python3 -I -B $R/tools/fleet/ot-tree-fork --seal-check $N; echo "SEAL rc=$?"
sha256sum $N/rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_f5_cpub39_1.sv 2>/dev/null | cut -c1-12
[ -d $W/launch_v3 ] || bash "$R/tools/autopilot/rt_launch_tree.sh" "$N" "$R" "$W/launch_v3"
export OT_LANE=QC-COLLFTN-REFLOOR OT_REPO_ROOT=$N OT_PLAN_ROOT=$N/$Q OT_RT_CURRENT=$R PYTHONDONTWRITEBYTECODE=1 OT_PLAN_GATE_PRE=warn OT_RESETPUB_SOLVE=1 OT_BIND_EMIT_J=8
unset OT_RESET_HOP_CAP_UM
export OT_BIND_ONLY_TYPES=coll_ftn
cd "$W/launch_v3"
python3 -I -B tools/die_plan/bind.py elab "$C" --out "$BIN" --asbuilt "$N/$A" --mem 64 --strict > "$W/elab_v3.log" 2>&1; echo "ELAB rc=$?"
python3 -I -B tools/die_plan/bind.py bind "$C" --out "$BIN" --asbuilt "$N/$A" --mem 64 --strict --all-gaps --types coll_ftn > "$W/bind_v3.log" 2>&1; echo "BIND rc=$?"
tail -3 "$W/bind_v3.log"
python3 -I -B tools/die_plan/lane_asbuilt_latency.py "$BIN" "$C" --asbuilt "$N/$A" --pricing as-bound --json "$W/lat_v3.json" > "$W/lat_v3.log" 2>&1; echo "LAT rc=$?"; tail -2 "$W/lat_v3.log"
