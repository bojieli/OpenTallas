#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch/claude/q-vmwb/zfix; R=$D/src
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sed -e "s#/srv/opentallas-scratch/claude/q-attn-1015/b4/obj/Vqkd_astk_ctl_tp8_cal_d#$D/ctl#" /srv/opentallas-scratch/claude/q-attn-1015/b4/obj/Vqkd_astk_ctl_tp8_cal_d__hierMkArgs.f \
 | tr ' ' '\n' | sed -E "s#^(rtl|physical)/#$R/\1/#" | grep -v 'rtl/test/\|ot_qwen_tp8_attention_native_service.sv$' | tr '\n' ' ' > $D/ctl.f
rm -rf $D/ctl; cd $R
"$vl" -f $D/ctl.f --build > $D/ctl_build.log 2>&1
