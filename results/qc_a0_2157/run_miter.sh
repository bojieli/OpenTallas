#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for v in nominal mutant;do
 src=ot_qwen_tile_lsl_sync_fault.sv
 if [ "$v" = mutant ];then
   sed "s/lfault <= lf_raw/lfault <= lf_raw ^ 8'h01/" "$src" > mutant.sv;src=mutant.sv
 fi
 verilator --binary --timing --top-module tb --Mdir obj_$v -j 8 -Wno-fatal $(cat sources.txt) "$src" tb_lsl_sync.sv > build_$v.log 2>&1
 set +e
 ./obj_$v/Vtb > sim_$v.log 2>&1
 rc=$?
 set -e
 cat sim_$v.log
 if [ "$v" = nominal ];then test $rc = 0;else test $rc != 0;fi
done
