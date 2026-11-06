#!/bin/bash
set -eu
cd "$(dirname "$0")"
python3 reset_probe.py
cd obj_modes
vr=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
g++ -O1 -fcoroutines -DVL_TIME_CONTEXT -DVERILATOR=1 -DVM_TIMING=1 -I. -I"$vr/include" -I"$vr/include/vltstd" -c ../directed_reset_stimulus/Vtb_delpipe___024root__0.cpp -o ../directed_reset_stimulus/Vtb_delpipe___024root__0.o > ../directed_reset_stimulus/build.log 2>&1
ar r ../directed_reset_stimulus/Vtb_delpipe__ALL.a ../directed_reset_stimulus/Vtb_delpipe___024root__0.o
g++ verilated.o verilated_timing.o verilated_threads.o ../directed_reset_stimulus/Vtb_delpipe__ALL.a -pthread -lpthread -latomic -o ../directed_reset_stimulus/Vtb_reset
cd ..
./directed_reset_stimulus/Vtb_reset +mode=1 > directed_reset_stimulus/result.log 2>&1
[ "$(grep -c DIRECTED_RESET directed_reset_stimulus/result.log)" = 4 ]
grep SUMMARY directed_reset_stimulus/result.log
