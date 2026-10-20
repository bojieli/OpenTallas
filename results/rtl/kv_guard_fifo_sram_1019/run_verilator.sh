#!/usr/bin/env bash
set -euo pipefail
test "$#" -ge 1 || { echo "usage: $0 OUT [MUTANT]" >&2; exit 2; }
TASK_ROOT=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
TASK_OUT=$(realpath -m -- "$1")
TASK_MUTANT=${2:-0}
TASK_VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
case "$TASK_MUTANT" in 0|1|2|3) ;; *) echo "invalid mutant" >&2; exit 2;; esac
test ! -e "$TASK_OUT" || { echo "refusing to overwrite $TASK_OUT" >&2; exit 2; }
mkdir -p -- "$TASK_OUT"
"$TASK_VERILATOR" --version | tee "$TASK_OUT/tool.txt"
grep -q '^Verilator 5\.050 ' "$TASK_OUT/tool.txt" || { echo 'requires Verilator 5.050' >&2; exit 2; }
TASK_SOURCES=(
 "$TASK_ROOT/physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v"
 "$TASK_ROOT/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv"
 "$TASK_ROOT/results/rtl/kv_guard_fifo_sram_1019/qkd_host_guard_fifo_ref.sv"
 "$TASK_ROOT/results/rtl/kv_guard_fifo_sram_1019/tb_guard_fifo_sram.sv"
)
sha256sum "${TASK_SOURCES[@]}" > "$TASK_OUT/source_sha256.txt"
"$TASK_VERILATOR" --binary --timing -j 4 -Wno-fatal \
 --top-module tb_guard_fifo_sram --Mdir "$TASK_OUT/obj" \
 +define+OT_HOST_GUARD_SRAM_DEFAULT=1 \
 "+define+OT_HOST_GUARD_SRAM_MUTANT=$TASK_MUTANT" \
 "${TASK_SOURCES[@]}" > "$TASK_OUT/build.log" 2>&1
set +e
(ulimit -c 0; "$TASK_OUT/obj/Vtb_guard_fifo_sram") > "$TASK_OUT/run.log" 2>&1
TASK_STATUS=$?
set -e
printf '%s\n' "$TASK_STATUS" > "$TASK_OUT/exit_code.txt"
cat "$TASK_OUT/run.log"
if test "$TASK_MUTANT" = 0; then
 test "$TASK_STATUS" = 0
 grep -q 'PASS cycles=100140 .*zero_added_edges=1' "$TASK_OUT/run.log"
else
 test "$TASK_STATUS" != 0
 grep -q 'cycle .*\(data got\|control got\)' "$TASK_OUT/run.log"
fi
printf 'GUARD_FIFO_VERILATOR_PASS mutant=%s observed_exit=%s\n' "$TASK_MUTANT" "$TASK_STATUS" | tee "$TASK_OUT/verdict.txt"
