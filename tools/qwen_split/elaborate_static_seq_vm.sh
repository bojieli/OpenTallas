#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory}
mkdir "$out"
cd "$root"
verilator --lint-only --timing -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -Wno-fatal -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Irtl/hdc \
 --top-module qfd_seq_su_vm_static -f tools/qwen_split/static_seq_vm.f > "$out/compile.log" 2>&1
echo PASS_ACTUAL_STATIC_SEQ_NOX_VM_ELABORATION_ONLY
