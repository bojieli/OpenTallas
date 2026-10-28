#!/bin/bash
# usage: run.sh BUILDDIR LABEL [plusargs...]   e.g. run.sh b_nk mut0 ; run.sh b_nk mut1 +ICG_MUT=1 (must FAIL)
set -uo pipefail
B=$(realpath "$1"); L=$2; shift 2
/usr/bin/time -v "$B/obj/Vtb_a0_icg" +OT_ROM_DIR="$B/rom" "$@" > "$B/run_$L.log" 2>&1
grep '^A0ICG_\(PASS\|FAIL\|COUNTS\|ACTIVITY\|STRICT\|QMISMATCH\)\|%Fatal\|%Error\|Maximum resident\|Elapsed' "$B/run_$L.log"
