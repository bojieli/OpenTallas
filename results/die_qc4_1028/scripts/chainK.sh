#!/bin/bash
# DIE-QC-4 full chain on kit NAME (after runKit.sh): clock-first stage 1 (2W2S, TT+FF) -> stage 2 signal GRT (frozen clock)
# -> spice-scaled proof -> die STA lca + HB4 -> CA chain (lpo -> ca_spice -> bind -> STA --count-align).  usage: PLAN=.. MAP=.. chainK.sh NAME
set -u
B=/srv/opentallas-scratch2/claude/die-qc4-1028; N=$1; K=$B/$N
$B/runC.sh $N 2w2s TT & $B/runC.sh $N 2w2s FF & wait
$B/runSig.sh $N 2w2s &
R=$K/P2w; mkdir -p $R/sc/out_TT $R/sc/out_FF; ln -sfn ../../clk $R/sc/clk
for c in TT FF; do F=1.0485; [ $c = FF ] && F=1.0552; python3 -I $B/scale_arr.py $K/c1_2w2s_$c/arr_$c.txt $R/sc/out_$c/arr_$c.txt $c; python3 -I $B/pspread.py $K $K/c1_2w2s_$c/arr_$c.txt $MAP $F > $K/spread2w_$c.txt; done
python3 -I $B/mk_proof.py $R/sc $MAP $R/proof > $R/proof.log 2>&1
$B/runS.sh $R none & $B/runS.sh $R HB4 & $B/runCA.sh $N 2w2s & wait
echo "chainK $N DONE $(date)" >> $B/chain.log
