#!/bin/bash
# KV-CORE-LAT-HEAD pv_pair CTS-only what-if on a COPY of the reviewed pv3 placement (diagnostic; never routed). $1=v1|v2
set -eu
V=$1; S=/srv/opentallas-scratch2/claude/kv-core-lat-head/src; O=/srv/opentallas-scratch2/claude/kv-core-lat-head/pvwhatif; K=/srv/opentallas-scratch2/claude/codex-kvx-1026/pv3
W=$O/$V/kv3_pv_pair; mkdir -p $O/$V
rsync -a --exclude 'run/results/asap7/*/base/4_*' --exclude 'run/results/asap7/*/base/5_*' --exclude 'run/results/asap7/*/base/6_*' --exclude 'run/logs/asap7/*/base/4_*' $K/ $W/
if [ "$V" = v2 ]; then cp $S/pv_pair_taps_chunk.tcl $W/pv_pair_taps.tcl; fi
if [ "$V" = v5 ]; then cp $S/entry_centre.tcl $W/; printf "source /work/max_fanout.tcl\nsource /work/entry_centre.tcl\n" > $W/pv_pre_cts.tcl; sed -i "s/^export CTS_ARGS = .*/export CTS_ARGS = -sink_clustering_enable -repair_clock_nets/" $W/config.mk; fi
DN=hc_kv3_pv_pair__380_16x190_08
docker run --rm --name "klh-pvcts-$V" --memory=24g --memory-swap=24g --cpus=8 -u "$(id -u):$(id -g)" -v "$W":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts" > $O/$V/cts.log 2>&1
docker run --rm --name "klh-pvins-$V" --memory=16g -u "$(id -u):$(id -g)" -v $W:/k:ro -v $S:/p:ro -v $O/$V:/o \
  -e ODB=/k/run/results/asap7/$DN/base/4_cts.odb -e SDC=/k/run/results/asap7/$DN/base/4_cts.sdc -e SETRC=/k/setRC_rcx.tcl -e FACE=/k/run/results/asap7/$DN/base/ot_face_flops.txt -e OUT=/o/ins.tsv \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /p/ins.tcl" > $O/$V/ins.log 2>&1
echo DONE > $O/$V/done
