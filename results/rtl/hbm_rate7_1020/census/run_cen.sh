#!/usr/bin/env bash
R=/srv/opentallas-scratch/claude/hbm-rate7-1020/cen; cd /srv/opentallas-scratch/claude/hbm-smxl-census-1019/src || exit 9
for n in m_base m_xl_i8 m_all; do
  PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out $R/$n.out.json --measured $R/$n.json --bw 98 --bridge 1 > $R/$n.log 2>&1; echo "$n rc=$?" >> $R/rc.txt
  python3 $R/tok_from_sched.py $R/$n.out_jobs > $R/$n.tok.json; echo "$n $(cat $R/$n.tok.json)" >> $R/tok.txt
done
