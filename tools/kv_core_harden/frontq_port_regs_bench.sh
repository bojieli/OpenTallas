#!/bin/bash
# KVG3-CORES 10-24: ot_qkh_head_frontq_native PORT_REGS=1 vs 0 miter.  usage: frontq_port_regs_bench.sh OUTDIR [MUT]
#   MUT 0: PASS (identical f_t0..3 / pack_fault every edge); MUT 1: swapped Q slice, MUT 2: stuck-zero fault pin (must FAIL)
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$(command -v verilator)}
mkdir -p "$OUT"
D=""; [ "$MUT" = 1 ] && D="-DKVG3_FRONTQ_PRMUT"
[ "$MUT" = 2 ] && D="-DKVG3_FRONTQ_PFMUT"
SRC="$R/rtl/test/kv_core_harden/tb_frontq_port_regs.sv $R/rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv $R/rtl/lib/ot_rst_relay.sv"
"$V" --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_frontq_port_regs $D \
  -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL frontq build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -6
grep -q '^PASS frontq_port_regs' "$OUT/run.log"
