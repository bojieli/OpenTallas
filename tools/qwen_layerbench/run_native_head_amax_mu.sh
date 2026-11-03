#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS > hash_guard.log
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee compiler_version.log
grep -q 'Verilator 5.050' compiler_version.log
export CXX=g++
"$CXX" --version >> compiler_version.log
/usr/bin/time -v "$VL" --binary --timing -O0 -j 1 --build-jobs 1 -CFLAGS '-O0 -w -fno-var-tracking' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qwen_native_head_amax_mu \
 rtl/qfd_dv_amax_mu.sv rtl/tb_qwen_native_head_amax_mu.sv --Mdir obj > build.log 2>&1
/usr/bin/time -v ./obj/Vtb_qwen_native_head_amax_mu +INPUT=inputs > baseline_and_controls.log 2>&1
grep -q 'PASS_NATIVE_AMAX_MU_COMPONENT' baseline_and_controls.log
for mut in 2 3 4;do grep -q "DETECTED_NATIVE_MUTANT mut=$mut " baseline_and_controls.log;done
printf 'PASS_NATIVE_AMAX_GATE component_and_native_mutants\n'
