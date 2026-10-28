#!/bin/bash
# DIE-KV-6 strict bind of the KV strap-form landed plan: recipe_kv_2350 + clock_landing_table (mk_recipe.py); bind_capture.py
# records the pre-landing bound base per type for the KV strap LEC.  usage: bind.sh TAG (compose/landed_TAG_{plan,sidecar}.json)
set -u
T=$1; W=/srv/opentallas-scratch2/claude/wt/die-kv-6; R=/srv/opentallas-scratch2/claude/die-kv-6-1028; O=$R/b_$T
P=$R/compose/landed_${T}_plan.json; RC=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv_strap_$T.json
mkdir -p $O; cd $W
cp $R/compose/landed_${T}_sidecar.json $W/results/die_kv_6_1028/landed_${T}_sidecar.json
python3 results/die_kv_6_1028/mk_recipe.py $P results/die_kv_6_1028/landed_${T}_sidecar.json $RC || exit 3
if [ ! -s $O/asbuilt.json ]; then echo "$(date) elab"; python3 tools/die_plan/bind.py elab $P --asbuilt $RC --out $O --mem 48 > $O/elab.log 2>&1 || { echo ELAB_RC=$?; tail -5 $O/elab.log; exit 4; }; fi
echo "$(date) bind"; python3 results/die_kv_6_1028/bind_capture.py $O/capture -- bind $P --asbuilt $RC --out $O --mem 48 --strict > $O/bind.log 2>&1; echo BIND_RC=$?
tail -c 1500 $O/bind.log; echo "$(date) DONE"
