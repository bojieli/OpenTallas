#!/bin/bash
set -uo pipefail
OUT=$(realpath "$1")
rc=0
for H in 0 1 2;do
 for P in -4 4;do
  "$OUT/obj$H/Vtb" +PHASE=$P > "$OUT/h${H}p${P}.log" 2>&1
  grep -q "BANK_RELAY_PASS HOPS$H PHASE$P" "$OUT/h${H}p${P}.log"||rc=1
 done
done
"$OUT/obj4/Vtb" +PHASE=-4 > "$OUT/h4p-4.log" 2>&1
grep -q 'BANK_RELAY_FAIL HOPS4 PHASE-4' "$OUT/h4p-4.log"||rc=1
echo "BANK_PHASE40_EXIT $rc"
exit "$rc"
