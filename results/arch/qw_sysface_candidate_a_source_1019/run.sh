#!/bin/bash
set -u
mkdir -p logs
hostname > logs/host.txt
iverilog -V > logs/iverilog_version.txt 2>&1
yosys -V > logs/yosys_version.txt 2>&1
sha256sum *.sv *.ys *.py run.sh > logs/inputs.sha256
/usr/bin/time -v -o logs/build.time iverilog -g2012 -s tb -o sim original.sv candidate_a.sv tb.sv > logs/build.log 2>&1 || exit $?
/usr/bin/time -v -o logs/sim.time vvp sim > logs/sim.log 2>&1
rc=$?; echo "$rc" > logs/sim.rc
if [ "$rc" -ne 0 ]; then cat logs/sim.log; exit "$rc"; fi
/usr/bin/time -v -o logs/formal.time yosys -Q -s proof.ys > logs/formal.log 2>&1
rc=$?; echo "$rc" > logs/formal.rc
if [ "$rc" -ne 0 ]; then tail -40 logs/formal.log; exit "$rc"; fi
iverilog -g2012 -s tb -o mutant original.sv mutant_reserved.sv tb.sv > logs/mutant_build.log 2>&1 || exit $?
vvp mutant > logs/mutant.log 2>&1
rc=$?; echo "$rc" > logs/mutant.rc
cat logs/sim.log
tail -8 logs/formal.log
cat logs/mutant.log
if [ "$rc" -eq 0 ]; then exit 3; fi
