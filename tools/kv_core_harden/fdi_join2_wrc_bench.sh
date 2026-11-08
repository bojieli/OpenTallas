#!/bin/bash
# DIE-KV-93 11-08: ot_fdi_join2 RP_COPIES=16 + WR_COPIES=16 vs original, +1 edge lock-step.  usage: fdi_join2_rpc_bench.sh OUTDIR [MUT]  (MUT 1 must FAIL)
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$(command -v verilator)}
mkdir -p "$OUT"
D=""; [ "$MUT" = 1 ] && D="-DKV93_WRC_MUT"
"$V" --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_fdi_join2_wrc $D \
  -Mdir "$OUT/obj" -o Vtb "$R/rtl/test/kv_core_harden/tb_fdi_join2_wrc.sv" "$R/rtl/physical/ot_fdi_join2.sv" > "$OUT/build.log" 2>&1 \
  || { tail -30 "$OUT/build.log"; echo "FAIL fdi build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -6
grep -q '^PASS fdi_join2_wrc' "$OUT/run.log"
