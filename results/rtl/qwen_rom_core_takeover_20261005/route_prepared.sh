#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/codex/qwen-rom-core-context3-20261005
SOURCE_DIR=/srv/opentallas-scratch/codex/qwen-rom-core-context2-20261005/context_src
cd "$R/src"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
# Same pinned prepared core; driver1e5's argv-only fix a78, no re-preparation.
python3 tools/run_abi3_physical.py --source-root "$SOURCE_DIR" --view asap7 --top ot_qwen_rom_core \
 --source rtl/control_context.v --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
 --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag codex_rom_dec_la_ar_ctx3 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$R/work" --output "$R/physical.json"
python3 tools/w18/corner_sta.py --orfs-dir "$R/work/orfs" --output "$R/corner_sta.json"
