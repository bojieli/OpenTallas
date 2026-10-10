#!/bin/bash
cd /srv/opentallas-scratch/claude/mtp-draftdie/src_cur
for n in draftA draftB head631 headp2 scan; do
 ( /srv/opentallas-scratch/admit.sh 30 -- python3 tools/s81/s81_dies_recipe.py plan --only $n --out /srv/opentallas-scratch/claude/mtp-draftdie/records/plan > /srv/opentallas-scratch/claude/mtp-draftdie/records/$n.plan.log 2>&1; echo rc=$? >> /srv/opentallas-scratch/claude/mtp-draftdie/records/$n.plan.log ) &
done
( export OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz; /srv/opentallas-scratch/admit.sh 30 -- python3 tools/dsrom_s81_fulldie.py check $(cat results/physical/s81_gen_20261009/s81_layer1_full.opts) > /srv/opentallas-scratch/claude/mtp-draftdie/records/layer1_full.check.log 2>&1; echo rc=$? >> /srv/opentallas-scratch/claude/mtp-draftdie/records/layer1_full.check.log ) &
wait; touch /srv/opentallas-scratch/claude/mtp-draftdie/records/DONE
