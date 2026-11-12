#!/bin/bash
# usage: variants.sh TAG "TYPES" "extra args" ...  (runs make_refloor then route_supply)
R=/srv/opentallas-scratch2/claude/sc-refloor-1; SRC=/srv/opentallas-scratch2/claude/kw45/src_qc_s25_4e2764d237
TAG=$1; TY=$2; shift 2
cd /
nice python3 -I -B $R/bin/make_refloor.py $SRC $R/planq/plan_qc99_s25.json $R/planq/plan_rf_$TAG.json $R/planq/delta_rf_$TAG.json --types $TY "$@" > $R/planq/$TAG.log 2>&1 || { echo "GEN FAIL $TAG"; tail -3 $R/planq/$TAG.log; exit 1; }
RE="^($(echo $TY | tr , '|'))\$"
$R/rs.sh plan_rf_$TAG "$RE" > /dev/null
echo "== $TAG $(grep -o 'problems.*' $R/planq/$TAG.log | grep -v 'problems \[\]' | head -3)"
cut -f2,5,6,8,9,10,17,18,19,20,21 $R/rs/plan_rf_$TAG/route_supply_qwen_compute.tsv | tail -n +2
