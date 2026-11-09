#!/bin/bash
# DIE-HBM-92-OPEN/Q2NF vD unit body. usage: vd_stage.sh KIT synth|place|lec
set -euo pipefail
K=$1; ST=$2; NAME=q2nfrf-vF-$ST
case $ST in
synth) MEMG=32; ENVS=();;
place) MEMG=32; ENVS=();;
ctsgrt) MEMG=40; ENVS=();;
lec)   MEMG=40; ENVS=(-e OT_LEC_REPLICA_MATCH=1 -e OT_LEC_PARITY_TERMS=1024 -e OT_LEC_CONE_S=3600);;
esac
cat > "$K/vf_inner_$ST.sh" <<IN
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'rc=\$?; chown -R 1000:1000 /work; exit \$rc' EXIT
set -e
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
if grep -q "^override export OT_HOLD_MM = 1" /work/config.mk; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1; fi
case $ST in
synth)
  python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1 || { tail -3 /work/rtl_lint.log; echo FAIL rtl_lint; exit 8; }
  \$M synth > /work/run_vd_synth.log 2>&1
  N=/work/run/results/asap7/hbc_ot_q2nf_rest/base/1_2_yosys.v
  python3 -I /work/face_guard_core.py \$N /work > /work/face_guard.log 2>&1; echo "face_guard rc \$?"
  python3 -I /work/port_bind_core.py \$N /work > /work/port_bind.log 2>&1; cat /work/port_bind.log
  grep -c "_dh92_dnz" \$N || true ;;
place)
  \$M do-floorplan > /work/run_vd_floorplan.log 2>&1
  \$M do-place > /work/run_vd_place.log 2>&1
  bash /work/layout_render_hook.sh 3_5_place_dp 0 || true
  echo "PLACE complete \$(date)" > /work/PLACE_DONE.txt ;;
ctsgrt)
  G="bash /work/grt183_make.sh \$M"
  \$M cts > /work/run_vd_cts.log 2>&1
  C=\$(ls /work/run/results/asap7/*/base/4_cts.odb | head -1); S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1)
  PLIBS="\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')" ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 OT_VCLK_TT=250 OT_VCLK_FF=202.5 LAYER_PARASITICS_FILE=\$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk) openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1 || true
  grep OT_HOLD_GATE /work/hold_gate.log || true
  bash /work/layout_render_hook.sh 4_1_cts 0 || true
  python3 -I /work/kit_modes.py check /work --step grt --session 'tc bc' --hold-repair > /work/kit_modes_grt.log 2>&1 || { echo FAIL kit_modes grt; exit 9; }
  \$G grt HOLD_SLACK_MARGIN=0 > /work/run_vd_grt.log 2>&1
  bash /work/layout_render_hook.sh 5_1_grt 0 || true
  echo "CTSGRT complete \$(date)" > /work/CTSGRT_DONE.txt ;;
lec)
  python3 -I /work/lec.py /work --out /work/lec_vd > /work/lec_vd.log 2>&1 ;;
esac
IN
docker run --rm --name "$NAME" --memory=${MEMG}g --memory-swap=${MEMG}g --cpus=8 "${ENVS[@]}" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /work/vf_inner_$ST.sh
