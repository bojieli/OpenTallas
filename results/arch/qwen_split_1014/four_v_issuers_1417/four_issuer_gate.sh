#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/kv-four-v-issuer-1417
sha256sum -c SOURCES.sha256
for m in 0 1 2 3 4;do
 iverilog -g2012 -s tb_qwen_tp8_vrow_four_static -Ptb_qwen_tp8_vrow_four_static.MODE=$m -o mode$m.vvp ot_qwen_tp8_vrow_stack_static.sv tb_qwen_tp8_vrow_four_static.sv > build$m.log 2>&1
 set +e
 vvp mode$m.vvp > mode$m.log 2>&1
 rc=$?
 set -e
 echo "$rc" > mode$m.exit
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q '^PASS FOUR_ISSUER_FULL8192_AND_PARTIAL' mode$m.log;else test "$rc" != 0;grep -q '^EXPECTED_MUTANT_FAULT' mode$m.log;fi
done
echo PASS_FOUR_V_ISSUER_GATE
