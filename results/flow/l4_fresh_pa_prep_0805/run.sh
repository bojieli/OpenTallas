#!/bin/bash
set -euo pipefail
R=$(realpath "$(dirname "$0")")
K=$R/kit
[[ ${L4_FRESH_PA_REVIEWED:-0} == 1 ]] || { echo PREP_ONLY_NO_DISPATCH; exit 70; }
[[ $(sha256sum "$K/apreader.so" | cut -d ' ' -f 1) == 425d9c256dddb0f1bae66bf2d8aa0fb81e2940d7b242eb1eaecf4171c6e66d66 ]] || { echo AP_READER_MODULE_REFUSED; exit 71; }
docker run --rm --memory=32g --memory-swap=32g --cpus=1 -v "$K":/work -w /OpenROAD-flow-scripts/flow -e OT_PG_STRICT=1 \
 sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/fresh_pa_mm.log 2>&1
python3 /work/patch_fresh_pa.py > /work/fresh_pa_runtime.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 do-5_1_grt CORNER=TC CORNERS="tc bc" SKIP_INCREMENTAL_REPAIR=1
'
python3 -I "$K/clk_geom_diff.py" "$K/FRESH_PA_CLOCK_INPUT.tsv" "$K/FRESH_PA_CLOCK_AFTER.tsv" > "$R/clock_guard.json"
