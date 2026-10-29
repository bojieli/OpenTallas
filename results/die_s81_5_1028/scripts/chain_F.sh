#!/bin/bash
# DIE-S81-5 parked chain: kit F -> GRT F (clock 2W2S NDR) -> post F.  Light wrapper; heavy steps via ot-run.
cd /srv/opentallas-scratch2/claude/die-s81-5
until grep -qE "KIT_RC|Traceback" kit_F.log; do sleep 30; done
grep -q "KIT_RC 0" kit_F.log || { echo KIT_F_FAILED $(date); exit 1; }
CKNDR=1 ~/.local/bin/ot-run --mem 120 --threads 16 --dir /srv/opentallas-scratch2/claude/die-s81-5 -- env CKNDR=1 bash /srv/opentallas-scratch2/claude/wt/die-s81-5/results/die_s81_5_1028/scripts/go_grt.sh F > grt_F.log 2>&1
~/.local/bin/ot-run --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/die-s81-5 -- bash /srv/opentallas-scratch2/claude/wt/die-s81-5/results/die_s81_5_1028/scripts/post.sh F > post_F.log 2>&1
echo CHAIN_F_DONE $(date)
