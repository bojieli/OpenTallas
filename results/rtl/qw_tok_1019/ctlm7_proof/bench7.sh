#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -j 4 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f bench7.f --Mdir ../bench7_obj > ../bench7_build.log 2>&1
for mode in 0 1 2; do
 ../bench7_obj/Vtb_qfd_tt_ctlm_dv_lpf_lp +MUT=$mode +SEED=73521 > ../bench7_mut${mode}.out
 cat ../bench7_mut${mode}.out
 if [ "$mode" = 0 ]; then grep -q 'LP_LOCKSTEP PASS MUT=0' ../bench7_mut${mode}.out; else grep -q "LP_LOCKSTEP FAIL MUT=$mode" ../bench7_mut${mode}.out; fi
done
