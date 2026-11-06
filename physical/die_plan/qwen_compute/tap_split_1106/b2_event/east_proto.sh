#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-tapsplit-east-1106
K=/srv/opentallas-scratch2/claude/codex-wave-1105/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/sle_su_c/gen/sle_su_c
python3 -B "$R/east_proto.py"
mkdir -p "$R/canary_f870"
docker run --rm --cpus=2 --memory=8g -v "$K:/work:ro" -v "$R/canary_f870:/out" -v "$R/src:/src:ro" -v "$R/proto2.tcl:/canary.tcl:ro" -v "$R/proto_assign.tcl:/proto_assign.tcl:ro" -e OT_TAP_CHAIN_RADIUS_UM=200 -e OT_TAP_CHAIN_MAX_GROUP=128 -e OT_TAP_MAX_SINKS=1200 -e RESULTS_DIR=/out -e OT_VCLK_FF=202.5 -e OT_HOLD_IN_MIN=-85 -e OT_HOLD_OUT_MIN=95 -e OT_TAP_WINDOW=120 -e LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl -e ODB=/work/run/results/asap7/dp_sle_su_c/base/3_place.odb -e SDC=/work/run/results/asap7/dp_sle_su_c/base/3_place.sdc --entrypoint bash openroad/orfs:asap7lock -c 'L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; PLIBS="";for n in AO INVBUF OA SEQ SIMPLE;do P=$(find "$L" -maxdepth 1 -name "asap7sc7p5t_${n}_RVT_FF_nldm*" ! -name "*250407*" | sort | head -1); PLIBS="$PLIBS $P";done; export PLIBS="$PLIBS $(find /work/macros -maxdepth 1 -name "*_ff.lib" | sort | tr "\n" " ")"; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /canary.tcl' > "$R/canary_f870/run.log" 2>&1
