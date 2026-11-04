#!/bin/bash
P=/srv/opentallas-scratch2/claude/die-qc-66-nlcf/probe
docker run --rm --name dq66nl-probe-$$ --cpus=8 --memory=40g --memory-swap=40g -v $P:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-4_1_cts; rc=\$?; chown -R $(id -u):$(id -g) /work/run; exit \$rc" > $P/probe_cts.log 2>&1
echo "PROBE rc=$? $(date)" >> $P/../status
