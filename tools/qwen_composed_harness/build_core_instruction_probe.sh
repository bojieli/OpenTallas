#!/usr/bin/env bash
# Reuse the genuine existing generated PCH. Never reparse the giant root header
# or modify an owned model/PCH build. An invalid PCH is a hard failure.
set -euo pipefail
core=${1:?actual generated object directory with completed PCH}
output=${2:?fresh probe output directory}
[[ ! -e "$output" ]];mkdir -p "$output"
pch=Vot_hdc_core_vector_weight_native_candidate__pch.h.fast
[[ -s "$core/$pch.gch" ]]
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
sha256sum src/core_instruction_probe.cpp src/core_instruction_probe.hpp "$core/$pch.gch" "$core/Vot_hdc_core_vector_weight_native_candidate___024root.h" "$core/Vot_hdc_core_vector_weight_native_candidate.h" > "$output/inputs.sha256"
g++ -Os -O0 -I"$core" -Isrc -I"$vroot/include" -I"$vroot/include/vltstd" -DVERILATOR=1 -DVM_COVERAGE=0 -DVM_SC=0 -DVM_TIMING=0 -DVM_TRACE=0 -DVM_TRACE_FST=0 -DVM_TRACE_VCD=0 -DVM_TRACE_SAIF=0 -DVM_VPI=0 -faligned-new -fcf-protection=none -Werror=invalid-pch -include "$core/$pch" -c src/core_instruction_probe.cpp -o "$output/core_instruction_probe.o" > "$output/build.log" 2>&1
sha256sum "$output/core_instruction_probe.o" >> "$output/inputs.sha256"
printf '%s\n' 'PASS_COMPILED_READ_ONLY_ACTUAL_GENERATED_ROOT_PROBE_NOT_EXECUTED_LAYER'
