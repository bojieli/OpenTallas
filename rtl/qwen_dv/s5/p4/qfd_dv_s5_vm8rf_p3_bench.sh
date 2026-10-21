#!/usr/bin/env bash
# QW2-VM8P4 10-21: P4 flat parent qfd_dv_s5_vm8rf vs qfd_dv_s5_vm8fh with the P3 tb (offsets VM1 / BTAB-PROG2 / CROM4), MUT 0 only
# (the landing / reset mutants are the lp bench rtl/qwen_dv/s5/p4/lp/qfd_dv_s5_vm8r_bench.sh).  Fleet only.
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}"
OUT=${1:-vm8rf_p3_out}; mkdir -p "$OUT"
SRCS="rtl/qwen_dv/s5/qfd_dv_s5_vm8fh.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8out.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv rtl/qwen_dv/s5/p4/qfd_dv_s5_vm8rf.sv rtl/qwen_dv/s5/p4/tb_qfd_dv_s5_vm8rf_p3.sv"
${VERILATOR:-verilator} --binary -j ${VL_JOBS:-8} -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 --top-module tb_qfd_dv_s5_vm8rf_p3 $SRCS -Mdir "$OUT/obj0" > "$OUT/build_0.log" 2>&1 \
  && "$OUT/obj0/Vtb_qfd_dv_s5_vm8rf_p3" > "$OUT/mut0.log" 2>&1
r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/mut0.log" 2>/dev/null | head -1); echo "P4FLAT_VS_FH: ${r:-NO_RESULT}"
[ "$r" = "LP_LOCKSTEP PASS" ]; rc=$?; echo "BENCH_EXIT $rc"; exit $rc
