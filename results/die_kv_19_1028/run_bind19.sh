#!/bin/bash
# DIE-KV-19 strict bind of the (b2) lc event (= DIE-KV-16 run_bind16.sh, plan + recipe changed)
# usage: run_bind19.sh OUT RECIPE
set -u
cd /srv/opentallas-scratch2/claude/wt/die-kv-16
P=${P:-results/die_kv_19_1028/event/plan.json}; RC=$2; O=$1
mkdir -p $O
if [ ! -s $O/asbuilt.json ]; then echo "$(date) elab"; python3 tools/die_plan/bind.py elab $P --asbuilt $RC --out $O --mem 48 > $O/elab.log 2>&1 || { echo ELAB_RC=$?; tail -5 $O/elab.log; exit 4; }; fi
echo "$(date) bind"; python3 tools/die_plan/bind.py bind $P --asbuilt $RC --out $O --mem 48 --strict > $O/bind.log 2>&1; echo BIND_RC=$?
head -c 3000 $O/bind.log; echo "$(date) DONE"
