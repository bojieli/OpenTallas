#!/bin/bash
# ROOT4-STAPG: collect PG-bind ECO receipts (kv + hbm) into the receipts worktree; rerunnable
T=/home/ubuntu/scratch/root4-stapg; WT=/home/ubuntu/wt/root4-stapg
for set in "kv kv_list.txt results/rtl/kv_pg_bind_eco_1019" "hbm hbm_eco_run.txt results/rtl/hbm_pg_bind_eco_1019"; do
  read tag list dir <<<"$set"; R=$WT/$dir; mkdir -p $R; cp $T/$list $R/eco_list.txt
  echo "| view | ran on | bound terminals | post audit | grid VDD/VSS | signal |" > $R/table.md; echo "|---|---|---:|---|---|---|" >> $R/table.md
  while read name host root base orig; do
    log=$T/eco_${tag}_$name.log; grep -q '^RC=' $log 2>/dev/null || { echo "| $name | $host | RUNNING | | | |" >> $R/table.md; continue; }
    mkdir -p $R/$name; o=$root/pg_bind_eco_native
    scp -q -o ControlPath=none $host:$o/run.log $host:$o/post_audit.json $R/$name/ </dev/null
    cp $log $R/$name/ot_run.log; echo "$name $host $root $base ${orig:+(copied from $orig, sha256 equal)} -> $o/6_final_pgbound.odb" > $R/$name/source.txt
    b=$(grep -o 'bound_terminals=[0-9]*' $R/$name/run.log | cut -d= -f2); p=$(grep -o 'OT_PG_ECO_POST_PASS checked=[0-9]*' $R/$name/run.log | cut -d= -f2)
    g=$(grep -c 'OT_PG_GRID_V.. PASS' $R/$name/run.log); s=$(grep -q SIGNAL_IDENTICAL $R/$name/run.log && echo identical || echo DIFF)
    echo "| $name | $host | $b | $([ -n "$p" ] && echo "PASS ($p)" || echo FAIL) | $g/2 PASS | $s |" >> $R/table.md
  done < $T/$list
done
