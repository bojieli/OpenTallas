#!/bin/bash
set -euo pipefail
Y=/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys
for m in 0 1 2;do
 if "$Y" -p "read_verilog reset_depth_m$m.sv; prep -top reset_depth; flatten; sat -seq 4 -set-init-zero -prove eq 1 -verify -show rst_n -show eq" > reset_depth_m$m.log 2>&1;then
  test "$m" = 0 || { echo "MUTANT_SURVIVED $m";exit 1; }
 else
  test "$m" != 0 || { tail -20 reset_depth_m$m.log;exit 1; }
  grep -q 'proof did fail' reset_depth_m$m.log
 fi
 echo "resetdepth m$m expected passed"
done
