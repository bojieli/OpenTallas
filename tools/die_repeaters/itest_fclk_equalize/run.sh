#!/bin/bash
D=$(cd $(dirname $0) && pwd)  # copy fclk_audit.tcl + die_repeaters.tcl from .. next to t.tcl first; mkdir -p $D/out
docker run --rm --cpus=2 --memory=4g -v $D:/work -w /work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/t.tcl > /work/out/t.log 2>&1; rc=\$?; chmod -R a+rwX /work/out; exit \$rc"
rc=$?; tail -12 $D/out/t.log; exit $rc
