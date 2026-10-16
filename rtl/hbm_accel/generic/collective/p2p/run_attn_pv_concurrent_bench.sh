#!/usr/bin/env bash
# Concurrent Qwen8192 PV tree: production exact (SCEN 0) + 3 fault scenarios must PASS; 3 RTL mutants must FAIL.
# usage: run_attn_pv_concurrent_bench.sh OUT
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
src=("$P/tb_hgi_attn_pv_concurrent.sv" "$P/ot_hgi_attn_pv_concurrent.sv" "$P/ot_hgi_coll_pring_static.sv" "$P/f32add.c"
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
sha256sum "${src[@]}" "$0" > "$OUT/source.sha256"
build(){ "$V" --binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_attn_pv_concurrent \
  --Mdir "$OUT/$1" "${@:2}" "${src[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -30 "$OUT/$1.build.log"; exit 2; }; }
rc=0
for s in ${SCENS:-0 1 2 3}; do build scen$s -GSCEN=$s
 "$OUT/scen$s/Vtb_hgi_attn_pv_concurrent" > "$OUT/scen$s.log" 2>&1 || true; grep -E "ATTN_PV_CONCURRENT|Fatal|mismatch" "$OUT/scen$s.log" | head -2
 grep -q "ATTN_PV_CONCURRENT .*PASS" "$OUT/scen$s.log" || rc=1; rm -rf "$OUT/scen$s"; done
for m in ${MUTS-MUT_PAIR MUT_SLOT MUT_DATA}; do build $m -G$m=1
 if "$OUT/$m/Vtb_hgi_attn_pv_concurrent" > "$OUT/$m.log" 2>&1 && grep -q "PASS" "$OUT/$m.log"; then echo "$m SURVIVED"; rc=1; else echo "$m rejected: $(grep -m1 -E 'Fatal|mismatch|fault' "$OUT/$m.log")"; fi; rm -rf "$OUT/$m"; done
[ $rc = 0 ] && echo "ATTN_PV_CONCURRENT GATE PASS" || { echo "ATTN_PV_CONCURRENT GATE FAIL"; exit 1; }
