#!/bin/bash
# windowed G2 GRT probe (diagnostic, owner 10-23: docker with --memory = --memory-swap, not ot-run)
D=$(cd $(dirname $0) && pwd); N=dhbm41-gwin-$(basename $D)
docker run --rm --name $N --cpus=4 --memory=24g --memory-swap=24g -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/probe.tcl > /work/grt.log 2>&1; echo EXIT \$? > /work/probe.exit; chmod -R a+rwX /work"
python3 /srv/opentallas-scratch2/claude/die-hbm-38/g2tools/die_plan/g2.py parse $D/grt.log > $D/grt.json 2>/dev/null || true
cat $D/probe.exit
