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
[[ "$mode" != tag ]] || args+=(-DMUT_TAG)
[[ "$mode" != bf16 ]] || args+=(-DMUT_BF16)
"$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_coll_reduce_static --Mdir "$OUT/obj" "${args[@]}" \
 "$P/tb_hgi_coll_reduce_static.sv" "$P/ot_hgi_coll_reduce_static.sv" "$P/ot_hgi_coll_pring_static.sv" "$P/f32add.c" \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log";exit 2; }
if [[ "$mode" != normal ]];then
 if "$OUT/obj/Vtb_hgi_coll_reduce_static" > "$OUT/run.log" 2>&1;then
  echo "mutant unexpectedly passed $mode";exit 1
 fi
 grep -q 'STATIC_REDUCE FAIL' "$OUT/run.log"
 echo "STATIC_REDUCE MUTANT REJECTED $mode"
 exit 0
fi
"$OUT/obj/Vtb_hgi_coll_reduce_static" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^STATIC_REDUCE PASS ' "$OUT/run.log"
for scenario in {1..12};do
 "$OUT/obj/Vtb_hgi_coll_reduce_static" +fault="$scenario" > "$OUT/fault-$scenario.log" 2>&1
 grep -q '^STATIC_REDUCE FAULT PASS ' "$OUT/fault-$scenario.log"
 cat "$OUT/fault-$scenario.log"
done
if "$OUT/obj/Vtb_hgi_coll_reduce_static" +order=1 > "$OUT/order-mutant.log" 2>&1;then
 echo 'order mutant unexpectedly passed';exit 1
fi
grep -q 'STATIC_REDUCE FAIL' "$OUT/order-mutant.log"
echo 'STATIC_REDUCE MUTANT REJECTED pairwise_order'
