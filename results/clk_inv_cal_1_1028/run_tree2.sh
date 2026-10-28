#!/bin/bash
set -u; M=/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028; cd $M
for t in tree2/*; do for c in TT FF; do
  docker run --rm --memory 2g -u $(id -u):$(id -g) -v $M/$t:/d -w /d openroad/orfs:asap7lock sh -c "zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz > lib_${c}.lib; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_splash -exit sta_${c}.tcl" > $M/$t/sta_${c}.log 2>&1
done; done
ls tree2/*/deck_*.sp | xargs -P 6 -I{} sh -c "d=\$(dirname {}); b=\$(basename {} .sp); docker run --rm --name clkinv2-\$(basename \$d)-\$b --memory 4g --cpus 1 -u $(id -u):$(id -g) -v $M:/w -w /w/\$d ot-ngspice:r3 sh -c \"ngspice -b \$b.sp > \$b.log 2>&1\""
for t in tree2/*; do for c in TT FF; do python3 -I clk_inv_cal.py compare $t --corner $c >> $M/compare2.txt 2>&1; done; done
echo "TREES2DONE $(date)" >> run.log
