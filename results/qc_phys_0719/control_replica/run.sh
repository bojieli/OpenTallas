#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --version > tool.txt
verilator --binary --timing -Wno-fatal -j 4 --top-module tb_control --Mdir obj actual_kff.sv tb_control.sv > build.log 2>&1 || exit $?
obj/Vtb_control +MODE=0 > nominal.log 2>&1; n=$?
(ulimit -c 0; obj/Vtb_control +MODE=1 > mutant_d.log 2>&1); d=$?
(ulimit -c 0; obj/Vtb_control +MODE=2 > mutant_cycle.log 2>&1); c=$?
printf 'nominal %s\nmutant_d %s\nmutant_cycle %s\n' "$n" "$d" "$c" > rc.txt
cat nominal.log rc.txt
if [ "$n" != 0 ] || [ "$d" = 0 ] || [ "$c" = 0 ]; then exit 1; fi
grep -q 'MUTANT_D caught' mutant_d.log && grep -q 'MUTANT_CYCLE caught' mutant_cycle.log
