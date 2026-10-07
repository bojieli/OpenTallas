#!/bin/bash
# Claude 01:50 PT: post-route FF hold ECO (closure-loop helpers as of ce52a512a) on a finished v13b route
E=/srv/opentallas-scratch/claude/dsrom-field-spine/v13b; O=$E/out; J=$E/jobs; t=$1; r=${t#c1r}; r=${r%%_*}
RB=$(ls -d $O/work_$t/orfs/results/asap7/*/base)
cd $E/src && THREADS=16 bash $E/hold_eco.sh $RB $RB $O/eco_$t $t physical/dsrom_field_spine/signoff_r$r.sdc > $J/${t}_eco.out 2>&1
echo $? > $J/${t}_eco.exit
echo "$(date -Is) ECO-END $t exit=$(cat $J/${t}_eco.exit) $(tail -1 $J/${t}_eco.out)" >> $J/MANIFEST
