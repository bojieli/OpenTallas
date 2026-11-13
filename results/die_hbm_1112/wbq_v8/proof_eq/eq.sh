#!/bin/bash
D=/srv/opentallas-scratch2/claude/hbm-cores-c/v8eq
docker run --rm --memory=24g --memory-swap=24g --cpus=4 -v $D:/eq -w /eq openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l /eq/eq.log /eq/eq.ys > /dev/null 2>&1; echo rc=$? > /eq/eq.rc'
