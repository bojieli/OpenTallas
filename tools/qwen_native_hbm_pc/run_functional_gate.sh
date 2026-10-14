#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
lib=${1:?library root}; out=${2:?out}
mkdir -p "$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
[[ -x "$v" ]]||v=$(command -v verilator)
vroot=$("$v" -V | sed -n 's/^ *VERILATOR_ROOT *= *//p' | head -1)
c++ -std=c++17 -O1 -pthread -I"$lib/obj" -I"$vroot/include" -Itools/qwen_native_hbm_pc \
 tools/qwen_native_hbm_pc/functional_gate.cpp "$lib/obj/Vqwen_native_hbm_pc_provider__ALL.a" \
 "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" -o "$out/gate" > "$out/link.log" 2>&1
"$out/gate" > "$out/positive.log"
"$out/gate" data_mut > "$out/data_mut.log"
"$out/gate" ack_mut > "$out/ack_mut.log"
grep -q '^PASS ACTUAL_PHY' "$out/positive.log"
grep -q '^OBSERVED_FAIL read payload\|^OBSERVED_FAIL uncorrectable' "$out/data_mut.log"
grep -q '^OBSERVED_FAIL ACK physical write identity' "$out/ack_mut.log"
cat "$out/positive.log" "$out/data_mut.log" "$out/ack_mut.log"
