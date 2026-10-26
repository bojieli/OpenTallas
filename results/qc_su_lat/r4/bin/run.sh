#!/bin/bash
set -euo pipefail
K=$(readlink -f "$1"); TOP=$(awk '/^export DESIGN_NAME/{print $4;exit}' "$K/config.mk")
R=$(dirname "$(readlink -f "$0")")
docker run --rm --name qc-r4-$(basename "$K")-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt' > "$K/cts_grt.log" 2>&1
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
python3 "$R/collect_native.py" "$K"
