#!/bin/bash
# light localhost relay: copy HBM e2e vectors EPYC1 -> EPYC3 once the exports finish (EPYC3 cannot reach EPYC1)
V=/srv/opentallas-scratch/claude/diesim-1012/hbm/vec
end=$(( $(date +%s) + 12*3600 ))
until timeout 60 ssh -o ControlPath=none ot-epyc1tb "test -f $V/EXPORTS_DONE"; do [ $(date +%s) -gt $end ] && exit 1; sleep 120; done
timeout 3600 ssh -o ControlPath=none ot-epyc1tb "tar -C $V -c ." | timeout 3600 ssh -o ControlPath=none ot-epyc3 "mkdir -p $V && tar -C $V -x && touch $V/READY" && echo "relay ok $(date)" || echo "relay FAIL $(date)"
