#!/usr/bin/env bash
R=/srv/opentallas-scratch/claude/hbm-collfuse2; cd $R/src || exit 9
for v in "base --qwen-tp4-rows" "fuse --qwen-tp4-rows" "tp8" "tp8_fuse"; do set -- $v; n=$1; shift
  PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out $R/cen/$n.json --measured $R/cen/m_$n.json --bw 98 --bridge 1 "$@" > $R/cen/$n.log 2>&1; echo "$n rc=$?" >> $R/cen/rc.txt
done
