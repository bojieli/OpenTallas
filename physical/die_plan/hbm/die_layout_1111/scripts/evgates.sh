#!/bin/bash
W=/srv/opentallas-scratch3/claude/die-layout-hbm; E=$W/ev; cd /
TY=NW_io,q_su01,q_su01__physical_v1,q_su30,q_su31,q_su31__physical_v1,root
bash $W/g0.sh $E/plan $E/g0 &
( cd $W/repo && nice -n 19 python3 -I tools/die_plan/station_lint.py $E/plan/die_plan.json --tsv $E/station_lint.tsv > $E/station_lint.log 2>&1 ) &
( cd $W && nice -n 19 python3 -I hcbin/stscan.py ev/plan bindrtl_k5d --out ev/stscan.tsv --detail ev/stscan.json > ev/stscan.log 2>&1; nice -n 19 python3 -I hcbin/stscan.py base_t10 bindrtl_k5d --out b0/stscan_k5d.tsv > b0/stscan_k5d.log 2>&1 ) &
( cd $W/repo && for p in base_t10 ev/plan; do o=$E/rs_$(echo $p | tr / _); mkdir -p $o; nice -n 19 python3 -I tools/die_plan/route_supply.py $W/$p/die_plan.json --die hbm --repo . --types $TY --out $o > $o/stdout 2>&1; done ) &
( nice -n 19 python3 -I /srv/opentallas-scratch3/claude/explorer-script/tools/fleet_viz/explorer_render.py die --plan $E/plan/die_plan.json --out $E/die --top 40 > $E/die.log 2>&1 ) &
( cd $W && nice -n 19 python3 -I hcbin/compose.py classify base_t10 ev/plan ev/classify.json > ev/classify.log 2>&1 ) &
wait; echo DONE > $E/GATES_DONE
