#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
core=${CORE_OBJ:-/srv/opentallas-scratch/codex/qwen-fullshape-provider-1014/v6_600/full_g3072_su64/obj}
allocator=${ALLOCATOR_OBJ:-/srv/opentallas-scratch/codex/qwen-full-layer-sequence-1014/allocator_v5_0/library/obj}
front=${FRONT59_OBJ:?fresh source-exact ENABLE_NATIVE1 frontend59 object directory}
sector=/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj
pc=/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj
kernel=/srv/opentallas-scratch/codex/qwen-composed-harness-f460-1014/kernel
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
sha256sum src/full_layer.cpp src/rom_vm_adapter.hpp "$core/Vot_hdc_core_vector_weight_native_candidate.h" > out/syntax_inputs.sha256
c++ -std=c++17 -fsyntax-only -I"$core" -I"$allocator" -I"$front" -I"$sector" -I"$pc" -I"$kernel" -Isrc \
 -I"$vroot/include" -I"$vroot/include/vltstd" src/full_layer.cpp > out/syntax.log 2>&1
printf '%s\n' 'PASS_REAL_GENERATED_HEADERS_SYNTAX_ONLY_NOT_EXECUTED_LAYER'
