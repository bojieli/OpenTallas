#!/bin/bash
# usage: place_geom.sh TYPE MEM  -- ot-run place goal on rekit/TYPE/gen/TYPE, then AUTO-GEOM on 3_place.odb
B=/srv/opentallas-scratch2/claude/head-kits-t; T=$1; M=$2; R=$B/rekit/$T; K=$R/gen/$T
~/.local/bin/ot-run --mem $M --threads 8 --dir $K -- bash $R/gen/run_kit.sh $K place $M 8 > $R/run_place.otrun.log 2>&1
echo "PLACE_RC $?" >> $R/run_place.otrun.log
O=$(ls $K/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1)
[ -n "$O" ] || { echo "$T NO_3_PLACE" >> $B/status.txt; exit 1; }
OL=$(python3 -c "import json;t=json.load(open(\"$R/source_plan_rekit.json\"))[\"partition_types\"][\"$T\"];o=t[\"outline_um\"];print(f\"{o[0]}x{o[1]}\" if len(o)==2 else f\"{o[2]-o[0]}x{o[3]-o[1]}\")")
G=$R/geom_v1; mkdir -p $G
printf "{\"id\":\"hkt-%s\",\"odb\":\"%s\",\"image\":\"openroad/orfs:asap7lock\",\"mem_gb\":%s,\"grt\":true,\"rules_args\":[\"--all-kits\",\"--outline\",\"%s\",\"--title\",\"%s HEAD-KITS-T src25m_kt 3_place\"]}\n" ${T//_/-} $O 16 $OL $T > $G/check.json
bash /srv/opentallas-scratch2/claude/wt/head-kits-t/tools/autopilot/geom_check.sh $G > $G/run.out 2>&1
echo "$T GEOM $(grep AP_AUTO_GEOM $G/run.out | tail -1 | cut -c1-200)" >> $B/status.txt
