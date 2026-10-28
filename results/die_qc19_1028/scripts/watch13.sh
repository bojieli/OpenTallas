#!/bin/bash
# DIE-QC-19: when the trial13 kit finishes (tree.json + ctree.v), run chain13.sh (bays, overlay, clock GRT TT/FF, eval, gate). Gives up at 18:30 PDT.
cd /srv/opentallas-scratch2/claude/die-qc19-1028
while pgrep -f "kit.sh t13" >/dev/null; do [ $(date +%H%M) -ge 1830 ] && { echo "gave up $(date)" >> chain13.status; exit 1; }; sleep 20; done
if [ -s trial13/clock/tree.json ] && [ -s trial13/clock/ctree.v ]; then echo "kit done $(date)" >> chain13.status; bash chain13.sh; else echo "kit FAILED $(date)" >> chain13.status; fi
