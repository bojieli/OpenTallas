#!/bin/bash
# DIE-KV-7 strict bind of the Codex K-only RT20 ECTL event (results/die_kv_7_1028/event_ectl = COPY of codex event_ectl)
set -u
cd /srv/opentallas-scratch2/claude/wt/die-kv-6
P=results/die_kv_7_1028/event_ectl/plan.json; RC=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv7_ectl_r8.json; O=/srv/opentallas-scratch2/claude/die-kv-7-1028/bind_ectl_r8
echo "$(date) elab"; python3 tools/die_plan/bind.py elab $P --asbuilt $RC --out $O --mem 48 > $O/elab.log 2>&1 || { echo ELAB_RC=$?; tail -5 $O/elab.log; exit 4; }
echo "$(date) bind"; python3 tools/die_plan/bind.py bind $P --asbuilt $RC --out $O --mem 48 --strict > $O/bind.log 2>&1; echo BIND_RC=$?
head -c 600 $O/bind.log; echo "$(date) DONE"
