#!/bin/bash
set -eu
cd "$(dirname "$0")"
iverilog -g2012 -s tb -o miter native_reset_trees.sv tb.sv
vvp miter > native_miter.log
cat native_miter.log | tail -n 1
