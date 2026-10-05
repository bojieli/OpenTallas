#!/bin/bash
# HBM accelerator control-loop SS screens (2026-10-04). Usage: screens.sh <round> <label> <screen args...>
# Runs on ot-epyc1tb under /srv/opentallas-scratch/claude/hbm-clock-loops; src/ = rsync of the branch worktree.
R=/srv/opentallas-scratch/claude/hbm-clock-loops
rnd=$1; lab=$2; shift 2
O=$R/runs/$rnd; mkdir -p $O
cd $R/src
export OT_SCREEN_ROOT=$R/src
exec /srv/opentallas-scratch/admit.sh ${NEED:-6} -- python3 jobs/screen.py --work $O/$lab --output $O/$lab.json --label $lab "$@" > $O/$lab.log 2>&1
