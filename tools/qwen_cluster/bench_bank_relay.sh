#!/bin/bash
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
rc=0
for H in 0 1 2 4;do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GHOPS=$H -Mdir "$OUT/obj$H" rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/qfd_c_land_safe.sv rtl/test/tb_qfd_c_bank_relay.sv > "$OUT/build$H.log" 2>&1 || { rc=1;continue; }
 if [[ $H == 4 ]];then phases="-1 0";else phases="-1 0 1";fi
 for P in $phases;do
  "$OUT/obj$H/Vtb" +PHASE=$P > "$OUT/h${H}p${P}.log" 2>&1
  if [[ $H == 4 ]];then grep -q "BANK_RELAY_FAIL HOPS4 PHASE$P" "$OUT/h${H}p${P}.log"||rc=1
  else grep -q "BANK_RELAY_PASS HOPS$H PHASE$P" "$OUT/h${H}p${P}.log"||rc=1;fi
 done
done
echo "BANK_RELAY_EXIT $rc"
exit "$rc"
