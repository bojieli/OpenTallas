#!/usr/bin/env bash
# QW-SLICE2W 10-21: lockstep bench qfd_dv_s5_vm8fh (flat) vs qfd_dv_s5_vm8q (P3) + mutants 1, 2.
# Run on the FLEET (ot-run), never on localhost.  Exit 0 iff MUT 0 PASSES and every mutant FAILS.
#   bash rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q_bench.sh OUTDIR   (SIM=verilator default; VERILATOR, VL_JOBS, MUTS overrides)
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../../../.." && pwd))}"
OUT=${1:-vm8q_bench_out}; mkdir -p "$OUT"; SIM=${SIM:-verilator}; rc=0
SRCS="rtl/qwen_dv/s5/qfd_dv_s5_vm8fh.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8out.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv rtl/qwen_dv/s5/p3/tb_qfd_dv_s5_vm8q.sv"
for m in ${MUTS:-0 1 2}; do
  if [ "$SIM" = verilator ]; then
    ${VERILATOR:-verilator} --binary -j ${VL_JOBS:-8} -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 --top-module tb_qfd_dv_s5_vm8q -GMUT=$m $SRCS -Mdir "$OUT/obj$m" > "$OUT/build_$m.log" 2>&1 \
      && "$OUT/obj$m/Vtb_qfd_dv_s5_vm8q" > "$OUT/mut$m.log" 2>&1
  else
    iverilog -g2012 -I. -o "$OUT/sim$m" -s tb_qfd_dv_s5_vm8q -Ptb_qfd_dv_s5_vm8q.MUT=$m $SRCS > "$OUT/build_$m.log" 2>&1 \
      && vvp -n "$OUT/sim$m" > "$OUT/mut$m.log" 2>&1
  fi
  r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/mut$m.log" 2>/dev/null | head -1)
  echo "MUT $m: ${r:-NO_RESULT (see $OUT/build_$m.log)}"
  if [ $m -eq 0 ]; then [ "$r" = "LP_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "LP_LOCKSTEP FAIL" ] || rc=1; fi
done
echo "BENCH_EXIT $rc"; exit $rc
