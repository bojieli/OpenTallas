#!/bin/bash
# CORES-KITS/KVX t1: CTS only from the reused fd4_cc 3_place (make do-cts: no upstream rebuild). Usage: cts_only.sh MEM_GB CPUS
K=$(cd "$(dirname "$0")" && pwd); MEM=${1:-24}; CPUS=${2:-16}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
$DK run --rm --name kvx-pvp-t1-cts-$$ --cpus=$CPUS --memory=${MEM}g --memory-swap=${MEM}g -v $K:/work -e HUID=$(id -u) -e HGID=$(id -g) \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-cts; rc=\$?; chown -R \$HUID:\$HGID /work/run; exit \$rc"
