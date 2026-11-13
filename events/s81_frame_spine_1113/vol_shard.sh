#!/bin/bash
# shard.sh ITEM : cp_frame (seed only) + full street check for one base item, into sh/ITEM/
W=/srv/opentallas-scratch3/claude/wt/frame-forms-1; E=$W/events/s81_frame_spine_1113; A=/srv/opentallas-scratch3/claude/frame-forms-1/all1; F=/srv/opentallas-scratch3/claude/frame-forms-1
T=$(cat $A/sh/$1.txt); O=$A/sh/$1; rm -rf $O; mkdir -p $O; cd $A
OMP_NUM_THREADS=8 nice python3 -I $E/cp_frame.py $W/tools/die_plan $A/plan_A_tp.json --die s81 --repo $W --types $T --seed $A/seed_all.json --no-search --gap 0.5 --reach 395 --out-plan $O/plan.json --event $O/ev.json --svg $O/svg > $O/log.txt 2>&1; echo CP_RC=$? > $O/rc
cd $F/srfull/die_plan && nice python3 -I street_rule.py check $O/plan.json --die s81 --repo $W --types $T --out $O/street_full.json > $O/street.log 2>&1; echo SR_RC=$? >> $O/rc
