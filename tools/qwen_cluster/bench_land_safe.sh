#!/bin/bash
# usage: bench_land_safe.sh OUTDIR [both|pass|mut] [WD]
#   both (default): MUT0 must pass and MUT1 (wrong read K3) must fail -> SAFE_LAND_EXIT 0
#   pass: MUT0 only, prints SAFE_LAND_PASS MUT0 ; mut: MUT1 only, prints SAFE_LAND_FAIL MUT1 errors=N
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MODE=${2:-both}
WD=${3:-258}
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
case "$MODE" in pass) MS="0";; mut) MS="1";; *) MS="0 1";; esac
rc=0
for M in $MS; do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GMUT=$M -GWD=$WD -Mdir "$OUT/obj$M" rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/qfd_c_land_safe.sv rtl/test/tb_qfd_c_land_safe.sv > "$OUT/build$M.log" 2>&1 || { rc=1; continue; }
 "$OUT/obj$M/Vtb" > "$OUT/mut$M.log" 2>&1
 cat "$OUT/mut$M.log"
 if [[ $M == 0 ]]; then grep -q 'SAFE_LAND_PASS MUT0' "$OUT/mut$M.log" || rc=1
 else grep -q 'SAFE_LAND_FAIL MUT1' "$OUT/mut$M.log" || rc=1; fi
done
echo "SAFE_LAND_EXIT $rc WD=$WD MODE=$MODE"
if [[ $MODE == mut ]]; then [[ $rc == 0 ]] && exit 1; exit 0; fi
exit "$rc"
