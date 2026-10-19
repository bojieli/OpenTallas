#!/bin/bash
set -u
S=/srv/opentallas-scratch/claude/refill-0725/MUKVREG2/src_recovery
O=/srv/opentallas-scratch/claude/refill-0725/MUKVREG2/recovery
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$O"
for c in tb_mu_kv_boot kb_sealwrong kb_gapnot kb_u0gap kb_collide; do
 bash "$S/rtl/test/mu_qwen_1018/run_mu_kv_boot.sh" "$S" "$O/$c" "$c" > "$O/s_$c.txt" 2>&1 &
done
bash "$S/rtl/test/mu_qwen_1018/run_mu_kv.sh" "$S" "$O/lint" lint_mu_kv_tiles > "$O/s_lint.txt" 2>&1 &
wait
cat "$O"/s_*.txt
