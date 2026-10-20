#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:?output directory}");mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version > "$out/verilator.txt"
src=(rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 rtl/hbm_accel/loader/service_native/ot_hbm_router_ids_static.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer_rel.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/test/hbm_idx_static/tb_hbm_router_ids_static.sv)
rc_all=0
for profile in raw am_pin;do
 opts=();[ "$profile" = raw ] || opts=(-GXRT=2 -GCOLLAR=1)
 "$VL" --binary --timing -Wno-fatal -j 4 --top-module tb_hbm_router_ids_static "${opts[@]}" --Mdir "$out/obj-$profile" "${src[@]}" > "$out/build-$profile.log" 2>&1
for m in 0 1 2 3 4 5 6;do
 set +e
 "$out/obj-$profile/Vtb_hbm_router_ids_static" +mutant=$m > "$out/$profile-run$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ] || rc_all=1;else [ "$rc" != 0 ] || rc_all=1;fi
 tail -4 "$out/$profile-run$m.log"
done
done
sha256sum "${src[@]}" > "$out/sources.sha256"
exit "$rc_all"
