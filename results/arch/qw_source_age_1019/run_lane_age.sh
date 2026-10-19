#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd qw_source_age_1019
verilator --version > verilator_version.txt
verilator --binary --timing -j 2 -Wno-fatal --top-module lane_age_tb --Mdir obj_age lane_age_tb.sv source/059_qfd_fwd_lane.sv source/005_ot_hdc_cg.sv >build_age.log 2>&1
./obj_age/Vlane_age_tb >lane_age_PASS.log 2>&1
python3 ../tools/qwen_layerbench/test_landing_strap.py >strap_tests.log 2>&1
