#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log
mkdir -p build
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export CXX=/usr/bin/g++
/usr/bin/time -v -o build/build.time "$VL" --binary --timing -O0 -finline --output-groups 16 -CFLAGS '-O0 -w -fno-var-tracking' -Wno-fatal -j 1 --top-module tb_head_stream_ring --Mdir build/obj src/*.sv >build/build.log 2>&1
failed=0
for row in '0 0 1' '-1 0 0' '0 1 0' '1 0 1';do
 read -r phase align fault <<<"$row"
 if ! /usr/bin/time -v -o "build/p${phase}_a${align}.time" build/obj/Vtb_head_stream_ring +PHASE=$phase +ALIGN=$align +FAULT=$fault >"build/p${phase}_a${align}.log" 2>&1;then echo "FAIL phase=$phase align=$align";failed=1;else echo "PASS phase=$phase align=$align";fi
 done
 echo "TERMINAL failed=$failed";exit "$failed"
