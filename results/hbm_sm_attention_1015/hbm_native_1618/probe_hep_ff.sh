#!/bin/bash
set -e
base=/srv/opentallas-scratch/claude/closure-loop/hep_static_w5e_1016-w5e-314f4f068
own=/srv/opentallas-scratch/codex/hbm-native-1618
python3 - <<'PY'
from pathlib import Path
b=Path('/srv/opentallas-scratch/claude/closure-loop/hep_static_w5e_1016-w5e-314f4f068')
s=(b/'record/views/hfd_ep_static/export_ff.tcl').read_text().split('write_timing_model')[0]
s+='''
report_checks -from [get_ports {tx_frame[389]}] -path_delay min -format full_clock_expanded -fields {slew cap fanout input net} -digits 6
report_checks -from [get_ports {sd_rx[419]}] -path_delay min -format full_clock_expanded -fields {slew cap fanout input net} -digits 6
report_checks -to [get_ports {sd_tx[149]}] -path_delay min -format full_clock_expanded -fields {slew cap fanout input net} -digits 6
exit
'''
Path('/srv/opentallas-scratch/codex/hbm-native-1618/probe_hep_ff.tcl').write_text(s)
PY
docker run --rm -v "$base/routes/hep_static_w5e_1016_w5e_314f4f068/work/orfs:/work:ro" -v "$base/src:/src:ro" -v "$base/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2:/mv0:ro" -v "$base/cl/routed_ioref.a1_meas:/meas:ro" -v "$own:/audit" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/probe_hep_ff.tcl > "$own/probe_hep_ff.log" 2>&1
