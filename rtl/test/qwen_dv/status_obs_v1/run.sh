#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
for M in 0 1; do
 verilator --binary --timing -j 8 -Wno-fatal --top-module tb_status_obs_v1 -GMUT=$M --Mdir obj$M rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe7.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_status_observers_v1.sv rtl/test/qwen_dv/status_obs_v1/tb_status_obs_v1.sv > build$M.log 2>&1 || { tail -n 30 build$M.log;exit 3; }
 obj$M/Vtb_status_obs_v1 > run$M.log 2>&1
 cat run$M.log
 if [ "$M" = 0 ]; then grep -q 'STATUS_OBS_V1 PASS MUT=0' run$M.log;else grep -q 'STATUS_OBS_V1 FAIL MUT=1' run$M.log;fi
done
printf 'STATUS_OBS_V1_SUITE PASS positive mutant_caught\n'
