#!/bin/bash
# KV-CORE-LAT-HEAD CTS-only what-if on a COPY of a GEOM-reviewed placement (diagnostic; never routed). $1=kit $2=variant(v1|v2) $3=outroot
set -eu
K=$(realpath "$1"); V=$2; O=$3; N=$(basename $K)
W=$O/$V/$N; mkdir -p $O/$V
rsync -a --exclude 'run/results/asap7/*/base/4_*' --exclude 'run/results/asap7/*/base/5_*' --exclude 'run/results/asap7/*/base/6_*' --exclude 'run/logs/asap7/*/base/4_*' $K/ $W/
cp /srv/opentallas-scratch2/claude/kv-core-lat-head/src/head_lane_taps.tcl $W/head_lane_taps.tcl
EX=""; [ "$V" = v4 ] && EX="-e OT_TAP_MAX_SINKS=300 -e OT_TAP_MAX_SPAN_UM=40"
if [ "$V" = v5 ]; then cp /srv/opentallas-scratch2/claude/kv-core-lat-head/src/entry_centre.tcl $W/; P=$(grep -o "PRE_CTS_TCL = /work/[a-z_]*.tcl" $W/config.mk | awk '{print $3}'); printf "source /work/max_fanout.tcl\nsource /work/entry_centre.tcl\n" > $W/${P#/work/}; sed -i 's/^export CTS_ARGS = .*/export CTS_ARGS = -sink_clustering_enable -repair_clock_nets/' $W/config.mk; fi
D=$(ls -d $W/run/results/asap7/*/base); DN=$(basename $(dirname $D))
docker run --rm --name "klh-cts-$V-$N" $EX --memory=24g --memory-swap=24g --cpus=8 -u "$(id -u):$(id -g)" -v "$W":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts" > $O/$V/$N.cts.log 2>&1
docker run --rm --name "klh-ins-$V-$N" --memory=16g -u "$(id -u):$(id -g)" -v $W:/k:ro -v /srv/opentallas-scratch2/claude/kv-core-lat-head/src:/p:ro -v $O/$V:/o \
  -e ODB=/k/run/results/asap7/$DN/base/4_cts.odb -e SDC=/k/run/results/asap7/$DN/base/4_cts.sdc -e SETRC=/k/setRC_rcx.tcl -e FACE=/k/run/results/asap7/$DN/base/ot_face_flops.txt -e OUT=/o/$N.ins.tsv \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /p/ins.tcl" > $O/$V/$N.ins.log 2>&1
echo DONE > $O/$V/$N.done
