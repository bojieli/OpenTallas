#!/bin/bash
# MESO-START-2: S81 kit F (DIE-S81-6 data die-s81-5) count-aligned plan + bind + die STA (spice). usage: run_s81.sh TAG SCALE [plan flags]
set -u
R=/srv/opentallas-scratch2/claude/meso-start-2/s81F; D=/srv/opentallas-scratch2/claude/die-s81-5
MT=/srv/opentallas-scratch2/claude/meso-start-2/tools/die_plan; X=$D/lpo_F.json; PLAN=$D/plan_s5.json
TAG=$1; S=$2; shift 2; O=$R/$TAG; mkdir -p $O
python3 $MT/count_align_plan.py $X --scale $S "$@" --out $O/plan.json > $O/plan.log 2>&1; echo "plan rc $?" >> $O/chain.log
python3 $MT/count_align_bind.py $X --from-ocv --scale $S --samples 2000 "$@" --out $O/bind.json > $O/bind.log 2>&1; echo "bind rc $?" >> $O/chain.log
python3 $MT/die_sta_related.py $D/proof_F --plan $PLAN --out $O/sta --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $D/proof_F/droop_regions.json --hold-buffers none --cppr-lca --clock-cal spice --count-align $O/bind.json > $O/sta.log 2>&1; echo "sta rc $?" >> $O/chain.log
grep COUNT-ALIGN $O/sta.log >> $O/chain.log
