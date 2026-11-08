#!/bin/bash
# DIE-KV-93 11-08: ot_qkh_head_frontq_native PORT_NRS=2 vs PORT_NRS=1 (+1 edge) lock-step bench.
#   usage: frontq_port_nrs_bench.sh OUTDIR [MUT]   MUT 0: PASS; MUT 1: ports compared in reverse order (must FAIL)
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$(command -v verilator)}
mkdir -p "$OUT"
D=""; [ "$MUT" = 1 ] && D="-DKV93_NRS_MUT"
SRC="$R/rtl/test/kv_core_harden/tb_frontq_port_nrs.sv $R/rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv $R/rtl/lib/ot_rst_relay.sv"
"$V" --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_frontq_port_nrs $D \
  -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL frontq build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -6
grep -q '^PASS frontq_port_nrs' "$OUT/run.log"
