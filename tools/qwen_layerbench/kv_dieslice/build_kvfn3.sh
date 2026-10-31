#!/bin/bash
# KV-FN-3: build libkvfn3.so (main_kvfn3.cpp + trampolines) for the EXISTING bWc_o3_kv49fn model binary (its objects
# were deleted); run with LD_PRELOAD=libkvfn3.so <that binary> ...  No re-Verilate, no model change.
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-kvtok-2249; K=/srv/opentallas-scratch2/claude/kv-fn-3
S=$D/bWc_o3; EXE=$D/bWc_o3_kv49fn/obj/Vtb_kvslice
VI=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include
cd $K  # holds copies of main_kvfn3.cpp kvfn3_preload.c kvfn3_gen_tramp.sh from tools/qwen_layerbench/kv_dieslice
g++ -fPIC -Os -I$S/obj -I$VI -I$VI/vltstd -DVERILATOR=1 -DVM_COVERAGE=0 -DVM_SC=0 -DVM_TIMING=1 -DVM_TRACE=0 -DVM_TRACE_FST=0 -DVM_TRACE_VCD=0 -DVM_TRACE_SAIF=0 -DVM_VPI=0 -faligned-new -fcf-protection=none -w -O1 -DVL_TIME_CONTEXT -fcoroutines -c main_kvfn3.cpp -o main_kvfn3.o
bash kvfn3_gen_tramp.sh $EXE main_kvfn3.o
gcc -fPIC -O1 -c kvfn3_preload.c -o preload.o
gcc -c tramp.S -o tramp.o
g++ -shared -o libkvfn3.so preload.o tramp.o main_kvfn3.o -ldl
nm -u libkvfn3.so | grep -E '_ZN(11Vtb_kvslice|16VerilatedContext|9Verilated)' && { echo "unresolved model symbols"; exit 1; } || true
sha256sum $EXE libkvfn3.so main_kvfn3.cpp > build.sha256
echo BUILD_OK $(date)
