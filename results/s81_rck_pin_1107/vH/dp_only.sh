#!/bin/bash
# S81-RCK-6 vH: detail place only on vG's 3_4_place_resized (same netlist; vG passed every pre-floor gate on it).
# Same container preamble as run_kit.sh; the runner itself would start a second LEC on the same netlist.
K=/srv/opentallas-scratch3/claude/s81-rck-6/vH/serdes__t16
rm -f $K/FAIL_PREFLOOR
docker run --rm --name dpkit-vH-dp-$$ --cpus=4 --memory=24g --memory-swap=24g -v $K:/work -e HUID=$(id -u) -e HGID=$(id -g) -e OT_KIT_IR=defer \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts --metrics-only > /work/orfs_metrics.log 2>&1 || exit 9; \
 M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4'; \
 bash /work/grt183_make.sh \$M do-3_5_place_dp do-3_place; rc=\$?; chown -R \$HUID:\$HGID /work; exit \$rc" > $K/run_dp_only.log 2>&1
rc=$?; tail -4 $K/run_dp_only.log; grep -E 'RCK_TX_(CONTROL|COHORT)|OT_CLOCK_TAPS GROUPS|RCK_TX_COMPACT released|Error' $K/run_dp_only.log | cut -c1-400; exit $rc
