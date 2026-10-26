#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd);cd "$root"
out=$(realpath -m "${1:?output directory}");mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 rtl/hbm_accel/loader/service_native/ot_hbm_router_ids_static.sv
 rtl/hbm_accel/loader/service_native/ot_hbm_router_ids_static_2src.sv
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer_rel.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/test/hbm_idx_static/tb_hbm_router_ids_static_2src.sv)
for tag in alt0 alt1 alt2 pair0 pair3;do
 sm=${tag: -1};pair=0;[[ "$tag" = pair* ]] && pair=1
 "$VL" --binary --timing -Wno-fatal -j 4 --top-module tb_hbm_router_ids_static_2src -GXRT=2 -GCOLLAR=1 -GSMUT=$sm -GPAIR=$pair --Mdir "$out/obj-$tag" "${src[@]}" > "$out/build-$tag.log" 2>&1
 set +e
 "$out/obj-$tag/Vtb_hbm_router_ids_static_2src" > "$out/run-$tag.log" 2>&1
 rc=$?
 set -e
 if [ "$sm" = 0 ];then [ "$rc" = 0 ] || { tail -10 "$out/run-$tag.log";exit 1; };else [ "$rc" != 0 ] || { echo "MUTANT_NOT_CAUGHT $tag";exit 1; };fi
 tail -4 "$out/run-$tag.log"
done
echo 'ROUTER_IDS_2SRC_GATE PASS'
