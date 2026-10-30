#!/bin/bash
# V2 = V1 kit copy + Codex kit-local FT-after-landing hook (95b3ec924), place + AUTO-GEOM
B=/srv/opentallas-scratch2/claude/head-kits-t; T=$1; M=$2; R=$B/rekit/$T; V=$R/v2; K=$V/$T
mkdir -p $V; rsync -a --exclude run --exclude lec --exclude "kit_preflight_*" --exclude preflight_history --exclude FAIL_PREFLOOR --exclude FAIL_POSTCTS --exclude "run_*.log" $R/gen/$T/ $K/; cp $R/gen/run_kit.sh $V/; grep -q OT_CLAND_FIT_RESERVE $K/config.mk || echo "export OT_CLAND_FIT_RESERVE = 1" >> $K/config.mk
python3 $B/head_ft_landing_sites_95b3ec924.py $K > $V/hook.log 2>&1 || { echo "$T V2 HOOK_FAIL" >> $B/status.txt; exit 1; }
~/.local/bin/ot-run --mem $M --threads 8 --dir $K -- bash $V/run_kit.sh $K place $M 8 > $V/run_place.otrun.log 2>&1
echo "PLACE_RC $?" >> $V/run_place.otrun.log
O=$(ls $K/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1)
[ -n "$O" ] || { echo "$T V2 NO_3_PLACE" >> $B/status.txt; exit 1; }
OL=$(python3 -c "import json;o=json.load(open(\"$R/source_plan_rekit.json\"))[\"partition_types\"][\"$T\"][\"outline_um\"];print(f\"{o[0]}x{o[1]}\")")
G=$V/geom; mkdir -p $G
printf "{\"id\":\"hkt2-%s\",\"odb\":\"%s\",\"image\":\"openroad/orfs:asap7lock\",\"mem_gb\":16,\"grt\":true,\"rules_args\":[\"--all-kits\",\"--outline\",\"%s\",\"--title\",\"%s HEAD-KITS-T V2 ft-after-landing 3_place\"]}\n" ${T//_/-} $O $OL $T > $G/check.json
bash /srv/opentallas-scratch2/claude/wt/head-kits-t/tools/autopilot/geom_check.sh $G > $G/run.out 2>&1
echo "$T V2 GEOM $(grep "AP_AUTO_GEOM " $G/run.out | tail -1 | cut -c1-300)" >> $B/status.txt
