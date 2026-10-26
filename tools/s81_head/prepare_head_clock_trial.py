"""Stage CTS-only native-head trial with bounded local clock regions.
The existing GRT miss had 100-um leaf wiring after F4 reassignment; a 40-um
local region confines its wire growth and keeps the clock tree out of ROMs.
This does not alter RTL, IO timing, or give a route/signoff token.
"""
import argparse,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('seed',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[2]
if a.out.exists():raise SystemExit('refuse existing output')
shutil.copytree(a.seed,a.out)
for f in ['core_density_taps.tcl','core_tap_align.tcl','f4_chain_leaf.tcl']:
 shutil.copy2(repo/'physical/die_plan/hbm_arch_cores'/f,a.out/f)
(a.out/'prects_dtap.tcl').write_text('source /work/prects_clear.tcl\nsource /work/core_density_taps.tcl\n')
with (a.out/'config.mk').open('a') as f:f.write('''
# CTS-ONLY structural trial: finer density regions, no unused clock loads.
export PRE_CTS_TCL = /work/prects_dtap.tcl
export OT_DTAP_TARGET = 625
export OT_DTAP_DMAX_UM = 40
export OT_DTAP_OUT = /work/dtap.txt
export POST_CTS_TCL = /work/f4_chain_leaf.tcl
export OT_F4_NEXT_TCL = /work/core_tap_align.tcl
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -sink_clustering_max_diameter 20 -sink_clustering_size 16 -distance_between_buffers 40 -balance_levels -dont_use_dummy_load
''')
(a.out/'run_clock_trial.sh').write_text('''#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd); MEM=${3:-32}; CPUS=${4:-16}
test "${2:-cts}" = cts || { echo CTS_ONLY; exit 2; }
docker run --rm --name headb-cts40-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base cts' > "$K/cts_trial.log" 2>&1
''')
print(a.out)
