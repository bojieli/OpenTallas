#!/bin/bash
# Run one built A0 equivalence bench case.  usage: run.sh BUILDDIR LABEL [plusargs...]
#   e.g. run.sh nk_asbound hard +KRL=2 +KSKEW=0     (kit as hardened: 2 reset landing stages, same rst_n release)
#        run.sh nk_asbound aligned +KRL=2 +KSKEW=-1 (kit rst_n released 1 cycle earlier: core reset releases aligned)
#        run.sh nk_asbound mut1 +KRL=2 +KSKEW=-1 +MUT=1   (must FAIL)
set -uo pipefail
B=$(realpath "$1"); L=$2; shift 2
/usr/bin/time -v "$B/obj/Vtb_a0_equiv" +OT_ROM_DIR="$B/rom" "$@" > "$B/run_$L.log" 2>&1
grep '^A0EQ_\(PASS\|FAIL\|COUNTS\|RESET\|SHIFT\|MISMATCH \)\|%Fatal\|%Error\|Maximum resident\|Elapsed' "$B/run_$L.log"
