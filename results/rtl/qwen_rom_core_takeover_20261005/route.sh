#!/bin/bash
set -euo pipefail
R=${ROM_CONTEXT_ROOT:-/srv/opentallas-scratch/codex/qwen-rom-core-takeover-20261005}
cd "$R/src"
python3 tools/qwen_rom_core_takeover_context.py --retained "$R/retained_context" --out "$R/context_prepare"
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -q -s "$R/context_prepare/prepare.ys" > "$R/context_prepare/yosys.log" 2>&1
mkdir -p "$R/context_src/rtl"
cp "$R/context_prepare/control_context.v" "$R/context_src/rtl/"
cp -r configs "$R/context_src/"
cd "$R/context_src"
git init -q
git -c user.name=Codex -c user.email=codex@opentallas.local add rtl/control_context.v configs
git -c user.name=Codex -c user.email=codex@opentallas.local -c gc.auto=0 commit -qm 'Pinned exact exposed ROM core control context'
cd "$R/src"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --source-root "$R/context_src" --view asap7 --top ot_qwen_rom_core \
 --source rtl/control_context.v --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
 --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag codex_rom_dec_la_ar_ctx1 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$R/route_work" --output "$R/physical.json"
python3 tools/w18/corner_sta.py --orfs-dir "$R/route_work/orfs" --output "$R/corner_sta.json"
