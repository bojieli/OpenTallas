#!/bin/bash
# NEW LF-drivewire first GRT. Invoke through normal ot-run32G16T.
# Exact reviewed4CTS input; no synth/PLACE/CTS/proof rerun or DRT chain.
set -euo pipefail
K=$(cd "${1:?private candidate kit}" && pwd)
MEM=${2:-32}; THREADS=${3:-16}
test -f "$K/lf_drivewire_candidate.json"
test -s "$K/run/results/asap7/kl_dsdv_bksel_q_vG/base/4_cts.odb"
exec docker run --rm --name "bksel-lf-drivewire-grt-$$" --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$THREADS" -e OT_MAXWIRE_UM=90 -e OT_MACRO_OUT_BUF_MIN_UM=30 -e OT_HOLD_REPAIR_SCOPE=nonport -e OT_THREADS="$THREADS" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl; exec make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$OT_THREADS" HOLD_SLACK_MARGIN=20 do-grt' > "$K/run_grt_drivewire.log" 2>&1
