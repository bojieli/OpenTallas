#!/bin/bash
set -u
lane=$PWD
actual=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-cda9d9f9d-gen8v4mub
mkdir baseline candidate
for shape in baseline candidate; do
 tar -xf main.tar -C "$shape"
 cp test_kv_expand_alias.py test_kv_expand_parameters.py "$shape/tools/qwen_kv_die/"
 # Current-main RTL is authoritative for imports; frozen view tree is input-only.
 ln -s "$actual/physical" "$shape/physical"
 ln -s "$actual/results" "$shape/results"
done
(cd candidate && patch -p1 < ../candidate.patch)
for shape in baseline candidate; do
 cd "$lane/$shape"
 for kind in alias parameters; do
  mkdir -p "$lane/evidence/$shape/$kind"
  KV_PARAMETER_ACTUAL_ROOT="$actual" KV_ALIAS_ARTIFACT_DIR="$lane/evidence/$shape/alias/outputs" python3 "$lane/run.py" "test_kv_expand_$kind.py" "$lane/evidence/$shape/$kind" > "$lane/evidence/$shape/$kind/run.log" 2>&1
  echo $? > "$lane/evidence/$shape/$kind/exit_code"
 done
 mkdir -p "$lane/evidence/$shape/unsigned_parameters"
 # unsigned suite has a different filename.
 KV_PARAMETER_ACTUAL_ROOT="$actual" python3 "$lane/run.py" test_kv_unsigned_parameters.py "$lane/evidence/$shape/unsigned_parameters" > "$lane/evidence/$shape/unsigned_parameters/run.log" 2>&1
 echo $? > "$lane/evidence/$shape/unsigned_parameters/exit_code"
done
