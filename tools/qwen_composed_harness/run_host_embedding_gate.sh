#!/usr/bin/env bash
set -euo pipefail
hostbase=/srv/opentallas-scratch/codex/qwen-native-host-callable-1014
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include
host=$hostbase/full8bb9a6c00-compiledO1/obj
board=$hostbase/boardd4a77a6c7/obj
alloc=$hostbase/native-host-owner-models/allocator
cohort=$hostbase/native-host-owner-models/cohort
embed=$PWD/embedding/obj
mkdir -p out
sha256sum src/* embedding/obj/*.h embedding/obj/*__ALL.a embedding/obj/sim_hdc_v41x_fastfp_dpi.o embedding/embedding_program.hex embedding/vectors/token0/*.hex "$host/Vqkd_host_token_service__ALL.a" "$board/Vqkd_host_board_port_fixture__ALL.a" "$alloc/Vot_qwen_tp8_token_epoch_allocator__ALL.a" "$cohort/Vot_qwen_tp8_token_cohort__ALL.a" > out/inputs.sha256
g++ -O1 -std=c++20 -pthread -Isrc -I"$host" -I"$board" -I"$alloc" -I"$cohort" -I"$embed" -I"$vroot" -I"$vroot/vltstd" src/host_embedding_gate.cpp "$host/Vqkd_host_token_service__ALL.a" "$board/Vqkd_host_board_port_fixture__ALL.a" "$alloc/Vot_qwen_tp8_token_epoch_allocator__ALL.a" "$cohort/Vot_qwen_tp8_token_cohort__ALL.a" "$embed/Vot_qwen_tp8_embedding_core__ALL.a" "$embed/sim_hdc_v41x_fastfp_dpi.o" "$vroot/verilated.cpp" "$vroot/verilated_threads.cpp" "$vroot/verilated_dpi.cpp" -o out/host_embedding > out/build.log 2>&1
sha256sum out/host_embedding > out/binary.sha256
out/host_embedding embedding/embedding_program.hex embedding/vectors out/actual > out/run.log 2>&1
cat out/run.log
