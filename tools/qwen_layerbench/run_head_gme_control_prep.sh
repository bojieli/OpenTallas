#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log
mkdir -p build
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export CXX=/usr/bin/g++
failed=0
for mode in 0 1 2; do
 if ! /usr/bin/time -v -o "build/m${mode}.time" "$VL" --binary --timing -O0 -finline --output-groups 16 -CFLAGS '-O0 -w -fno-var-tracking' -Wno-fatal -j 1 --top-module tb_qwen_head_gme_control --Mdir "build/m${mode}" -GMODE=$mode src/*.sv src/*.v >"build/m${mode}.log" 2>&1; then echo "BUILD_FAIL $mode";exit 1;fi
 for native in 0 1; do
 fault=0
 if [[ $mode != 2 && $native == 1 ]];then fault=1;fi
 if ! "build/m${mode}/Vtb_qwen_head_gme_control" +NATIVE=$native +FAULT=$fault >"build/m${mode}_n${native}.log" 2>&1;then echo "FAIL MODE=$mode NATIVE=$native";failed=1;else echo "PASS MODE=$mode NATIVE=$native";fi
 done
 if [[ $mode == 2 ]];then
 if ! build/m2/Vtb_qwen_head_gme_control +NATIVE=1 +BUSY=1 +FAULT=1 >build/m2_busy.log 2>&1;then echo 'FAIL OWN_BUSY';failed=1;else echo 'PASS OWN_BUSY';fi
 fi
 done
 echo "TERMINAL failed=$failed"
 exit "$failed"
