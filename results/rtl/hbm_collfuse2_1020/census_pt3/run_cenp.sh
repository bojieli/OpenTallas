#!/usr/bin/env bash
R=/srv/opentallas-scratch/claude/hbm-collfuse2; cd $R/src || exit 9
for v in "p0 --qwen-tp4-rows" "p1 --qwen-tp4-rows" "p2" "p3"; do set -- $v; n=$1; shift
  PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out $R/cenp/$n.json --measured $R/cenp/m_$n.json --bw 98 --bridge 1 "$@" > $R/cenp/$n.log 2>&1; echo "$n rc=$?" >> $R/cenp/rc.txt
  python3 $R/cenp/tok_from_sched.py $R/cenp/${n}_jobs > $R/cenp/$n.tok.json
done
