#!/bin/bash
# S81-KVTC-PINS: full harden of one kvtcp kit (synth -> floorplan via ref_route.sh, then the signed kvtch chain:
# place with the kvtch GPL args, MM CTS (OT_HOLD_MM, TC lib), GRT, DRT, TC fill + finish with all-corner SPEF).
# usage: run_kvtcp.sh KIT LABEL
set -euo pipefail
B=/srv/opentallas-scratch2/claude/S81-KVTC-PINS; R=$B/kitrepo; K=$1; L=$2; O=$B/runs
mkdir -p $O
export SRC=$R NC=8 OPENTALLAS_ORFS_IMAGE=openroad/orfs:asap7lock
w=$O/$L/work/orfs
if [ -z "$(find $w/results -name 2_floorplan.odb -print -quit 2>/dev/null)" ]; then
  echo "== floorplan $(date -u +%T)"
  bash $R/tools/ref_tile/ref_route.sh $R/physical/ref_tile/$K/kit.env $L $O floorplan || { echo "STAGE_FAIL floorplan"; exit 3; }
fi
grep -q '^export OT_FENCE_UNREG_OK = o_fo$' $w/config.mk
mapped=$(find "$w/results" -name 1_2_yosys.v -print -quit)
python3 -I -B - "$mapped" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
pin=re.search(r'BUFx\w+ \S+ \(\s*\.A\((\w+)\),\s*\.Y\(o_fo\)\s*\);',s)
if not(pin and re.search(r'TIELO\w+ \S+ \(\s*\.L\('+pin[1]+r'\)\s*\);',s)):
    raise SystemExit('o_fo lacks mapped constant-low proof')
print(f'o_fo exact mapped TIELO0 via {pin[1]}')
PY
grep -q '^export GLOBAL_PLACEMENT_ARGS' $w/config.mk || printf '%s\n' 'export GLOBAL_PLACEMENT_ARGS = -routability_max_density 0.56 -routability_max_inflation_ratio 1.16 -routability_inflation_ratio_coef 0.9' >>"$w/config.mk"
echo "== place $(date -u +%T)"
docker run --rm --memory 39g -v "$R:/src:ro" -v "$w:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
  trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp
' >"$O/$L/place.log" 2>&1 || { echo "STAGE_FAIL place"; exit 3; }
f=$(find "$w/results" -name 3_5_place_dp.odb -print -quit); test -s "$f"; cp -p "$f" "${f%/*}/3_place.odb"
grep -q '^export OT_HOLD_MM = 1' $w/config.mk || cat >> "$w/config.mk" <<CONFIG
export OT_HOLD_MM = 1
export OT_MM_FF_SDC = /src/physical/ref_tile/$K/signoff.sdc /src/physical/ref_tile/$K/core_view_ff.sdc
export WC_NLDM_LIB_FILES = \$(TC_NLDM_LIB_FILES)
CONFIG
echo "== cts grt drt finish $(date -u +%T)"
docker run --rm --memory 39g -v "$R:/src:ro" -v "$w:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
  trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
  python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts &&
  python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl &&
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 do-cts &&
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt &&
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 do-5_2_route &&
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 CORNER=TC do-5_3_fillcell do-5_route do-5_route.sdc do-finish
' >"$O/$L/route.log" 2>&1 || { echo "STAGE_FAIL route"; tail -5 $O/$L/route.log; exit 3; }
find "$w/results" -name 6_final.odb | grep . && echo "KVTCP_ROUTED $L"
