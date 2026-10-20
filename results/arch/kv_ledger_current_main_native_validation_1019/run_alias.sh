#!/bin/bash
set -u
lane=$PWD
actual=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-cda9d9f9d-gen8v4mub
for shape in baseline candidate; do
 cp "$lane/test_kv_expand_alias_current_main.py" "$lane/$shape/tools/qwen_kv_die/test_kv_expand_alias.py"
 mkdir -p "$lane/evidence_v2/$shape/alias"
 cd "$lane/$shape"
 KV_PARAMETER_ACTUAL_ROOT="$actual" KV_ALIAS_ARTIFACT_DIR="$lane/evidence_v2/$shape/alias/outputs" python3 "$lane/run.py" test_kv_expand_alias.py "$lane/evidence_v2/$shape/alias" > "$lane/evidence_v2/$shape/alias/run.log" 2>&1
 echo $? > "$lane/evidence_v2/$shape/alias/exit_code"
done
