#!/bin/bash
# detached: resume_eco.sh + post-route STA (usage: run_chain_eco.sh SRC NEW MARGIN [SM])
T=/srv/opentallas-scratch/claude/dsrom-qtclose; R=$2
mkdir -p $T/jobs/$R; rm -rf $T/sta/$R
$T/post_sta_qz.sh $R $T/wt-0032b7355 > $T/post_$R.log 2>&1 &
$T/resume_eco.sh "$@"
wait
