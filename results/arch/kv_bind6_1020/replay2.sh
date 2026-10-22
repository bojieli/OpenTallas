#!/bin/bash
# KV-BIND6 10-20: re-run ONLY the strict bind v2 on the replay case with the e744dbe0f misc-roles tool (overlay tree:
# symlinks into the d7p worktree, the one changed file copied). Diagnostic only.
set -euo pipefail
B=/srv/opentallas-scratch/claude/kv-bind6-1020
S=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-abbb4391c-gen9d7p
O=$B/ovl; R=$B/replay/run
rm -rf $O; mkdir -p $O/tools/qwen_kv_die
for e in $S/* $S/.git; do n=$(basename $e); [ $n = tools ] || ln -s $e $O/$n; done
for e in $S/tools/*; do n=$(basename $e); [ $n = qwen_kv_die ] || ln -s $e $O/tools/$n; done
for e in $S/tools/qwen_kv_die/*; do n=$(basename $e); [ $n = kv_misc_unused_roles.py ] || ln -s $e $O/tools/qwen_kv_die/$n; done
cp $B/kv_misc_unused_roles.py $O/tools/qwen_kv_die/
set -a; . $R/kv_flags.env; set +a
export PYTHONDONTWRITEBYTECODE=1 OT_KV_PARAM_DIAG=1 OT_BIND_DIAGNOSTIC=1
cd $O
rm -rf $R/port_bind_v2b
bash tools/qwen_kv_die/kv_port_bind_v2.sh $R/case_kv/die.v $R/port_bind_v2b $R/case_kv/qkd_kv_relays.sv $R/expand.json > $R/port_bind_v2b.log 2>&1 || true
tail -n 5 $R/port_bind_v2b.log
