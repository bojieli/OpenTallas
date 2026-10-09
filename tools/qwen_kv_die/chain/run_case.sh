#!/bin/bash
# usage: run_case.sh <case_dir> <tcl> <log> <cpus> <mem_gb>
# Runs one OpenROAD case in the pinned ORFS image, detached-safe: writes <log>, <log>.exit, <log>.time
set -u
D=$(readlink -f "$1"); TCL=$2; LOG=$3; CPUS=${4:-16}; MEM=${5:-200}
NAME=qfd_$(basename $D)_$(basename $TCL .tcl)
date -u +%FT%TZ > $D/$LOG.start
docker run --rm --name $NAME --cpus=$CPUS --memory=${MEM}g -e OT_ORFS_NUM_CORES=$CPUS -v $D:/work -w /work ${IMAGE:-openroad/orfs:asap7lock} \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $CPUS -no_init -exit /work/$TCL > /work/$LOG 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/$LOG.exit
date -u +%FT%TZ > $D/$LOG.end
