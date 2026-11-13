#!/bin/bash
docker run --rm --memory=24g --memory-swap=24g --cpus=4 -v /srv/opentallas-scratch2/claude/hbm-cores-c/v8eq2:/eq -w /eq openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for g in g0 g1; do yosys -l /eq/eq_$g.log /eq/eq_$g.ys > /dev/null 2>&1; echo $g rc=\$? >> /eq/eq.rc; done'
