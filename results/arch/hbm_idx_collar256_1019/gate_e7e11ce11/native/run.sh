#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/hdie_col_idx256_1019-20261019-103656
for C in tt ff; do
 docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/hdie_col_idx256_1019/signoff.sdc -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work" -v "$R/idx256_probe_$C.tcl:/probe.tcl:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl > "$R/idx256_native_$C.log" 2>&1
 done
 echo IDX256_NATIVE_TT_FF_DONE
