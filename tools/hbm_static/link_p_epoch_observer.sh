#!/usr/bin/env bash
set -euo pipefail
model=$(realpath "$1")
observer=$(realpath "$2")
out=$(realpath -m "$3")
include=${VERILATOR_INCLUDE:-$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include}
mkdir -p "$out"
g++ -std=c++20 -O0 -I"$model" -I"$include" -I"$include/vltstd" "$observer" \
 "$model/Vtb_hbm_p_native_producer_static__ALL.a" "$model/verilated.o" "$model/verilated_timing.o" "$model/verilated_threads.o" \
 -pthread -latomic -Wl,--wrap=main -o "$out/p_epoch_observer"
