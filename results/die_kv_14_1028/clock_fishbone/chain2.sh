#!/bin/bash
T=$1; V=$2; REP=$3; R=/srv/opentallas-scratch2/claude/die-kv-14-1028; cd $R
./kit2.sh $T $V $REP > kit_$T.log 2>&1 || { echo KIT_FAIL; exit 1; }
mkdir -p clk_$T; cp kit_$T/clock/ctree.tcl clk_$T/ctree_ck89.tcl
./grt.sh $T TT > grt_${T}_TT.log 2>&1 & ./grt.sh $T FF > grt_${T}_FF.log 2>&1 & wait
python3 duty.py kit_$T/clock/ctree.v out_${T}_TT/duty_TT.txt out_${T}_FF/duty_FF.txt duty_$T.json > duty_$T.log 2>&1
echo CHAIN_DONE $(date)
