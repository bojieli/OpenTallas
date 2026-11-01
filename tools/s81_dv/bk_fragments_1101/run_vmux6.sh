#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_vmux6_fragments --build-jobs 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --Mdir obj candidate_vmux6.sv vmux6_legacy.sv tb_vmux6_fragments.sv >build.log 2>&1
set +e
obj/Vtb_vmux6_fragments >base.log 2>&1;b=$?
obj/Vtb_vmux6_fragments +mut_payload >mut_payload.log 2>&1;m=$?
printf 'BASE_RC=%d\nMUT_PAYLOAD_RC=%d\n' "$b" "$m" >status.txt
cat status.txt
grep VMUX6_FRAGMENTS base.log
if [ "$b" -ne 0 ]||[ "$m" -eq 0 ];then exit 1;fi
