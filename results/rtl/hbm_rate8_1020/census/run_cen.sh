#!/usr/bin/env bash
# HBM-RATE8: census on CURRENT MAIN tools/hgi_sim (overlaid on the smxl-census data bundle), same inputs as HBM-RATE7
R=/srv/opentallas-scratch/claude/hbm-rate8-1020/cen; cd /srv/opentallas-scratch/claude/hbm-rate8-1020/src || exit 9
for n in ${NAMES:-m_base m_xl_i8 m_all}; do
  PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out $R/$n.out.json --measured $R/$n.json --bw 98 --bridge 1 > $R/$n.log 2>&1; echo "$n rc=$?" >> $R/rc.txt
  python3 $R/tok_from_sched.py $R/$n.out_jobs > $R/$n.tok.json; echo "$n $(cat $R/$n.tok.json)" >> $R/tok.txt
done
