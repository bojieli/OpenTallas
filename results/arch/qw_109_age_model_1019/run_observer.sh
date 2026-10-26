#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for mode in observed PHASE;do
 opts=()
 if [[ "$mode" == PHASE ]];then opts+=(+define+MUT_PHASE);fi
 verilator --binary --timing -j 2 -Wno-fatal "${opts[@]}" --top-module mechanism_tb --Mdir "obj_$mode" mechanism_tb.sv original_publish.sv source/059_qfd_fwd_lane.sv source/005_ot_hdc_cg.sv >"build_$mode.log" 2>&1
 set +e
 "./obj_$mode/Vmechanism_tb" >"run_$mode.log" 2>&1
 result=$?
 set -e
 echo "$result" >"exit_$mode.txt"
done
