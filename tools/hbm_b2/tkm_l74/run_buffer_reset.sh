#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");mkdir -p "$o"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for m in 0 1 2;do
 "$v" --binary --timing -j 2 -Wno-fatal --top-module tb_tkm_buffer_reset -GMUT=$m --Mdir "$o/obj$m" tools/hbm_b2/tkm_l74/tb_tkm_buffer_reset.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_buffer.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$o/build$m.log" 2>&1
 set +e;"$o/obj$m/Vtb_tkm_buffer_reset" > "$o/run$m.log" 2>&1;rc=$?;set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ] || { cat "$o/run$m.log";exit 1; };else [ "$rc" != 0 ] || { echo "MUT$m SURVIVED";exit 1; };fi
 cat "$o/run$m.log"
done
