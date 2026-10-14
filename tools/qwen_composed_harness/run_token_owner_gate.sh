#!/usr/bin/env bash
set -euo pipefail
output=${1:?fresh output directory}
allocator=allocator0/library/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
[[ ! -e "$output" ]];mkdir -p "$output"
sha256sum src/token_epoch_owner.hpp src/token_owner_gate.cpp "$allocator/Vot_qwen_tp8_token_epoch_allocator__ALL.a" allocator0/src/ot_qwen_tp8_token_epoch_allocator.sv > "$output/inputs.sha256"
c++ -std=c++17 -O1 -pthread -Isrc -I"$allocator" -I"$vroot/include" -I"$vroot/include/vltstd" src/token_owner_gate.cpp "$allocator/Vot_qwen_tp8_token_epoch_allocator__ALL.a" "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" -o "$output/gate" > "$output/build.log" 2>&1
"$output/gate" "$output/actual" > "$output/run.log" 2>&1
sha256sum "$output/gate" >> "$output/inputs.sha256"
cat "$output/run.log"
