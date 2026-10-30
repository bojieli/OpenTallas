#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_vq_temporal --Mdir obj_vq -f source_middle.f src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv tb_vq_temporal.sv >vq_build.log 2>&1
rc=$?;echo VQ_BUILD_RC=$rc >>vq_status.txt
if [ "$rc" -ne 0 ];then tail -18 vq_build.log;exit "$rc";fi
obj_vq/Vtb_vq_temporal >vq_base.log 2>&1
rc=$?;echo VQ_BASE_RC=$rc >>vq_status.txt
obj_vq/Vtb_vq_temporal +bad_payload >vq_payload.log 2>&1
prc=$?;echo VQ_PAYLOAD_RC=$prc >>vq_status.txt
obj_vq/Vtb_vq_temporal +bad_age >vq_age.log 2>&1
arc=$?;echo VQ_AGE_RC=$arc >>vq_status.txt
cat vq_status.txt
if [ "$rc" -eq 0 ] && [ "$prc" -ne 0 ] && [ "$arc" -ne 0 ];then echo VQ_GATE_PASS >>vq_status.txt;else exit 1;fi
