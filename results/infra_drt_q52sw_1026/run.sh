#!/bin/bash
D=/srv/opentallas-scratch2/claude/infra-r5-1026/drt
docker run --rm --name infra_r5_drt_q52sw --cpus=16 --memory=48g --memory-swap=48g -v $D:/d -v /srv/opentallas-scratch2/claude/codex-qc-v4-probe-1026/clockkit:/work:ro -v /srv/opentallas-scratch2/claude/infra-r4-1026/drt:/src:ro openroad/orfs:asap7lock \
  bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; OT_MODE=drt /usr/bin/time -v openroad -threads 16 -exit /d/route_r5.tcl > /d/route_r5.log 2>&1; echo EXIT \$? >> /d/route_r5.log; chown -R 1000:1000 /d"
