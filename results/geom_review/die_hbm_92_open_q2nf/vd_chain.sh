#!/bin/bash
# DIE-HBM-92-OPEN/Q2NF vD chain on intel2 (ot-run, not --crit): synth, then PLACE and native LEC in parallel.
D=/srv/opentallas-scratch2/claude/die-hbm-92-open/q2nf; K=$D/kit_vD; T=$D/tools; L=$D/logs; mkdir -p $L
OR=~/.local/bin/ot-run
$OR --mem 32 --threads 8 --hosts localhost --dir $D -- bash $T/vd_stage.sh $K synth > $L/vd_synth.otrun.log 2>&1 || { echo "SYNTH FAIL $(date)" >> $L/vd_chain.log; exit 1; }
echo "SYNTH done $(date)" >> $L/vd_chain.log
$OR --mem 32 --threads 8 --hosts localhost --dir $D -- bash $T/vd_stage.sh $K place > $L/vd_place.otrun.log 2>&1 &
$OR --mem 40 --threads 8 --hosts localhost --dir $D -- bash $T/vd_stage.sh $K lec > $L/vd_lec.otrun.log 2>&1 &
wait
echo "PLACE+LEC done $(date)" >> $L/vd_chain.log
