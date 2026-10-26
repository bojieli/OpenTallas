#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/fallback-land-1026/qc; C=/srv/opentallas-scratch2/claude/codex-qc-land-price-1026
n=$1; O=$R/cost_$n
python3 $R/reprice_actual.py --root $R --requirements $R/req_$n.json --out $O > $R/prep_$n.log 2>&1
read -r CB HP L9 < <(python3 -c "import json;j=json.load(open(\"$O/actual_landing_paths.json\"));print(int(j[\"cb_add\"]),int(j[\"hop_add\"]),int(j[\"l9_add\"]))")
VF=$(cat $R/ages/vflags.txt); H=$R/inputs/price_fereach_clkland_1026
for k in land fe_land; do
 if [ "$k" = land ]; then A=$O/add_actual_land.json; else A=$O/add_actual_fe_land.json; fi
 t=${n}_${k}
 python3 $H/rederive_edges_ext.py $R/inputs/bus_groups_v7.json.gz $t --add $A --hop-ext --l9-stb --cb-add $CB --hop-add $HP --l9-add $L9 --out $O > $O/rederive_$k.log 2>&1
 python3 $R/compose/compose_edges.py $R/compose q_$t $R/ages/slice_ages.json $R/ages/vec_ages.json $R/ages/stn_ages.json "$VF" --replace $O/edges_${t}_rederived.json $O/lane_ages_${t}_rederived.json >> $O/compose.log 2>&1
done
cat $R/prep_$n.log $O/compose.log
