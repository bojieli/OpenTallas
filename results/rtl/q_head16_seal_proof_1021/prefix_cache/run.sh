#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
for kind in candidate mutant_count mutant_prefix; do
 verilator --binary --timing --assert -Wno-fatal --top-module tb -j 2 --Mdir obj_$kind tb.sv "$kind.sv" helpers.sv > build_$kind.log 2>&1
 set +e
 ./obj_$kind/Vtb > run_$kind.log 2>&1
 rc=$?
 set -e
 echo "$rc" > rc_$kind
 echo "$kind rc=$rc"
 tail -5 run_$kind.log
 if [ "$kind" = candidate ] && [ "$rc" != 0 ];then exit 1;fi
 if [ "$kind" != candidate ] && [ "$rc" = 0 ];then echo MUTANT_SURVIVED;exit 2;fi
 if [ "$kind" != candidate ];then grep -q 'H16V seal_bad\|DIFF' run_$kind.log;fi
done
