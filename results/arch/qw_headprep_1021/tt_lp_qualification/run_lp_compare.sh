#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary -j 4 --timing -I. -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHCONCAT -O1 --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f hp_calr.f -Mdir obj_hp_calr > lp_compare_build.log 2>&1
for mode in 1 2; do
 ./obj_hp_calr/Vtb_qfd_tt_ctlm_dv_lpf_lp +CALRDIR=$mode +CALR_ROM_DIR=calr > "lp_compare_calr$mode.log" 2>&1
 grep -q 'LP_LOCKSTEP PASS' "lp_compare_calr$mode.log"
 [ "$mode" = 1 ] || grep -q 'TLOAD_PRODUCER PASS' "lp_compare_calr$mode.log"
 tail -n 5 "lp_compare_calr$mode.log"
done
echo HP_LP_REALCAL_COMPARE_PASS
