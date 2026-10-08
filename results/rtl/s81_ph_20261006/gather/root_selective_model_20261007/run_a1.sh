#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/scratch/codex/root-selective-20261007
for c in ff ss; do
 docker run --rm -v /srv/opentallas-scratch2/scratch/claude/closure-loop/s81ph-root_tile-77bcb3f3c/src:/src:ro -v /srv/opentallas-scratch2/scratch/claude/closure-loop/s81ph-root_tile-77bcb3f3c/cl/eco/pass2/orfs:/work:ro -v /srv/opentallas-scratch2/scratch/codex/root-selective-20261007:/case sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -exit /case/a1_$c.tcl" > "a1_$c.log" 2>&1
 echo $? > "a1_$c.rc"
done
