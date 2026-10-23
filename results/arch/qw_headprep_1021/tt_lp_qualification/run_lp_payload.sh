#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for mode in 1 2; do
 ./obj_hp_calr/Vtb_qfd_tt_ctlm_dv_lpf_lp +CALRDIR=$mode +CALR_ROM_DIR=calr10 > "lp_payload_calr$mode.log" 2>&1
 grep -q 'LP_LOCKSTEP PASS' "lp_payload_calr$mode.log"
 [ "$mode" = 1 ] || grep -q 'TLOAD_PRODUCER PASS' "lp_payload_calr$mode.log"
 tail -n 5 "lp_payload_calr$mode.log"
done
echo HP_LP_REALCAL_COMPARE_PASS
