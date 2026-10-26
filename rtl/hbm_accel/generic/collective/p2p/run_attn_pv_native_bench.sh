#!/usr/bin/env bash
set -euo pipefail
ROOT=${REDUCE_STATIC_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
OUT=$(realpath -m "$1");shift
mkdir -p "$OUT"
cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
mode=${1:-normal}
args=()
[[ "$mode" != carry ]] || args+=(-GMUT_CARRY=1)
"$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_attn_pv_native --Mdir "$OUT/obj" "${args[@]}" \
 "$P/ot_hgi_attn_pv_pkg.sv" "$P/tb_hgi_attn_pv_native.sv" "$P/ot_hgi_attn_pv_native.sv" "$P/ot_hgi_coll_reduce_static.sv" "$P/ot_hgi_coll_pring_static.sv" "$P/f32add.c" \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log";exit 2; }
"$OUT/obj/Vtb_hgi_attn_pv_native" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
if [[ "$mode" == carry ]];then
 grep -q '^ATTN_NATIVE MUTANT REJECTED ' "$OUT/run.log"
else
 grep -q '^ATTN_NATIVE PASS ' "$OUT/run.log"
 "$OUT/obj/Vtb_hgi_attn_pv_native" +mutant=1 > "$OUT/localfirst.log" 2>&1
 grep -q '^ATTN_NATIVE MUTANT REJECTED ' "$OUT/localfirst.log"
 "$OUT/obj/Vtb_hgi_attn_pv_native" +mutant=2 > "$OUT/earlypub.log" 2>&1
 grep -q '^ATTN_NATIVE EARLYPUB REJECTED' "$OUT/earlypub.log"
 cat "$OUT/localfirst.log" "$OUT/earlypub.log"
fi
