#!/bin/bash
# usage: run.sh SRCDIR OUTDIR  (SRCDIR holds the peer .sv files). DIE-KV-79 fold audit.
S=$1; O=$2; mkdir -p $O
{
echo "read_verilog -sv -DSYNTHESIS $(ls $S/*.sv | tr '\n' ' ')"
echo 'hierarchy -top qkd_hr_core_peer'
echo 'proc; flatten; memory; opt_expr; simplemap; opt_expr; opt_clean'
echo "write_json $O/pre.json"
echo 'opt -full; opt_dff -sat; opt_merge -share_all; opt -full; opt_dff -sat; opt_clean'
echo "write_json $O/post.json"
} > $O/a.ys
yosys -q -l $O/a.log -s $O/a.ys > /dev/null 2>&1; echo "yosys rc $?"
python3 -I $(dirname $0)/fold_audit.py $O/pre.json $O/post.json --bits > $O/audit.txt; head -1 $O/audit.txt
