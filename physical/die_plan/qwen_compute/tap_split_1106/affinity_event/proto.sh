#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106
K=/srv/opentallas-scratch2/claude/codex-wave-1105/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/cbn_q00__cldbcda913/attempt_6/gen/cbn_q00__cldbcda913
python3 -B "$R/proto.py"
OUT=$R/canary_cbn_97
mkdir -p "$OUT"
docker run --rm --cpus=2 --memory=8g -v "$K:/work:ro" -v "$R/src:/src:ro" -v "$R/proto.tcl:/canary.tcl:ro" -v "$R/proto_assign.tcl:/proto_assign.tcl:ro" -v "$OUT:/out" -e OT_TAP_CHAIN_RADIUS_UM=200 -e OT_TAP_CHAIN_MAX_GROUP=128 -e OT_TAP_MAX_SINKS=1200 -e RESULTS_DIR=/out --entrypoint bash openroad/orfs:asap7lock -c 'L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; export PLIBS="$(find "$L" -maxdepth 1 -name "*RVT_FF_nldm*" ! -name "*250407*" | sort | tr "\n" " ") /work/macros/qfd_tile_nk_a0c_ff.lib"; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /canary.tcl' > "$OUT/run.log" 2>&1
