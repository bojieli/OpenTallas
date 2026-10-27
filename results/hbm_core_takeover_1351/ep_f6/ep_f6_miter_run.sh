#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-ep-f6-1453
for mut in 0 1 2; do
 set +e
 /home/ubuntu/.local/opentallas-tools/bin/yosys -Q -p "read_verilog -sv ep_f6_copy_miter.sv; chparam -set MUT $mut ep_f6_copy_miter; prep -top ep_f6_copy_miter; async2sync; opt; sat -seq 4 -tempinduct -set-def-inputs -prove ok 1 -verify" > "copy_mut${mut}.log" 2>&1
 rc=$?
 set -e
 echo "COPY_MUT=$mut RC=$rc"
 if [ "$mut" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
