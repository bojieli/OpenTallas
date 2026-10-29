#!/bin/bash
set -euo pipefail
R=$1;O=$2;H=$R/results/token_pass/qwen_rope_producer_0832
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir "$O/obj" \
 "$H/tb.sv" "$R/rtl/qwen_split/qfd_native59_svc_obs1.sv" \
 "$R/rtl/qwen_split/qfd_native59_q_export_control.sv" "$R/rtl/qwen_split/qfd_native59_command_context.sv" \
 "$R/rtl/qwen_split/qfd_native59_static_service_obs1.sv" "$R/rtl/qwen_split/qfd_native59_record_endpoint.sv" \
 "$R/rtl/qwen_split/qfd_native59_mctx_helpers.sv" "$R/rtl/qwen_split/qfd_kvn_static_transport.sv" \
 "$R/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv" > "$O/build.log" 2>&1
for m in 0 1 2;do
 set +e
 "$O/obj/Vtb" +MUT=$m > "$O/m$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep ROPE_PRODUCER_PASS "$O/m$m.log";else test "$rc" != 0;grep ROPE_PRODUCER_FAIL "$O/m$m.log";fi
done
