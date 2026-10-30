#!/bin/bash
set -euo pipefail
K=$1
mkdir -p "$K/diag_out2"
python3 - "$K" <<'PY'
from pathlib import Path
import sys
k=Path(sys.argv[1]);s=(k/'landing_placement.tcl').read_text();s=s[s.index('# Generated caller provides'):]
(k/'tile_geometry_helper.tcl').write_text('set cland_groups {}\nset cland_optional_groups {}\nset cland_status {}\n'+s)
PY
cat > "$K/dpl_trial2.tcl" <<'TCL'
set_thread_count 4
set ::env(RESULTS_DIR) /work/diag_out2
read_db /work/run/results/asap7/dp_hd_tile/base/3_place.odb
set ff_blk [ord::get_db_block]
set ff_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ff_core [$ff_blk getCoreArea]
set ff_x0 [$ff_core xMin];set ff_y0 [$ff_core yMin];set ff_x1 [$ff_core xMax];set ff_y1 [$ff_core yMax]
set ff_rows [$ff_blk getRows];set ff_site [[lindex $ff_rows 0] getSite]
set ff_sw [$ff_site getWidth];set ff_rh [$ff_site getHeight]
set ff_orient {}
foreach r $ff_rows {dict set ff_orient [lindex [$r getOrigin] 1] [$r getOrient]}
source /work/tile_geometry_helper.tcl
foreach i [$ff_blk getInsts] {
 if {![cland_ours [$i getName]] || [$i getPlacementStatus] ni {FIRM LOCKED}} continue
 set b [$i getBBox];cland_occupy [$b xMin] [$b yMin] [expr {[$b xMax]-[$b xMin]}] [expr {[$b yMax]-[$b yMin]}]
}
source /work/tile_hop.tcl
detailed_placement
check_placement -verbose
write_db /work/diag_out2/3_place.odb
TCL
docker run --rm --name codex-head-tile3-dpl2 --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/dpl_trial2.tcl'
