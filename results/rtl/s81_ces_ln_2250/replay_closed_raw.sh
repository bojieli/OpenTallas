#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/closure-loop/dscoll_cescn-sp1-5712c1f78
O=/var/tmp/s81rom2250/cesraw
mkdir -p "$O"
python3 - <<'PY'
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/closure-loop/dscoll_cescn-sp1-5712c1f78')
s=(r/'record/views/dsfd_coll_cescn/export_tt.tcl').read_text().split('puts "OT_WS')[0]
s+='\nputs "RAW_CORE_TT"\nreport_checks -to [get_ports {ln_d[408]}] -path_delay min_max -fields {slew cap input nets fanout} -format full_clock_expanded -group_path_count 3\nputs "RAW_DIE_BOUNDARY_DONE"\nexit\n'
Path('/var/tmp/s81rom2250/cesraw/raw_tt.tcl').write_text(s)
PY
docker run --rm -v "$R/routes/dscoll_cescn_sp1_5712c1f78/work/orfs:/work:ro" -v "$R/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2:/mv0:ro" -v "$R/cl/routed_ioref.a1_meas:/meas:ro" -v "$O:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/raw_tt.tcl > "$O/raw_tt.log" 2>&1
cat "$O/raw_tt.log"
