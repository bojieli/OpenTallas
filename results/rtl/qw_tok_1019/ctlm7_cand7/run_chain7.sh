#!/bin/bash
docker run --rm -u $(id -u):$(id -g) -v /srv/opentallas-scratch/claude/qw-ctlm7-1020:/work -w /work/src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; bash chain7.sh'
