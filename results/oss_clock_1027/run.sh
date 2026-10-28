#!/bin/bash
# OSS-CLOCK: OpenSTA + ngspice on one mscts region tree dir ($1), corner $2
D=$(readlink -f $1); C=$2; L=/srv/opentallas-scratch2/claude/clk-aocv-1026/mc
docker run --rm --memory 4g -v $D:/d -w /d openroad/orfs:asap7lock sh -c "zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz > lib_${C}.lib && head -c 2000 lib_${C}.lib | grep -E \"nom_(voltage|temperature)\" ; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_splash -exit sta_${C}.tcl" > $D/sta_${C}.log 2>&1
docker run --rm --memory 8g --name ossclk_$(basename $D)_$C -v $L/lib:/w/lib:ro -v $L/osdi:/w/osdi:ro -v $D:/d -w /d ot-ngspice:r3 sh -c "ngspice -b deck_${C}.sp" > $D/ngspice_${C}.log 2>&1
echo done $(date) >> $D/ngspice_${C}.log
