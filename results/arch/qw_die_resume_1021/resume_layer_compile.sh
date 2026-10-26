#!/bin/bash
set -euo pipefail
B=$(cd "$(dirname "$0")" && pwd)
cd "$B/src"
export OT_GIT_SHOW_CACHE="$B/cache" PYTHONDONTWRITEBYTECODE=1
python3 tools/qwen_layerbench/layer_compile.py --out "$B/compiled_L1" --compute-stages "$B/p2/relay_stages_netlist.json" --kv-stages results/rtl/qwen_layer_tput_1018/compiled_L1/die_run/kv_kvs14c_relay_stages.json.gz --compute-commit 61748a16e --compute-params "$B/p2/die.v.params.json" --compute-die-v "$B/p2/die.v" --compute-lanes "$B/p2/fwd_lanes.json" > "$B/layer_compile.log" 2>&1
bash tools/die_relay_chain_step.sh "$B/p2/relay_stages_netlist.json" "$(find "$B/compiled_L1/relay_schedule" -name 'compute_compiled.json*' -print -quit)" "$B/relay_check.json" > "$B/relay_check.log" 2>&1
