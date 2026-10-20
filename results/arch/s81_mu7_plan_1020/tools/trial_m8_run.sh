#!/bin/bash
D=$(cd $(dirname $0) && pwd); N=mu7m8-$$
docker run --rm --name $N --cpus=16 --memory=90g -v /srv/opentallas-scratch/claude/s81-mu5/case_mu5k:/in:ro -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\$?; chmod -R a+rwX /work/out; exit \$rc"
rc=$?; echo $rc > $D/out/run.exit; exit $rc
