#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106
CASE=$1
if [[ "$CASE" == east ]];then
 TYPE=sle_su_c
 K=/srv/opentallas-scratch2/claude/codex-wave-1105/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/sle_su_c/gen/sle_su_c
else
 TYPE=cbn_q00__cldbcda913
 K=/srv/opentallas-scratch2/claude/codex-wave-1105/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/cbn_q00__cldbcda913/attempt_6/gen/cbn_q00__cldbcda913
fi
python3 -B "$R/proto2.py" "$CASE"
OUT=$R/canary_${CASE}_f870
mkdir -p "$OUT"
docker run --rm --cpus=2 --memory=8g -v "$K:/work:ro" -v "$R/src:/src:ro" -v "$R/proto2.tcl:/canary.tcl:ro" -v "$R/proto_${CASE}_assign.tcl:/proto_assign.tcl:ro" -v "$OUT:/out" -e ODB=/work/run/results/asap7/dp_$TYPE/base/3_place.odb -e SDC=/work/run/results/asap7/dp_$TYPE/base/3_place.sdc -e OT_TAP_CHAIN_RADIUS_UM=200 -e OT_TAP_CHAIN_MAX_GROUP=128 -e OT_TAP_MAX_SINKS=1200 -e RESULTS_DIR=/out --entrypoint bash openroad/orfs:asap7lock -c 'L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; PLIBS="";for n in AO INVBUF OA SEQ SIMPLE;do P=$(find "$L" -maxdepth 1 -name "asap7sc7p5t_${n}_RVT_FF_nldm*" ! -name "*250407*" | sort | head -1); PLIBS="$PLIBS $P";done; export PLIBS="$PLIBS $(find /work/macros -maxdepth 1 -name "*_ff.lib" | sort | tr "\n" " ")"; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /canary.tcl' > "$OUT/run.log" 2>&1
