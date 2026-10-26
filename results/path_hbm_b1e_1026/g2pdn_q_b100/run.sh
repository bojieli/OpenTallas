#!/bin/bash
D=$(cd $(dirname $0) && pwd)
docker run --rm --name g2pdn-$$ --cpus=8 --memory=32g --memory-swap=32g -v $D:/work -w /work openroad/orfs:asap7lock   bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/probe.tcl > /work/grt.log 2>&1; echo EXIT \$? > /work/probe.exit; chmod -R a+rwX /work"
python3 /srv/opentallas-scratch2/claude/wt/hbm-b1e-1026/tools/die_plan/g2.py parse $D/grt.log > $D/grt.json 2>/dev/null || true
cat $D/probe.exit
