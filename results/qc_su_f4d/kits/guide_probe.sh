#!/bin/bash
K=$1; P=$2; mkdir -p $P
HB=$(ls -d $K/run/results/asap7/*/base); B=/work/run/results/asap7/$(basename $(dirname $HB))/base
docker run --rm --name f4d-gprobe-$(basename $K) --cpus=16 --memory=24g --memory-swap=24g -v $K:/work:ro -v $P:/out -v $P/guide_probe.tcl:/p.tcl:ro \
  -e ODB=$B/5_1_grt_f4c.odb -e GUIDE=/out/route_v2.guide ${DRT:+-e DRT=1} openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /p.tcl' > $P/probe.log 2>&1
docker run --rm -v $P:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out
