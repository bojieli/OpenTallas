#!/bin/bash
# HBM-NEXT-UNITS-IDX 10-19: pitch sweep on the kept hnx INDEX binary (bundle 71e301580): N=2 at pitch P -> PASS/FAIL
O=/srv/opentallas-scratch/claude/hnx-idx-71e301580/out_index; K=/srv/opentallas-scratch/claude/hnx-idx-71e301580/keep
S=$K/sweep; mkdir -p $S; FL=1397
one(){ local n=$1 p=$2 od=$S/n${1}_p$2; rm -rf $od; mkdir -p $od; cp $O/vec/*.hex $O/cal/frame/calendar_instructions.hex $od/
 ( cd $od && $K/obj_hnx/Vhnx +N=$FL +ROWS=$n +PITCH=$p > run.log 2>&1; echo RUN_RC=$? >> run.log )
 local v=FAIL; grep -q 'IDX_HNX_ROWS PASS' $od/run.log && v=PASS
 echo "N$n pitch$p $v: $(grep -h 'IDX_ROWS_CYCLES\|IDX_HNX_ROWS rows' $od/run.log | tr '\n' ' ' | cut -c1-260)" >> $S/sweep.txt; }
for p in 952 951 950 940 920 900 850 800 750 700; do one 2 $p & done; wait
sort -t h -k2 $S/sweep.txt > $S/sweep_sorted.txt; echo done >> $S/sweep.txt
