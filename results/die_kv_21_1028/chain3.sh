#!/bin/bash
# DIE-KV-21: GRT TT+FF + duty on an existing kit_<T> (DIE-KV-20 chain2 recipe minus the kit step)
T=$1; R=/srv/opentallas-scratch2/claude/die-kv-21-1028; cd $R
mkdir -p clk_$T; cp kit_$T/clock/ctree.tcl clk_$T/ctree_ck89.tcl
./grt.sh $T TT > grt_${T}_TT.log 2>&1 & ./grt.sh $T FF > grt_${T}_FF.log 2>&1 & wait
python3 /srv/opentallas-scratch2/claude/die-kv-15-1028/duty.py kit_$T/clock/ctree.v out_${T}_TT/duty_TT.txt out_${T}_FF/duty_FF.txt duty_$T.json > duty_$T.log 2>&1
echo CHAIN_DONE $(date)
