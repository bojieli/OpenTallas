#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?image};mut=${2:-0};vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O2 -j 4 -Wno-fatal +define+OT_MEM_NO_INIT --top-module host_su_cdc_tb -GMUT="$mut" --Mdir "$out/obj_cdc$mut" \
 rtl/hbm_accel/host_static_20261015/transport/ot_hbm_host_cfg_cdc.sv \
 rtl/hbm_accel/host_static_20261015/su_target/{host_su_axi_install,host_su_target}.sv \
 rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 "$out/host_su_cdc_tb.sv" > "$out/cdc_build$mut.log" 2>&1
"$out/obj_cdc$mut/Vhost_su_cdc_tb" +DIR="$out" > "$out/cdc_run$mut.log" 2>&1
cat "$out/cdc_run$mut.log"
grep -q '^HOST_SU_CDC_PASS' "$out/cdc_run$mut.log"
