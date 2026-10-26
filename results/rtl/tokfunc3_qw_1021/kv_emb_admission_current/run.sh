#!/bin/bash
set -uo pipefail
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
out=/srv/opentallas-scratch/claude/codex-tok-qw-2000/emb_current_out
mkdir -p "$out"
failed=0
for m in 0 1 2 3 4 5; do
 bash tools/qwen_kv_die/kvs_emb_rope_ovl_bench.sh "$out/m$m" "$m" > "$out/m$m.runner.log" 2>&1; rc=$?
 if [ "$m" = 0 ]; then regex='^KVS_EMB_ROPE_OVL PASS'; else regex='^KVS_EMB_ROPE_OVL FAIL'; fi
 if grep -q "$regex" "$out/m$m/m$m.log"; then echo "EMB current m$m expected outcome rc=$rc"; else echo "EMB current m$m UNMET rc=$rc"; failed=1; fi
done
bash tools/qwen_kv_die/kvs_emb_rope_rowtx_eq.sh "$out/rowtx" > "$out/rowtx.runner.log" 2>&1; rc=$?
if [ "$rc" = 0 ] && grep -q '^EQ PASS' "$out/rowtx/eq.log"; then echo 'EMB current rowtx EQ PASS'; else failed=1; echo 'EMB current rowtx UNMET';fi
exit "$failed"
