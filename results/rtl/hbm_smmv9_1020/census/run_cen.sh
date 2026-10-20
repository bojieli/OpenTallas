#!/usr/bin/env bash
# HBM-SMMV9: SM.MATVEC per-record projections through the RATE8 current-main census (same src/inputs)
R=/srv/opentallas-scratch/claude/hbm-smmv9-1020; cd /srv/opentallas-scratch/claude/hbm-rate8-1020/src || exit 9
cp /tmp/smmv9_mall.json $R/m_all.json 2>/dev/null; cp $R/smmv9_mall.json $R/m_all.json
for n in ${NAMES:-m_all p_floor p_fetch p_fetch_xlr p_fix}; do
  PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out $R/$n.out.json --measured $R/$n.json --bw 98 --bridge 1 > $R/$n.log 2>&1; echo "$n rc=$?" >> $R/rc.txt
  python3 /srv/opentallas-scratch/claude/hbm-rate8-1020/cen/tok_from_sched.py $R/$n.out_jobs > $R/$n.tok.json; echo "$n $(cat $R/$n.tok.json)" >> $R/tok.txt
done
