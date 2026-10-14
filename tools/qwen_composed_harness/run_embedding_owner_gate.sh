#!/usr/bin/env bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/qwen-native-embedding-1014
obj=$base/build-lv6/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
mkdir -p out
sha256sum src/embedding_owner.hpp src/embedding_owner_gate.cpp src/rom_vm_adapter.hpp src/kernel_physical_rows.hpp "$obj/Vot_qwen_tp8_embedding_core__ALL.a" "$obj/sim_hdc_v41x_fastfp_dpi.o" "$base/embedding_program.hex" > out/inputs.sha256
c++ -O1 -std=c++17 -pthread -Isrc -I"$obj" -I/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj -I"$vroot/include" -I"$vroot/include/vltstd" src/embedding_owner_gate.cpp "$obj/Vot_qwen_tp8_embedding_core__ALL.a" "$obj/sim_hdc_v41x_fastfp_dpi.o" "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" "$vroot/include/verilated_dpi.cpp" -o out/embedding_owner > out/build.log 2>&1
sha256sum out/embedding_owner > out/binary.sha256
out/embedding_owner "$base/embedding_program.hex" "$base/vectors" > out/run.log 2>&1
cat out/run.log
