#!/bin/bash
# cts_only.sh KITDIR [CPUS]: ORFS CTS step only from the copied 3_place checkpoint, then a geometry dump for the render
K=$(cd "$1" && pwd); CPUS=${2:-8}; P=/srv/opentallas-scratch2/claude/s81-cores-split/probe
NAME=s81split-cts-$(basename $K)
docker run --rm --name $NAME --cpus=$CPUS --memory=16g --memory-swap=16g -v $K:/work -v $P:/p:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
 bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-4_1_cts do-4_cts; rc=\$?; \
  B=\$(ls -d /work/run/results/asap7/*/base); mkdir -p /work/geom; \
  [ \$rc = 0 ] && ODB=\$B/4_cts.odb STAGE=cts CORNER=TT OUT=/work/geom openroad -exit /p/ckprobe.tcl > /work/geom/probe_cts.log 2>&1; \
  [ \$rc = 0 ] && ODB=\$B/4_cts.odb STAGE=cts CORNER=FF OUT=/work/geom openroad -exit /p/ckprobe.tcl > /work/geom/probe_cts_ff.log 2>&1; \
  chown -R $(id -u):$(id -g) /work; exit \$rc" > $K/cts_only.log 2>&1
rc=$?; grep -E "OT_RT|CTS-0011|Max level|hold buffers|Error|ERROR" $K/run/logs/asap7/*/base/4_1_cts.log | tail -40; echo "cts_only rc $rc"; exit $rc
