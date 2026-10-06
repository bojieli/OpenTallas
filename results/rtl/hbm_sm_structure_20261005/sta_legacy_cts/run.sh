#!/bin/bash
J=/srv/opentallas/scratch-overflow/claude/hbm-sm-struct/sta_full
S=/srv/opentallas-scratch/claude/hbm-fmax-sm/src
W=/srv/opentallas-scratch/claude/hbm-fmax-sm/routes/sm_r2/work/orfs
c=$1
/srv/opentallas-scratch/admit.sh 40 -- docker run --rm --name claude-hbmsm-sta-$c -v "$J:/query" -v "$W:/retained:ro" -v "$S:/src:ro" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads 4 -no_init -exit /query/full_$c.tcl" > $J/full_$c.log 2>&1
echo $? > $J/full_$c.exit
