#!/bin/bash
set -uo pipefail
OUT=$(mkdir -p "$1"&&realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
err=0
for M in 0 1;do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GMUT=$M -Mdir "$OUT/obj$M" rtl/physical/qcluster/qfd_c_xstn_safe.sv rtl/physical/qcluster/qfd_c_stn.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv rtl/test/tb_qfd_c_xstn_safe.sv > "$OUT/build$M.log" 2>&1||{ err=1;continue; }
 "$OUT/obj$M/Vtb" > "$OUT/mut$M.log" 2>&1
 if [[ $M == 0 ]];then grep -q 'SAFE_XSTN_PASS MUT0' "$OUT/mut$M.log"||err=1
 else grep -q 'SAFE_XSTN_FAIL MUT1' "$OUT/mut$M.log"||err=1;fi
done
echo "SAFE_XSTN_EXIT $err"
exit "$err"
