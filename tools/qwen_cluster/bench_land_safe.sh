#!/bin/bash
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
rc=0
for M in 0 1; do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GMUT=$M -Mdir "$OUT/obj$M" rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/qfd_c_land_safe.sv rtl/test/tb_qfd_c_land_safe.sv > "$OUT/build$M.log" 2>&1 || { rc=1; continue; }
 "$OUT/obj$M/Vtb" > "$OUT/mut$M.log" 2>&1
 if [[ $M == 0 ]]; then grep -q 'SAFE_LAND_PASS MUT0' "$OUT/mut$M.log" || rc=1
 else grep -q 'SAFE_LAND_FAIL MUT1' "$OUT/mut$M.log" || rc=1; fi
done
echo "SAFE_LAND_EXIT $rc"
exit "$rc"
