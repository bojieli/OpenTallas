#!/bin/bash
# render.sh KIT... : dump 3_place (docker 4 GB) + render + census into /srv/opentallas-scratch2/claude/s81-head-kits/render
P=/srv/opentallas-scratch2/claude/proto1025; R=/srv/opentallas-scratch2/claude/s81-head-kits; O=$R/render; mkdir -p $O
for k in "$@"; do
  m=$(basename $(dirname $k)); t=$(basename $k); o=$(ls $k/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1); [ -n "$o" ] || { echo "$t $m no 3_place"; continue; }
  docker run --rm --memory=4g -v $k:$k -v $O:$O -v $P:$P -e ODB=$o -e OUT=$O/${t}_$m.place.tsv openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit $P/dump_place.tcl" > $O/${t}_$m.dump.log 2>&1
  python3 $P/render_place.py $O/${t}_$m.place.tsv $O/${t}_$m.place.png "$t $m s81_head 3_place" > $O/${t}_$m.hops.txt 2>&1
  python3 $R/hk_ana.py $O/${t}_$m.place.tsv > $O/${t}_$m.census.json 2>&1
  echo "== $t $m"; cat $O/${t}_$m.hops.txt; cat $O/${t}_$m.census.json
done
