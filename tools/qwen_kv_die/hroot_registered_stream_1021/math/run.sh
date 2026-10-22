#!/usr/bin/env bash
set -euo pipefail
iverilog -V >iverilog.version 2>&1
iverilog -g2012 -s tb_math -o sim tb_math.sv >build.log 2>&1
vvp sim >sim.log 2>&1
grep -q SPIPE6_ARITH_BOUNDED_PASS sim.log
