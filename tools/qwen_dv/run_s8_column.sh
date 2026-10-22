#!/usr/bin/env bash
set -euo pipefail
out=$1;mode=${2:-pass};mkdir -p "$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
defs=(-DOT_S8_SIM)
case "$mode" in pass);;read0)defs+=(-DOT_S8_COL_MUT_READ0);;*)exit 2;;esac
src=(rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv rtl/test/qwen_dv/s8/tb_s8_column.sv)
"$v" --version > "$out/version.txt"
"$v" --binary --timing -O1 -j ${VJOBS:-4} --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN "${defs[@]}" --top-module tb_s8_column "${src[@]}" -Mdir "$out/obj" -CFLAGS -O0 > "$out/build.log" 2>&1
if [ "$mode" != pass ];then exec "$out/obj/Vtb_s8_column" +seed=7 +cid=22 +cycles=20000;fi
for cid in 0 5 22 63;do
 "$out/obj/Vtb_s8_column" +seed=1 +cid=$cid +cycles=20000 > "$out/cid${cid}.log" 2>&1
 grep -q 'S5_XH3_EQ PASS' "$out/cid${cid}.log"
 grep 'S8_COLUMN_AGES\|S5_XH3_EQ PASS' "$out/cid${cid}.log"
done
echo 'S8_COLUMN READ1 FILL1 exact chain ALL PASS'
