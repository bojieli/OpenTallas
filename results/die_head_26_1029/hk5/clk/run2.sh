#!/bin/bash
# DIE-HEAD-26: kit -> GRT TT+FF -> duty + spread for one variant.  usage: run.sh TAG CONFIG_ABS
T=$1; C=$2; R=/srv/opentallas-scratch2/claude/die-head-26/clk; cd $R
./kit.sh $T $C > kit_$T.log 2>&1 || exit 1
grep -q "KIT_${T}_RC 0" kit_$T.log || exit 1
./grt.sh $T TT > grt_${T}_TT.log 2>&1 & ./grt.sh $T FF > grt_${T}_FF.log 2>&1; wait
python3 duty.py kit_$T/kit/clock/ctree.v out_${T}_TT/duty_TT.txt out_${T}_FF/duty_FF.txt duty_$T.json > duty_$T.log 2>&1
python3 spread.py $T ${REG:-in/spine_regions.json} > spread_$T.log 2>&1
echo DONE_$T $(date)
