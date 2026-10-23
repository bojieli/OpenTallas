#!/bin/bash
# QK3-QGEN 10-21: clone a prepared r10 run dir (same src / scripts / plan inputs) to a new tag, overlay main's
# static_link_bind.py (c1961bab1 SOURCE_BITS-aware validate_case_masters) and optional extra overlay files.
# usage: mkrun.sh OLD_TAG NEW_TAG [overlay_dir]
set -eu
R=/srv/opentallas-scratch/claude/mu-die-qw; O=$R/${1:?old}; N=$R/${2:?new}; OV=${3:-}
[ -e $N ] && { echo "$N exists"; exit 3; }
mkdir -p $N
cp -a $O/src $N/src
for f in gen.sh run.sh run_candidate.sh pre.sh chain.sh follow.sh phase2_fleet.sh phase3.sh project_reset_g5.sh receiver_plan.json land_plan_bi_chain.json reset_release_prior_g4try3.json slice_slot.json source.json; do
  [ -e $O/$f ] && cp -a $O/$f $N/$f; done
sed -i "s#$1#$2#g" $N/gen.sh $N/run.sh $N/run_candidate.sh $N/pre.sh $N/chain.sh $N/follow.sh $N/phase2_fleet.sh $N/phase3.sh $N/source.json
cp $R/qk3-qgen/static_link_bind.main_c1961bab1.py $N/src/tools/qwen_split/static_link_bind.py
[ -n "$OV" ] && cp -a $OV/. $N/src/
ln -sfn $N /srv/opentallas-scratch/claude/qwen-split-compute/$2
echo "$(date '+%F %T %Z') QK3-QGEN setup $2 = clone of $1 src/scripts + main c1961bab1 static_link_bind.py${OV:+ + overlay $OV} (OT_SPLIT_FAULT_SOURCE_BITS=1)" >> $N/PILOT.log
