#!/bin/bash
set -eu
verilator -cc --converge-limit 1000 -Wno-fatal --top-module probe --exe probe.cpp --Mdir timing_mutant_build component_sources.sv candidate_timing_mutant.sv probe.sv >timing_mutant_verilate.log 2>&1
make -C timing_mutant_build -f Vprobe.mk -j1 >timing_mutant_make.log 2>&1
set +e
./timing_mutant_build/Vprobe >timing_mutant.log 2>&1
rc=$?
set -e
printf '%s\n' "$rc" >timing_mutant.exit
test "$rc" -eq 2
cat timing_mutant.log
