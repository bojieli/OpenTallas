#!/bin/bash
# usage: g0c.sh PLAN OUT  (run from the RED worktree)
cd /home/ubuntu/scratch-root/claude/die-qc-63-red/wt; P=$1; O=$2; mkdir -p $O
python3 -I tools/die_plan/check.py $P --out $O --completeness > $O/check.log 2>&1; echo G0C_RC $? >> $O/check.log
