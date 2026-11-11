#!/bin/bash
# CPL-QC-2 (copy of CORE-PLACE-1 harness) GRT-only probe arm (DO_NOT_COUNT). usage: run_probe.sh ODB_DIR ARMDIR MOVES DENSITY ITERS ADJ [IMAGE] [GRTMODE]
set -u
P=/srv/opentallas-scratch2/claude/cpl-qc-2/probe
IN=$1; A=$2; MV=$3; DEN=$4; IT=$5; ADJ=$6; IMG=${7:-openroad/orfs:asap7lock}; MODE=${8:-stock}
mkdir -p $P/$A
ENVM=""; [ "$MODE" != stock ] && ENVM="-e OT_GRT_TRANSITION_MODE=$MODE"
echo "CPP_START $(date -Is) arm=$A in=$IN moves=$MV density=$DEN iters=$IT image=$IMG mode=$MODE"
docker run --rm --name cplqc2_$(echo $A | tr / _) --cpus=16 --memory=48g --memory-swap=48g --user $(id -u):$(id -g) $ENVM \
  -e ODB=/in/4_cts.odb -e MOVES=/p/$MV -e OUT=/p/$A -e DENSITY=$DEN -e ITERS=$IT -e "ADJ=$ADJ" \
  -v $P/in/$IN:/in:ro -v $P:/p --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad $IMG \
  -no_init -exit -threads 16 /p/cp_probe.tcl > $P/$A/probe.log 2>&1
echo "CPP_RC=$? $(date -Is)"
grep -E "^Total|CP_PROBE_.*DONE" $P/$A/probe.log | tail -n 3
