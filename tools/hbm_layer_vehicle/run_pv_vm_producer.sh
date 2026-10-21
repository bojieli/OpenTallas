#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "${1:?output directory}");mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
verilator --binary --timing -j "${OT_THREADS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_pv_vm_producer --Mdir "$OUT/obj" \
 rtl/lib/ot_rst_relay.sv rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_bfqg.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv \
 rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_pstore.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_layer/tb_hbm_pv_vm_producer.sv > "$OUT/build.log" 2>&1
cp results/rtl/hbm_pv_producer_1340/inputs/*.hex "$OUT/"
cd "$OUT"
for m in 0 1 2;do
 "$OUT/obj/Vtb_hbm_pv_vm_producer" +MUT=$m > "$OUT/run_m$m.log" 2>&1
 if [ "$m" = 0 ];then grep -q 'PVROW PASS rows128' "$OUT/run_m$m.log";else grep -q 'PVROW FAIL' "$OUT/run_m$m.log";fi
done
printf '%s\n' 'PVROW_EXPECTATIONS_MET'
