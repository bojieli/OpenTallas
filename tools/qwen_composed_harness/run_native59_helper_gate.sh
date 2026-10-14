#!/usr/bin/env bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/qwen-full-layer-sequence-1014
obj=$base/native59_helper/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
mkdir -p out
sha256sum src/native59_helpers.hpp src/native59.h src/native59_helper_gate.cpp "$obj/Vot_qwen_native59__ALL.a" "$base/libnative59.so" > out/inputs.sha256
c++ -O1 -std=c++17 -pthread -I"$obj" -Isrc -I"$vroot/include" -I"$vroot/include/vltstd" src/native59_helper_gate.cpp "$obj/Vot_qwen_native59__ALL.a" "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" -ldl -o out/helper_gate > out/build.log 2>&1
sha256sum out/helper_gate > out/binary.sha256
# Explicit fixture descriptor bank derived from candidate encoding: AR256 VM word0/base0 then END/base22.
mkdir -p descriptors
for rank in {0..7}; do mkdir -p "descriptors/die$rank"; printf '%s\n' 0000000000000001 0000001600000000 > "descriptors/die$rank/segments.hex"; done
out/helper_gate "$base/libnative59.so" descriptors > out/run.log 2>&1
for bit in 0 6 19 37 43; do out/helper_gate "$base/libnative59.so" descriptors "$bit" > "out/tag_bit${bit}.log" 2>&1; done
cat out/run.log out/tag_bit*.log
