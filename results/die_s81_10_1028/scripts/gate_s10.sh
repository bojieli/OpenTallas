#!/bin/bash
# DIE-S81-10 gate on packed-G proof (Codex clock_G_body, fresh GRT0) with plan_s10 (CORELAT taps + tap_window 180 + seam_hold):
# CA-OCV-1 planner (--sta-clock-ocv table, shared droop) + start-skew-clean + STA hull, die_sta_related spice/cppr-lca/key region.
# Arrivals = packed-G tree (built on plan_s5 taps): WHAT-IF for the core-tap part, gate form for CA/window.
set -u
MAP=/srv/opentallas-scratch2/claude/die-s81-5/feed/map_part.json; WT=/srv/opentallas-scratch2/claude/wt/die-s81-10; MT=$WT/tools/die_plan
CB=/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body; PR=$CB/proof_body
PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json; O=/srv/opentallas-scratch2/claude/die-s81-10/gate; mkdir -p $O
X=/srv/opentallas-scratch2/claude/die-s81-8/gate_sspice/sp_xing_lpo.json   # DIE-S81-8 spice per-corner crossing export (same proof)
F="--start-skew 46.9,79.4 --start-skew-clean --sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
echo START $(date) $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $PL | cut -c1-12)
python3 $MT/count_align_plan.py $X $F --out $O/plan.json > $O/plan.log 2>&1; echo "plan rc $?"
python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --out $O/bind.json > $O/bind.log 2>&1; echo "bind rc $?"
for V in table none; do
python3 $MT/die_sta_related.py $PR --plan $PL --out $O/sta_$V --corner TT --corner FF --clock-ocv $V --clock-droop shared \
  --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice \
  --count-align $O/bind.json --count-align-key region > $O/sta_$V.log 2>&1; echo "sta $V rc $?"; grep -E "COUNT-ALIGN|intra " $O/sta_$V.log
done
B=/srv/opentallas-scratch2/claude/die-s81-8/gate_sspice/bind.json
python3 $MT/die_sta_related.py $PR --plan $PL --out $O/sta_oldbind --corner TT --corner FF --clock-ocv table --clock-droop shared \
  --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice \
  --count-align $B --count-align-key region > $O/sta_oldbind.log 2>&1; echo "sta oldbind rc $?"; grep -E "COUNT-ALIGN" $O/sta_oldbind.log
echo DONE $(date)
