#!/bin/bash
# wait for census PLACE (ot-run log terminal line) then launch the chain via ot-run on epyc2
V=$1; B=/srv/opentallas-scratch2/claude/die-s81-26/bf
for i in $(seq 1 360); do grep -q "ot-run: RAN\|NOT RUN\|NOT COMPLETED" $B/cen_$V.otrun.log 2>/dev/null && break; sleep 30; done
echo "census done $(date -Is): $(tail -1 $B/cen_$V.otrun.log)" > $B/launch_$V.log
~/.local/bin/ot-run --mem 24 --threads 8 --hosts epyc2 --dir $B -- bash $B/chain.sh $V >> $B/chain_$V.otrun.log 2>&1
