#!/bin/bash
# HBM-IR8: solve one window case dir with the pinned ORFS image
W=$(readlink -f $1)
docker run --rm --name otir8-$(basename $(dirname $W))-$(basename $W)-$$ --cpus=8 --memory=32g -v "$W":/work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -no_init -exit /work/run.tcl > /work/run.log 2>&1; echo \$? > /work/run.exit; chmod -R a+rwX /work"
