#!/usr/bin/env bash
set -euo pipefail
output=${1:?fresh output directory}
front=/srv/opentallas-scratch/codex/native-services-front59-1014/library-v1/obj
kernel=/srv/opentallas-scratch/codex/qwen-composed-harness-f460-1014/kernel
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
[[ ! -e "$output" ]];mkdir -p "$output"
sha256sum src/services_vm_adapter.hpp src/frontend59_vm_syntax.cpp "$front/Vot_qwen_tp8_native_services_frontend_native59.h" "$kernel/Vot_qwen_tp8_attention_service.h" > "$output/inputs.sha256"
c++ -std=c++17 -fsyntax-only -Isrc -I"$front" -I"$kernel" -I"$vroot/include" -I"$vroot/include/vltstd" src/frontend59_vm_syntax.cpp > "$output/syntax.log" 2>&1
printf '%s\n' 'PASS_ACTUAL_FRONTEND59_KERNEL_VM_PORT_ABI_ONLY_NOT_EXECUTION'
