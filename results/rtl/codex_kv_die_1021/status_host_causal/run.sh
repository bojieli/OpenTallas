#!/bin/bash
set -euo pipefail
v=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for variant in good count_level; do
 mut=0;if [ "$variant" = count_level ];then mut=3;fi
 "$v" --binary --timing -Wno-fatal --top-module tb_status_host -GMUT="$mut" --Mdir "obj_$variant" -j 1 qkd_host_status_obs.sv ot_qwen_status_observers_v1.sv tb_status_host.sv > "$variant.build.log" 2>&1
 set +e
 "obj_$variant/Vtb_status_host" > "$variant.log" 2>&1
 rc=$?
 set -e
 if [ "$variant" = good ];then test "$rc" = 0;grep -q STATUS_HOST_PASS "$variant.log";
 else test "$rc" != 0;grep -Eq 'FIRST_RECORD_OR_DELTA_LOST|COMPLETION_DELTA_NOT_COUNT' "$variant.log";fi
 echo "$variant expected verdict PASS"
done
