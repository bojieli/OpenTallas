#!/bin/bash
# QC-TYPES-10/CLAND: private bind farm = src_d95ec (the bind_v4w producer) + the CLAND tool patch; plan v4w unchanged
set -eu
S=$(readlink -f /srv/opentallas-scratch2/claude/kw33/src_d95ec)
W=/srv/opentallas-scratch2/claude/qct10/cland; F=$W/farm
rm -rf $F; mkdir -p $F
for e in $S/* $S/.[!.]*; do b=$(basename $e); case $b in tools|physical) ;; *) ln -s $e $F/$b;; esac; done
cp -a $S/tools $F/tools; chmod -R u+w $F/tools
mkd(){ mkdir -p $2; for e in $1/* $1/.[!.]*; do [ -e "$e" ] || continue; b=$(basename $e); [ "$b" = "$3" ] || ln -s $e $2/$b; done; }
mkd $S/physical $F/physical die_plan
mkd $S/physical/die_plan $F/physical/die_plan qwen_compute
mkd $S/physical/die_plan/qwen_compute $F/physical/die_plan/qwen_compute plan_of_record
mkd $S/physical/die_plan/qwen_compute/plan_of_record $F/physical/die_plan/qwen_compute/plan_of_record __none__
cp /srv/opentallas-scratch2/claude/qct9/plan_qc53v4w.json $F/physical/die_plan/qwen_compute/plan_of_record/plan_qc53v4w.json
python3 -I $W/patch_d95ec.py $F/tools/die_plan
sha256sum $F/physical/die_plan/qwen_compute/plan_of_record/plan_qc53v4w.json $F/tools/die_plan/landing_collector.py $F/tools/die_plan/clock_landings.py
