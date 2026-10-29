#!/bin/bash
# DIE-KV-15 strict bind of the fishbone proofF event (= DIE-KV-13 run_bind13.sh, paths changed)
# usage: run_bind13.sh OUT [RECIPE]
set -u
cd /srv/opentallas-scratch2/claude/wt/die-kv-15
P=${P:-results/die_kv_15_1028/event/plan.json}; RC=${2:-physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv15_b1.json}; O=$1
mkdir -p $O
if [ ! -s $O/asbuilt.json ]; then echo "$(date) elab"; python3 tools/die_plan/bind.py elab $P --asbuilt $RC --out $O --mem 48 > $O/elab.log 2>&1 || { echo ELAB_RC=$?; tail -5 $O/elab.log; exit 4; }; fi
echo "$(date) bind"; python3 tools/die_plan/bind.py bind $P --asbuilt $RC --out $O --mem 48 --strict > $O/bind.log 2>&1; echo BIND_RC=$?
head -c 3000 $O/bind.log; echo "$(date) DONE"
