#!/bin/bash
set -eu
mkdir -p logs_directed
sha256sum original.sv candidate_a.sv tb_directed.sv run_directed.sh > logs_directed/inputs.sha256
/usr/bin/time -v -o logs_directed/build.time iverilog -g2012 -s tb -o sim_directed original.sv candidate_a.sv tb_directed.sv > logs_directed/build.log 2>&1
/usr/bin/time -v -o logs_directed/sim.time vvp sim_directed > logs_directed/sim.log 2>&1
cat logs_directed/sim.log
