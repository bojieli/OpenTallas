#!/bin/bash
set -uo pipefail
OUT=$(mkdir -p "$1"&&realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
err=0
for M in 0 1;do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GMUT=$M -Mdir "$OUT/obj$M" rtl/physical/qcluster/qfd_c_land_safe.sv rtl/physical/qcluster/qfd_c_bank_forward_safe.sv rtl/test/tb_qfd_c_bank_forward_safe.sv > "$OUT/build$M.log" 2>&1||{ err=1;continue; }
 for P in -4 0 4;do
  "$OUT/obj$M/Vtb" +PHASE=$P > "$OUT/m${M}p$P.log" 2>&1
  if [[ $M == 0 ]];then grep -q "BANK_FORWARD_PASS MUT0 PHASE$P" "$OUT/m${M}p$P.log"||err=1
  else grep -q "BANK_FORWARD_FAIL MUT1 PHASE$P" "$OUT/m${M}p$P.log"||err=1;fi
 done
done
echo "BANK_FORWARD_EXIT $err"
exit "$err"
