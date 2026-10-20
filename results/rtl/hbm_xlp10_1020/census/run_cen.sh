#!/usr/bin/env bash
# HBM-XLP10: census on the RATE8 current-main tools (same src / flags as HBM-RATE8 / HBM-SMMV9); NAMES = m_<variant>
C=/srv/opentallas-scratch/claude/hbm-xlp10-1020/cen; S=/srv/opentallas-scratch/claude/hbm-rate8-1020; cd $S/src || exit 9
for n in ${NAMES:-m_xl m_xr m_xp4}; do
  PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out $C/$n.out.json --measured $C/$n.json --bw 98 --bridge 1 > $C/$n.log 2>&1; echo "$n rc=$?" >> $C/rc.txt
  python3 $S/cen/tok_from_sched.py $C/$n.out_jobs > $C/$n.tok.json; echo "$n $(cat $C/$n.tok.json)" >> $C/tok.txt
done
