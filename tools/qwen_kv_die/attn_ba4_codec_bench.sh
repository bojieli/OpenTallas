#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd);O=$(mkdir -p "$1" && readlink -f "$1");M=${2:-0}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$O/verilator.version"
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_kvba_codec_ba4 -GMUT="$M" -Mdir "$O/obj" "$R/rtl/qwen_sys/split_20261014/qkd_native_attention_static_ctl.sv" "$R/rtl/qwen_sys/kv_bootage_20261019/qkd_native_attention_static_ctl_ba4.sv" "$R/rtl/test/kv_bootage_1019/tb_kvba_codec_ba4.sv" > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_kvba_codec_ba4" > "$O/sim.log" 2>&1
sim_rc=$?
set -e
cat "$O/sim.log"
[ "$sim_rc" = 0 ] || exit "$sim_rc"
grep -q '^KVBA_CODEC_BA4 PASS' "$O/sim.log"
