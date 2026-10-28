#!/bin/bash
# DIE-S81-9 WHAT-IF (diagnostic): packed-G proof, plan_s5 with plan pins resolved (HB4 bound count), kit tap window W per --intra-window-ps
set -u
MT=/srv/opentallas-scratch2/claude/wt/die-s81-9/tools/die_plan; PR=/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body/proof_body
PL=/srv/opentallas-scratch2/claude/die-s81-9/wi/plan/plan_s5.json; B=/srv/opentallas-scratch2/claude/die-s81-8/gate_sspice/bind.json
for W in 0 165; do
python3 $MT/die_sta_related.py $PR --plan $PL --out /srv/opentallas-scratch2/claude/die-s81-9/wi/sta_W$W --corner TT --corner FF --clock-ocv table --clock-droop shared   --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers HB4 --cppr-lca --clock-cal spice   --count-align $B --count-align-key region --intra-window-ps $W > /srv/opentallas-scratch2/claude/die-s81-9/wi/sta_W$W.log 2>&1 &
done; wait; echo DONE $(date)
