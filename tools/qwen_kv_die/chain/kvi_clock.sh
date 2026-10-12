#!/bin/bash
# kv-die lead die_iter_1012: KV-die clock plan (clock-only CTS per group; region trees sharded, as qwendie-1011 702bea6f6)
S=$1; R=$2; CK=$R/clock; ADMIT=/srv/opentallas-scratch/admit.sh; PY=python3
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
mkdir -p $CK; cd $S
$PY tools/budgets/extract_die.py --src $S --die qwen_kv --variant kv_wq_mirror --out $CK/model.json.gz > $CK/extract.log 2>&1 || { say "CLOCK extract FAIL ($(tail -1 $CK/extract.log))"; exit 1; }
say "clock model: $(tail -1 $CK/extract.log | cut -c1-300)"
for g in htop hreg; do
  SH=; [ $g = hreg ] && SH="--shards 24"
  $PY tools/budgets/clock_plan.py emit --die-model $CK/model.json.gz --group $g --name kvi_$g $SH --out $CK/$g > $CK/emit_$g.log 2>&1 || { say "clock emit $g FAIL ($(tail -1 $CK/emit_$g.log))"; continue; }
  ( cd $CK/$g && $ADMIT 24 -- bash run.sh > run.out 2>&1 ) &
done; wait
$PY tools/budgets/clock_plan.py record --die-model $CK/model.json.gz $(for g in htop hreg; do if [ -f $CK/$g/shards.json ]; then for s in $CK/$g/sh??; do echo --case $s; done; elif [ -d $CK/$g ]; then echo --case $CK/$g; fi; done) --out $CK/plan.json > $CK/record.log 2>&1
say "CLOCK PLAN: $(tail -1 $CK/record.log | cut -c1-400)"
