#!/bin/bash
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for kind in golden candidate; do
 yosys -Q -T -p "read_verilog /w/$kind.sv; chparam -set WIDTH 340 ${kind}_skid; hierarchy -top ${kind}_skid; proc; opt; stat; write_json /w/${kind}_proc.json" > /w/${kind}_proc.log 2>&1
done
