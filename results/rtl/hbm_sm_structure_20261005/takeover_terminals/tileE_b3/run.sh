#!/bin/bash
# tileE_b3: route, abstract, sign-off corner STA.  Host-side paths; the container sees /src (sources) and /work.
set -u
W=/srv/opentallas-scratch2/scratch/claude/hbm-sm-struct/r1/tileE_b3
S=/srv/opentallas-scratch2/scratch/claude/hbm-sm-struct/src
NEED=24
CORES=24
IMG=openroad/orfs:latest
cd $W
echo "start $(date -Is)" > $W/status
/srv/opentallas-scratch/admit.sh $NEED -- docker run --rm --name claude-smh-tileE_b3 -v $S:/src:ro -v $W:/work \
  -w /OpenROAD-flow-scripts/flow $IMG bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; \
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work \
  FLOW_VARIANT=base NUM_CORES=$CORES finish" > $W/flow.log 2>&1
echo "flow_rc=$?" >> $W/status
B=$(ls -d $W/results/asap7/*/base | head -1)
if [ -f $B/6_final.odb ]; then
  docker run --rm -v $S:/src:ro -v $W:/work $IMG bash -lc \
    "mkdir -p /work/views; for c in ss ff; do /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/abstract_\$c.tcl || exit 1; done" > $W/abstract.log 2>&1
  echo "abstract_rc=$?" >> $W/status
  (cd $S && python3 tools/w18/corner_sta.py --orfs-dir $W --macro physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 --output $W/corner_sta.json) > $W/corner.log 2>&1
  echo "corner_rc=$?" >> $W/status
fi
echo "end $(date -Is)" >> $W/status
