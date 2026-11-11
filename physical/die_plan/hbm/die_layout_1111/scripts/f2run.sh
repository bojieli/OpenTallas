#!/bin/bash
# DIE-LAYOUT-HBM F2: ft_s0_resite on the DIE-VIS R/J over-reach slots of non-bank/non-hub types, 6 groups in parallel
W=/srv/opentallas-scratch3/claude/die-layout-hbm; cd $W/repo
T=/srv/opentallas-scratch2/claude/die-vis-hbm/slot_plan_post_cut.tsv
awk -F'\t' 'NR>1 && ($13 ~ /^RESPACE/ || $13 ~ /^JOG /|| $13=="JOG") && $3 !~ /^q_b0|^q_hub|^q_b10/ {print $3"/"$4}' $T | sort -u > $W/f2/slots.txt
split -n l/6 -d $W/f2/slots.txt $W/f2/grp.
for g in $W/f2/grp.0*; do n=$(basename $g)
  S=$(paste -sd, $g)
  nohup nice -n 19 python3 -I tools/die_plan/ft_s0_resite.py $W/base_t10/die_plan.json $W/f2/$n.plan.json $W/f2/$n.ledger.json --slots "$S" --jog-sweep 6 > $W/f2/$n.log 2>&1 < /dev/null &
done
wait; echo ALLDONE > $W/f2/ALLDONE
