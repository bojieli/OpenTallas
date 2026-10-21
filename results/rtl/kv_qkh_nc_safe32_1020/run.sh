#!/bin/bash
set -eu
bash tools/qwen_kv_die/qkh_nc_bench.sh add 1 "$PWD/mut1live" +n=300000 +warm=0 >mut1live.log 2>&1 && { echo ERROR_MUTANT_PASS;exit 1; } || grep 'TB_QKH_NC FAIL' mut1live.log
for top in ot_qkh_ktree_nc ot_qkh_lane8_nc; do
 docker run --rm -v "$PWD:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/work/results/rtl/kv_qkh_nc_safe32_1020/$top.mk WORK_HOME=/work/native_$top synth >synth_$top.log 2>&1
done
