#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/qc-sliceclk-1027/price
n=$1; O=$R/cost_$n
python3 $R/reprice_actual.py --root $R --requirements $R/req_$n.json --out $O > $R/prep_$n.log 2>&1
read -r CB HP L9 < <(python3 -c "import json;j=json.load(open(\"$O/actual_landing_paths.json\"));print(int(j[\"cb_add\"]),int(j[\"hop_add\"]),int(j[\"l9_add\"]))")
VF=$(cat $R/ages/vflags.txt); H=$R/inputs/price_fereach_clkland_1026
t=${n}_land; A=$O/add_actual_land.json
python3 $H/rederive_edges_ext.py $R/inputs/bus_groups_v7.json.gz $t --add $A --hop-ext --l9-stb --cb-add $CB --hop-add $HP --l9-add $L9 --out $O > $O/rederive_land.log 2>&1
python3 $R/compose/compose_edges.py $R/compose q_$t $R/ages/slice_ages.json $R/ages/vec_ages.json $R/ages/stn_ages.json "$VF" --replace $O/edges_${t}_rederived.json $O/lane_ages_${t}_rederived.json >> $O/compose.log 2>&1
cat $R/prep_$n.log $O/compose.log
