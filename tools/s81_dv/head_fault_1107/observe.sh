#!/bin/bash
set -u
cd "$(dirname "$0")"
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
tag=${OBSERVE_TAG:-observe}
[ ! -e "${tag}_build.log" ] || exit 95
g++ -std=c++20 -O0 -fcoroutines -pthread -Iobj -I"$V/include" -I"$V/include/vltstd" observe.cpp obj/Vhead_guard_tb__ALL.a obj/verilated.o obj/verilated_timing.o obj/verilated_threads.o -o "$tag" > "${tag}_build.log" 2>&1
rc=$?; echo "$rc" > "${tag}_build.rc"
[ "$rc" -eq 0 ] || exit "$rc"
"./$tag" > "${tag}_TT.log" 2>&1
rc=$?; echo "$rc" > "${tag}_TT.rc"
[ "$rc" -eq 0 ] || exit "$rc"
"./$tag" +FF > "${tag}_FF.log" 2>&1
rc=$?; echo "$rc" > "${tag}_FF.rc"
exit "$rc"
