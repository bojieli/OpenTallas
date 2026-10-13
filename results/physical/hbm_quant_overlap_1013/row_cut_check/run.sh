#!/bin/bash
set -euo pipefail
base=/srv/opentallas/claude/closure-loop/qw_ov_ref-ov1-cx-c8c47022e
trial=/srv/opentallas-scratch2/codex/qw-ov-row-cut
old=$base/routes/qw_ov_ref_ov1_cx_c8c47022e/work/orfs
mkdir -p "$trial/work"
cp -a --reflink=auto "$old/." "$trial/work/"
python3 - "$trial/work/config.mk" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();assert s.count('export POST_TAPCELL_TCL =')==1
p.write_text(s.replace('export POST_TAPCELL_TCL =','export PRE_TAPCELL_TCL ='))
PY
image=openroad/orfs:asap7lock
db=/work/results/asap7/opentallas_ot_hgi_quant_wide_ov_asap7_ref_qw_ov_ref_ov1_cx_c8c47022e/base
docker run --rm -v "$base/src:/src:ro" -v "$trial/reserve_seam.tcl:/src/physical/hbm_quant_overlap/reserve_seam.tcl:ro" -v "$trial/work:/work" -w /OpenROAD-flow-scripts/flow "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 do-2_3_floorplan_tapcell' > "$trial/tapcell.log" 2>&1
docker run --rm -v "$trial:/trial:ro" -v "$trial/work:/work" -e OV_FRESH_DB="$db/2_3_floorplan_tapcell.odb" "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /trial/fresh_geometry.tcl' > "$trial/fresh.log" 2>&1
docker run --rm -v "$trial:/trial:ro" -v "$trial/work:/work" -e OV_OLD_DB="$db/3_4_place_resized.odb" -e OV_WARM_DB="$db/3_4_place_resized.odb" "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /trial/warm_geometry.tcl' > "$trial/warm.log" 2>&1
docker run --rm -v "$base/src:/src:ro" -v "$trial/work:/work" -w /OpenROAD-flow-scripts/flow "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 do-3_5_place_dp' > "$trial/dp.log" 2>&1
echo "PASS PRE_TAPCELL fresh geometry + preserved-netlist warm detailed-placement"
