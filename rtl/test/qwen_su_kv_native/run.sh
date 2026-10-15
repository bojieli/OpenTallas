#!/bin/bash
set -euo pipefail
for fixture in positive historical lane tag mask reject1 reject2 reject3 reject4; do
 params=()
 case "$fixture" in
 historical) params=(-Ptb_native.HEADS=2);;
 lane) params=(-Ptb_native.MUT_LANE=1);;
 tag) params=(-Ptb_native.MUT_TAG=1);;
 mask) params=(-Ptb_native.MUT_MASK=1);;
 reject1) params=(-Ptb_native.FAULTCASE=1);;
 reject2) params=(-Ptb_native.FAULTCASE=2);;
 reject3) params=(-Ptb_native.FAULTCASE=3);;
 reject4) params=(-Ptb_native.FAULTCASE=4);;
 esac
 iverilog -g2012 -s tb_native "${params[@]}" -o "$fixture.vvp" rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_native_posted.sv rtl/test/qwen_su_kv_native/tb_native.sv 2>"$fixture.compile.log"
 vvp "$fixture.vvp" >"$fixture.log"
 tail -2 "$fixture.log"
 case "$fixture" in
 positive|historical) rg -q '^NATIVE_KV_PASS' "$fixture.log";;
 lane|tag|mask) rg -q '^NATIVE_KV_FAIL data_errors=[1-9]' "$fixture.log";;
 reject*) rg -q '^NATIVE_KV_REJECT_PASS' "$fixture.log";;
 esac
 done
