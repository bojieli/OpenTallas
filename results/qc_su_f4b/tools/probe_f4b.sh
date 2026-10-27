#!/bin/bash
# QC-SU-F4B DIAGNOSTIC route-rule probe (not a candidate build): F4A placement + plan CTS (4_cts.odb, unchanged), tree nets
# on M5/M6 (f4b_layers.tcl in grt_pre_core.tcl) -> GRT (rc_cal) -> DRT -> fill/RCX (finish_f4a.sh flow).  No hold repair.
set -uo pipefail
K=$(cd "$1" && pwd); STEP=${2:-grt}
mk() { docker run --rm --name qcf4b-$1-$(basename $K)-$$ --cpus=16 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 $1" > "$K/probe_$1.log" 2>&1; r=$?; docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run; return $r; }
mk do-5_1_grt || exit 3
[ "$STEP" = grt ] && exit 0
mk do-5_2_route || exit 4
$(dirname $0)/finish_f4a.sh $K || exit 5
echo "PROBE_DONE $(date -Is)" > $K/probe_done.txt
