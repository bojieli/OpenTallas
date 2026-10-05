#!/bin/bash
set -u
cd "$(dirname "$0")/../.."
TASK_ROOT=$(realpath "$1")
export OT_ORFS_NUM_CORES=4
ulimit -f unlimited
# Current prescribed same-policy route, persistent uncapped launcher, no retries.
python3 tools/run_abi3_physical_persistent.py \
 --persistent-workdir "$TASK_ROOT/work" --launch-receipt "$TASK_ROOT/launch.json" \
 --view asap7 --top ot_v41_static_provider_context \
 --source physical/dsrom_static_provider_context/ot_v41_static_provider_context.sv \
 --source rtl/v41die/static_controls/ot_v41_stage37_control_rom.sv \
 --source rtl/v41die/static_controls/ot_v41_stage38_control_rom.sv \
 --param CONTROL_STAGE=37 --clock-period-ns 0.833333 \
 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --corner TT --orfs-corner WC --hold-corners WC,BC \
 --io-delay-fraction 0.2 --max-transition-ns --max-fanout 32 \
 --slew-margin-percent 30 --hold-margin-ns 0.01 --stages pnr \
 --die-area 0 0 207.36 108 --core-area 2.16 2.16 205.20 107.73 \
 --routing-layers M2 M8 --place-density 0.5 \
 --orfs-var PLACE_DENSITY_LB_ADDON= \
 --step-tcl PRE_GLOBAL_PLACE_SKIP_IO=physical/dsrom_static_provider_context/threads.tcl \
 --step-tcl PRE_GLOBAL_PLACE=physical/dsrom_static_provider_context/threads.tcl \
 --step-tcl POST_PDN=physical/dsrom_static_provider_context/regions.tcl \
 --step-tcl PRE_CTS=physical/dsrom_static_provider_context/clock.tcl \
 --step-tcl POST_CTS=physical/dsrom_static_provider_context/clock.tcl \
 --orfs-var ADDER_MAP_FILE= --orfs-var MIN_CLK_ROUTING_LAYER=M7 \
 --orfs-var FASTROUTE_TCL=/src/physical/dsrom_static_provider_context/fastroute.tcl \
 --orfs-var PDN_TCL=/src/physical/dsrom_static_provider_context/pdn.tcl \
 --nickname-tag epicurus_static_context_r1 --keep-heavy-artifacts --output "$TASK_ROOT/physical.json" \
 > "$TASK_ROOT/route.log" 2>&1
TASK_STATUS=$?
printf '%s\n' "$TASK_STATUS" > "$TASK_ROOT/terminal.exit"
exit "$TASK_STATUS"
