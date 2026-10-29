#!/bin/bash
# MODEL-CORR-1: OpenSTA + ngspice of every reference case (intel1 docker, 1 CPU / <=4 GB each)
set -u
M=/srv/opentallas-scratch2/claude/model-corr-1-1028; cd $M
log(){ echo "$1 $(date)" >> $M/run.log; }
log START
for d in ref/*; do [ -f $d/chain.v ] || continue; for c in TT FF; do
  docker run --rm --memory 2g -u $(id -u):$(id -g) -v $M/$d:/d -w /d openroad/orfs:asap7lock sh -c "zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz > lib_${c}.lib; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_splash -exit sta_${c}.tcl" > $M/$d/sta_${c}.log 2>&1
done; done
log STA
ls ref/*/deck_*.sp | xargs -P 18 -I{} sh -c 'd=$(dirname {}); b=$(basename {} .sp); docker run --rm --name mcorr-$(basename $d)-$b --memory 4g --cpus 1 -u '$(id -u):$(id -g)' -v '$M'/lib:/w/lib:ro -v '$M'/osdi:/w/osdi:ro -v '$M'/$d:/d -w /d ot-ngspice:r3 sh -c "ngspice -b $b.sp > $b.log 2>&1"'
log SPICE
python3 -I tools/model_corr.py collect $M/ref --out $M/raw.json >> $M/run.log 2>&1
log ALLDONE
