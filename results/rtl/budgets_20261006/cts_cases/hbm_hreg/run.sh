#!/bin/bash
# clock-only die CTS case hbm_hreg (hreg); docker on the compute host, admission guard if present
set -o pipefail
D=$(cd "$(dirname "$0")" && pwd)
IMG=${IMG:-openroad/orfs:latest}
CPUS=${CPUS:-8}
run() { docker run --rm --name ckplan_hbm_hreg_$1 --cpus=$CPUS -v $D:/work -w /work $IMG bash -lc \
  "/usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads $CPUS -no_init -exit /work/$1.tcl > /work/$1.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"; }
date -u +%FT%TZ > $D/start
run cts && run meas_SS && run meas_FF
echo $? > $D/exit
date -u +%FT%TZ > $D/end
