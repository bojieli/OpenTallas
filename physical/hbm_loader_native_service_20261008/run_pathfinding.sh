#!/usr/bin/env bash
# Run only on an admitted remote host. Never claim generic IO as die closure.
set -euo pipefail
: "${NATIVE_SOURCE:?pinned source root required}"
: "${NATIVE_DRIVER:?source-pinned physical driver required}"
: "${NATIVE_ROUTE_OUT:?new immutable output required}"
test -f /srv/opentallas-scratch/admit.sh
test ! -e "$NATIVE_ROUTE_OUT"
mkdir -p "$NATIVE_ROUTE_OUT"
OT_ORFS_NUM_CORES=4 NUM_CORES=4 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited \
/srv/opentallas-scratch/admit.sh 24 -- python3 "$NATIVE_DRIVER/tools/run_abi3_physical.py" \
 --source-root "$NATIVE_SOURCE" --view asap7 --top ot_hbm_loader_pc_service_lease \
 --source rtl/ot_hbm_loader_pc_service_lease.sv --param ENABLE=1 \
 --clock-port clk --clock-period-ns 0.833333333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner TC --hold-corners TC,BC --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 100 100 --core-area 2.052 2.160 97.884 97.740 --place-density 0.55 \
 --routing-layers M2 M7 --orfs-var ADDER_MAP_FILE= \
 --orfs-var 'CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none' \
 --hold-margin-ns 0.035 --purpose characterization --nickname-tag native_pc_pathfinding \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$NATIVE_ROUTE_OUT/work" --output "$NATIVE_ROUTE_OUT/physical.json" \
 > "$NATIVE_ROUTE_OUT/route.log" 2>&1
