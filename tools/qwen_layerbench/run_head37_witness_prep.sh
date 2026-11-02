#!/usr/bin/env bash
# Run only after component resource admission; one compiler thread per build.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
cd "$root"
sha256sum -c packet.sha256 >input_guard.log 2>&1 || exit 3
packet="$root/input"
build="$root/build"
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export CXX=/usr/bin/g++
"$VL" --version >toolchain.log
/usr/bin/g++ --version >>toolchain.log
failed=0
printf 'START host=%s\n' "$(hostname -s)" >status
mkdir -p "$build"
rtl=("$root/src/qfd_dv_typed_witness_control.sv" "$root/src/qfd_dv_typed_witness_control_head37.sv" "$root/src/qfd_dv_typed_su_observer.sv" "$root/src/tb_qwen_head37_witness_prep.sv")
digest=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["digest"])' "$packet/profile.json")
for mode in legacy plain select phys; do
 args=(-GHEAD=1 "-GDIGEST=64'h$digest")
 if [[ $mode == legacy ]];then args=(-GHEAD=0 -GPAIR=1);fi
 if [[ $mode == select || $mode == phys ]];then args+=(-GSAFE=1 -GSELECT=1);fi
 if [[ $mode == phys ]];then args+=(-GPHYS=1);fi
 if ! /usr/bin/time -v -o "$build/${mode}_build.time" "$VL" --binary --timing -O0 -finline --output-groups 16 -CFLAGS '-O0 -w -fno-var-tracking' -Wno-fatal -j 1 --top-module tb_qwen_head37_witness_prep --Mdir "$build/$mode" "${args[@]}" "${rtl[@]}" >"$build/${mode}_build.log" 2>&1; then echo "BUILD_FAIL $mode" >>status; failed=1;continue;fi
 if [[ $mode == legacy ]];then sets=(legacy);else sets=(enabled_base head);fi
 for set in "${sets[@]}";do
 for stim in "$packet/${set}_"*.txt;do
 name=$(basename "$stim" .txt);fault=1;groups=65
 if [[ $set == head ]];then groups=8;fi
 if [[ $name == *_nominal ]];then fault=0;fi
 if ! "$build/$mode/Vtb_qwen_head37_witness_prep" "+STIM=$stim" "+GROUPS=$groups" "+FAULT=$fault" >"$build/${mode}_${name}.log" 2>&1; then echo "FAIL $mode $name" >>status;failed=1;else echo "PASS $mode $name" >>status;fi
 done
 done
 done

echo "TERMINAL failed=$failed" >>status
exit "$failed"
