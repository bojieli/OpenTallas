#!/bin/bash
set -euo pipefail
source "$HOME/.opentallas-env"
export OT_ORFS_NUM_CORES=2
export OPENTALLAS_ORFS_IMAGE=openroad/orfs:asap7lock
job=/srv/opentallas/jobs/dsrom-native-relay-leaf-20261003-r5
mkdir -p "$job/tmp"
export TMPDIR="$job/tmp"
python3 tools/run_abi3_physical_aligned_guarded.py --macro-track-gate --persistent-workdir "$job/work" --launch-receipt "$job/receipt.json" --view asap7 --top ot_ds_native_relay_leaf --source rtl/model_ready_ds_relay_20261003/ot_ds_native_relay_leaf.v --purpose characterization --stages synth,pnr --clock-period-ns 0.833333333333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --false-path-io --io-delay-fraction 0.2 --max-transition-ns 0.32 --hold-margin-ns 0 --die-area 0 0 26.19 4.86 --core-area 0 0 26.19 4.86 --routing-layers M2 M9 --step-tcl POST_DETAIL_PLACE=physical/dsrom_native_relay_20261003/place.tcl --step-tcl PRE_CTS=physical/dsrom_native_relay_20261003/fixed_cts.tcl --step-tcl POST_DETAIL_ROUTE=physical/dsrom_native_relay_20261003/report.tcl --orfs-var PDN_TCL=/src/physical/dsrom_native_relay_20261003/pdn.tcl --orfs-var DONT_BUFFER_PORTS=1 --orfs-var CELL_PAD_IN_SITES_GLOBAL_PLACEMENT=0 --orfs-var CELL_PAD_IN_SITES_DETAIL_PLACEMENT=0 --orfs-var PLACE_DENSITY_LB_ADDON= --keep-heavy-artifacts --nickname-tag ds_native_relay_leaf_r5 --output "$job/physical.json"
