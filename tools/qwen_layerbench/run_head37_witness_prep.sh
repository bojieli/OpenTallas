#!/usr/bin/env bash
# Run only after component resource admission; one compiler thread per build.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
packet=${1:?generated packet directory required}
build=${2:?scratch build directory required}
mkdir -p "$build"
rtl=("$root/rtl/qwen_dv/qfd_dv_typed_witness_control.sv" "$root/rtl/qwen_dv/headprep37/qfd_dv_typed_witness_control_head37.sv" "$root/rtl/qwen_dv/qfd_dv_typed_su_observer.sv" "$root/rtl/test/qwen_dv/tb_qwen_head37_witness_prep.sv")
digest=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["digest"])' "$packet/profile.json")
for mode in legacy plain select phys; do
 args=(-GHEAD=1 "-GDIGEST=64'h$digest")
 if [[ $mode == legacy ]];then args=(-GHEAD=0 -GPAIR=1);fi
 if [[ $mode == select || $mode == phys ]];then args+=(-GSAFE=1 -GSELECT=1);fi
 if [[ $mode == phys ]];then args+=(-GPHYS=1);fi
 verilator --binary --timing -Wno-fatal -j 1 --top-module tb_qwen_head37_witness_prep --Mdir "$build/$mode" "${args[@]}" "${rtl[@]}" >"$build/${mode}_build.log" 2>&1
 if [[ $mode == legacy ]];then sets=(legacy);else sets=(enabled_base head);fi
 for set in "${sets[@]}";do
 for stim in "$packet/${set}_"*.txt;do
 name=$(basename "$stim" .txt);fault=1;groups=65
 if [[ $set == head ]];then groups=8;fi
 if [[ $name == *_nominal ]];then fault=0;fi
 "$build/$mode/Vtb_qwen_head37_witness_prep" "+STIM=$stim" "+GROUPS=$groups" "+FAULT=$fault" >"$build/${mode}_${name}.log" 2>&1
 done
 done
 done
