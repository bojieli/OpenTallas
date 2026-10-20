#!/usr/bin/env bash
# HBM-SMMV9: compose SM projections with HBM-AGSM8 lever (c) train_go step 129 (its census script, 8bf3152d5)
R=/srv/opentallas-scratch/claude/hbm-smmv9-1020; S=$R/agsrc; rm -rf $S; mkdir -p $S; cp -r /srv/opentallas-scratch/claude/hbm-rate8-1020/src/tools $S/; for x in /srv/opentallas-scratch/claude/hbm-rate8-1020/src/*; do [ -e $S/$(basename $x) ] || ln -s $x $S/; done; cp $R/agsm8_train_census_1020.py $S/tools/hgi_sim/; cd $S
for n in ${NAMES:-m_all p_fix p_floor}; do
  PYTHONPATH=tools python3 -m hgi_sim.agsm8_train_census_1020 --variant train_go --step 129 --out $R/ag_$n.out.json --measured $R/$n.json --bw 98 --bridge 1 > $R/ag_$n.log 2>&1; echo "ag_$n rc=$?" >> $R/rc.txt
  python3 /srv/opentallas-scratch/claude/hbm-rate8-1020/cen/tok_from_sched.py $R/ag_$n.out_jobs > $R/ag_$n.tok.json; echo "ag_$n $(cat $R/ag_$n.tok.json)" >> $R/tok.txt
done
