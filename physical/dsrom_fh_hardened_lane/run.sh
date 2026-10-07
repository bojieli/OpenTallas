#!/bin/bash
# Caller performs active capacity admission, then invokes through host admit.sh.
set -euo pipefail
if [ "$#" -ne 1 ]; then echo 'Usage: run.sh RUN_ROOT' >&2; exit 2; fi
R=$(realpath -m "$1")
S=$(realpath "$(dirname "$0")/../..")
cd "$S"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
export OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
D=rtl/hdc/v41/dspark_fused_head
M=ot_sram_1r1w_512x128_m4_r2c2
exec python3 tools/run_abi3_physical.py --source-root "$S" --view asap7  --top ot_hdc_v41_fh_sram_lane_hardened  --source "$D/capture_candidate/ot_hdc_v41_fh_sram_return.sv"  --source "$D/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv"  --source rtl/dft/ot_rom_secded_dec.sv  --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025  --orfs-corner WC --hold-corners WC,BC --stages pnr --pnr-stop-after finish  --macro-view "$M=physical/asap7_memory_macros/$M" --macro-place-halo 2 2  --orfs-var ADDER_MAP_FILE= --die-area 0 0 200 55 --core-area 2 2 198 53  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/dsrom_fh_hardened_lane/macro_place.tcl  --place-density "${OT_FH_PLACE_DENSITY:-0.55}" --core-utilization 35  --orfs-var GPL_TIMING_DRIVEN=0 --orfs-var CTS_CLUSTER_SIZE=8 --orfs-var ENABLE_DPO=0  --orfs-var DETAIL_PLACEMENT_ARGS=-use_diamond_legalizer --orfs-var PLACE_DENSITY_LB_ADDON=  --max-transition-ns 0.25 --max-fanout 16 --slew-margin-percent 20 --hold-margin-ns 0.02  --sdc-append physical/dsrom_fh_hardened_lane/boundary.sdc --io-delay-fraction 0.2  --keep-workdir "$R/work" --nickname-tag "${OT_FH_ROUTE_TAG:-lane}" --output "$R/physical.json"
