#!/bin/bash
set -euo pipefail
SRC=$1
OUT=$2
cd "$SRC"
export OT_ORFS_NUM_CORES=4
# Same actual FIFO/held NEXT/dynamic tables and all decoded fields; arithmetic
# engines are outside this component. This cannot qualify the full core.
python3 tools/run_abi3_physical.py --view asap7 --top decode_component \
 --source rtl/test/qwen_decode_pipe_20261004/component_selected.sv \
 --source rtl/hdc/ot_hdc_dyn_ttiles.sv \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
 --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 \
 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target \
 --nickname-tag hubble_qwen_decode_pipe_r2 --keep-workdir "$OUT/work" --output "$OUT/physical.json"
python3 tools/w18/corner_sta.py --orfs-dir "$OUT/work/orfs" --output "$OUT/corner_sta.json"
