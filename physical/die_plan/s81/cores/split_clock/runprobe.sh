#!/bin/bash
# runprobe.sh KIT NAME STAGE CORNER  (diagnostic probe; docker --memory 24g)
K=$1; N=$2; ST=$3; C=$4
O=/srv/opentallas-scratch2/claude/s81-cores-split/probe/$N; mkdir -p $O
B=$(ls -d $K/run/results/asap7/*/base); 
case $ST in cts) ODB=$B/4_cts.odb;; grt) ODB=$B/5_1_grt.odb;; rcx) ODB=$B/6_final.odb;; esac
docker run --rm --name s81split-probe-$N-$ST-$C --memory 24g --cpus 4 -v $K:/work:ro -v $O:/out -v /srv/opentallas-scratch2/claude/s81-cores-split/probe:/p:ro \
  -e ODB=${ODB/$K//work} -e SPEF=${B/$K//work}/6_final.spef -e STAGE=$ST -e CORNER=$C -e OUT=/out openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /p/ckprobe.tcl" > $O/probe_${ST}_$C.log 2>&1
tail -2 $O/probe_${ST}_$C.log
