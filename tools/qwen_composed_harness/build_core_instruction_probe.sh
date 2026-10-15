#!/usr/bin/env bash
# Build a read-only probe against the actual model. Flat LV6 must reuse its
# generated PCH; hierarchical LV6 can compile the smaller root header directly.
set -euo pipefail
core=${1:?actual generated object directory with completed PCH}
output=${2:?fresh probe output directory}
[[ ! -e "$output" ]];mkdir -p "$output"
core=$(realpath "$core")
output=$(realpath "$output")
pch=Vot_hdc_core_vector_weight_native_candidate__pch.h.fast
# Flat LV6 needs its huge generated PCH. A hierarchical root is smaller and
# Verilator does not necessarily emit a PCH: compile that actual header directly.
pch_flags=()
if [[ -d "$core/Vot_hdc_fadd" ]]; then
 # Hierarchical PCHs are compiled with the model's optimization flags and may
 # be incompatible with this deliberately small read-only probe.
 :
elif [[ -s "$core/$pch.gch" ]]; then
 pch_flags=(-Werror=invalid-pch -include "$core/$pch")
 sha256sum "$core/$pch.gch" > "$output/pch.sha256"
else
 echo "flat core requires its generated PCH" >&2; exit 2
fi
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
sha256sum src/core_instruction_probe.cpp src/core_instruction_probe.hpp "$core/Vot_hdc_core_vector_weight_native_candidate___024root.h" "$core/Vot_hdc_core_vector_weight_native_candidate.h" > "$output/inputs.sha256"
g++ -Os -O0 -I"$core" -Isrc -I"$vroot/include" -I"$vroot/include/vltstd" -DVERILATOR=1 -DVM_COVERAGE=0 -DVM_SC=0 -DVM_TIMING=0 -DVM_TRACE=0 -DVM_TRACE_FST=0 -DVM_TRACE_VCD=0 -DVM_TRACE_SAIF=0 -DVM_VPI=0 -faligned-new -fcf-protection=none "${pch_flags[@]}" -c src/core_instruction_probe.cpp -o "$output/core_instruction_probe.o" > "$output/build.log" 2>&1
sha256sum "$output/core_instruction_probe.o" >> "$output/inputs.sha256"
printf '%s\n' 'PASS_COMPILED_READ_ONLY_ACTUAL_GENERATED_ROOT_PROBE_NOT_EXECUTED_LAYER'
