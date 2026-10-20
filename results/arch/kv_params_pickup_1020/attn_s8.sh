#!/bin/bash
set -o pipefail
python3 /srv/opentallas-scratch/claude/kv-attn3-1020/tool/tools/qwen_kv_die/kv_param_native_audit.py audit --root /srv/opentallas-scratch/claude/kv-bind4-1019/attn/root --module qkd_kvs_attn_fl --rtl rtl/lib/face_land/qkd_kvs_attn_fl_r16.sv --view physical/ref_tile/qkd_kvs_attn_rv3/views/qkd_kvs_attn_fl --params '{"MUT":0,"RETIRE_STATIC":1,"STATUS_DELAY":213}' --archive-run /srv/opentallas-scratch/claude/kv-bind4-1019/attn/arch/qkd_kvs_attn_rv3-rv3-6fdacf98c --reset-landing /srv/opentallas-scratch/claude/kv-bind4-1019/attn/root/physical/ref_tile/qkd_kvs_attn_rv3/reset_landing.json --expect pass --reset-base 6 --induct-seq 8 --dup-witness --witness-joint --timeout 30000 --work /srv/opentallas-scratch2/claude/codex-kv-params-audit-1020/attn_j0_s8 --out /srv/opentallas-scratch2/claude/codex-kv-params-audit-1020/out/attn_j0_s8.audit.json > /srv/opentallas-scratch2/claude/codex-kv-params-audit-1020/out/attn_j0_s8.log 2>&1
rc=$?
printf "%s\n" "$rc" > /srv/opentallas-scratch2/claude/codex-kv-params-audit-1020/out/attn_j0_s8.rc
exit "$rc"
