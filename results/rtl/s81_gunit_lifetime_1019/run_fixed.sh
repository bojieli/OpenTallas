#!/bin/bash
set -euo pipefail
v=$(command -v verilator)
"$v" --version
for kind in fixed mut_same_edge mut_history; do
 cp vehicle.sv "$kind.sv"
 if [ "$kind" = mut_same_edge ]; then sed -i 's/(wbase \&\& wrow == {ss\[24\], sw\[24\]})/(1\x27b0)/' "$kind.sv"; fi
 if [ "$kind" = mut_history ]; then sed -i "s/wbase \&\& wrow == 2'(lr)/wbase \&\& wrow == 2'(lr) \&\& wrow == {ss[24], sw[24]}/" "$kind.sv"; fi
 "$v" --binary --timing --top-module tb -Wno-fatal -DOT_MEM_NO_INIT -DFIXED --x-initial unique -j 2 --Mdir "obj_$kind" "$kind.sv" tb.sv macro.v >"build_$kind.log" 2>&1
 set +e
 "./obj_$kind/Vtb" +verilator+seed+17 +verilator+rand+reset+2 >"$kind.log" 2>&1
 rc=$?
 set -e
 cat "$kind.log"
 if [ "$kind" = fixed ]; then test "$rc" = 0; grep -q CORRECTED_LIFETIME_PASS "$kind.log"; else test "$rc" != 0; grep -Eq 'WINDOW_FAIL|SELECTOR_HISTORY_FAIL' "$kind.log"; fi
 echo "$kind EXPECTED_RESULT rc=$rc"
done
