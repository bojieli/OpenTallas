#!/bin/bash
set -euo pipefail
gzip -dc cells.v.gz > cells.v
iverilog -g2012 -s tb_result_v_fourstate -o rv_fourstate.vvp tb_result_v_fourstate.sv native_result_v_cone.v cells.v > build_fourstate.log 2>&1
vvp rv_fourstate.vvp | tee result_v_fourstate.log
