#!/bin/bash
set -u
lane=$PWD
actual=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-cda9d9f9d-gen8v4mub
for shape in baseline candidate; do
 cp "$lane/test_kv_expand_unsigned_flow.py" "$lane/$shape/tools/qwen_kv_die/"
 mkdir -p "$lane/evidence_unsigned_flow/$shape"
 cd "$lane/$shape"
 KV_PARAMETER_ACTUAL_ROOT="$actual" python3 "$lane/run.py" test_kv_expand_unsigned_flow.py "$lane/evidence_unsigned_flow/$shape" > "$lane/evidence_unsigned_flow/$shape/run.log" 2>&1
 echo $? > "$lane/evidence_unsigned_flow/$shape/exit_code"
done
