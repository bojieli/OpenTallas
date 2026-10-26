#!/bin/bash
set -eu
verilator -cc --converge-limit 1000 -Wno-fatal --top-module probe --exe probe.cpp --Mdir build component_sources.sv qfd_res_train_static.sv probe.sv >verilate.log 2>&1
make -C build -f Vprobe.mk -j1 >make.log 2>&1
./build/Vprobe >positive.log 2>&1
cat positive.log
