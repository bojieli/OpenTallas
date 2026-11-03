#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log
mkdir -p build
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export CXX=/usr/bin/g++
/usr/bin/time -v -o build/build.time "$VL" --binary --timing -O0 -finline --output-groups 16 -CFLAGS '-O0 -w -fno-var-tracking' -Wno-fatal -j 1 --top-module tb_qwen_head_xpf37_control --Mdir build/obj src/*.sv >build/build.log 2>&1
failed=0
for mut in 0 1 2;do
 if ! build/obj/Vtb_qwen_head_xpf37_control +MUT=$mut >"build/m${mut}.log" 2>&1;then echo "FAIL MUT=$mut";failed=1;else echo "PASS MUT=$mut";fi
 done
 echo "TERMINAL failed=$failed";exit "$failed"
