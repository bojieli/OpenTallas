#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../../.." && pwd)
out=$(realpath "$1")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal +define+OT_MEM_NO_INIT --top-module host_su_axi_tb --Mdir "$out/obj_axi" \
 "$root/rtl/hbm_accel/host_static_20261015/su_target/host_su_axi_install.sv" \
 "$root/rtl/hbm_accel/host_static_20261015/su_target/host_su_target.sv" \
 "$root/rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv" \
 "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
 "$out/host_su_axi_tb.sv" > "$out/host_su_axi_build.log" 2>&1
"$out/obj_axi/Vhost_su_axi_tb" +DIR="$out" > "$out/host_su_axi_positive.log" 2>&1
grep -q HOST_SU_AXI_PASS "$out/host_su_axi_positive.log"
echo HOST_SU_AXI_GATE_PASS
