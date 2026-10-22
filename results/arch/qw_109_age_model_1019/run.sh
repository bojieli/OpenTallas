#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > verilator_version.txt
for mode in base K STAGE;do
 opts=()
 if [[ "$mode" != base ]];then opts+=("+define+MUT_$mode");fi
 verilator --binary --timing -j 2 -Wno-fatal "${opts[@]}" --top-module mechanism_tb --Mdir "obj_$mode" mechanism_tb.sv original_publish.sv source/059_qfd_fwd_lane.sv source/005_ot_hdc_cg.sv >"build_$mode.log" 2>&1
 set +e
 "./obj_$mode/Vmechanism_tb" >"run_$mode.log" 2>&1
 result=$?
 set -e
 echo "$result" > "exit_$mode.txt"
done
