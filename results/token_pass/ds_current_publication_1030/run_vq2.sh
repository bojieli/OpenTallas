#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_vq_temporal --Mdir obj_vq2 -f source_middle.f src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv tb_vq_temporal.sv >vq2_build.log 2>&1
rc=$?;echo VQ_BUILD_RC=$rc >>vq2_status.txt
if [ "$rc" -ne 0 ];then tail -18 vq2_build.log;exit "$rc";fi
obj_vq2/Vtb_vq_temporal >vq2_base.log 2>&1
rc=$?;echo VQ_BASE_RC=$rc >>vq2_status.txt
obj_vq2/Vtb_vq_temporal +bad_payload >vq2_payload.log 2>&1
prc=$?;echo VQ_PAYLOAD_RC=$prc >>vq2_status.txt
obj_vq2/Vtb_vq_temporal +bad_age >vq2_age.log 2>&1
arc=$?;echo VQ_AGE_RC=$arc >>vq2_status.txt
cat vq2_status.txt
if [ "$rc" -eq 0 ] && [ "$prc" -ne 0 ] && [ "$arc" -ne 0 ];then echo VQ_GATE_PASS >>vq2_status.txt;else exit 1;fi
