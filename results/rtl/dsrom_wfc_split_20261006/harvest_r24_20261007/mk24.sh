#!/bin/bash
# r24 = r23 (die150 hold-ECO IO model) + SS repair_design slew margin 30 / cap 20 (r23: 2 SS/FF slew violators place28557/8 -30/-10 ps after the hold buffers)
# CLAUDE s81-die r24 = r22 recipe (pre-DRT FF hold ECO HM 32 + SS repair_design, out_* pad 60) with the hold-repair IO
# model at die150 on EVERY port (vclk widened 90 -> 150 ps; r22 signed die150 FF +3.2 on pr_q -> nu_tok and rst_n
# removal +7.6: pr_* / rst_n come from outside the WFC region, so the region 90 ps model under-repaired them)
R=/srv/opentallas-scratch/claude/dsrom-wfc-split
mkdir -p $R/r24/eco && cp $R/r23/eco/* $R/r24/eco/ && cp -a $R/r13/src_u55 $R/r24/
grep -n "vclk\]" $R/r24/eco/region_ff.sdc
sed -i "s/repair_design -slew_margin 15 -cap_margin 10/repair_design -slew_margin 30 -cap_margin 20/" $R/r24/eco/grt_drv.tcl; grep -n repair_design $R/r24/eco/grt_drv.tcl
cd $R/r24/src_u55 && rm -f results/asap7/wfc_src_src_u55/base/{5_2*,5_3*,5_route*,6_*,route.guide} status wf_* sta.log check.* flow.log
sed -e "s#/r22#/r24#g; s#r22/#r24/#g; s#claude-wfc-r22#claude-wfc-r24#g" $R/r22/run.sh > $R/r24/run.sh
chmod +x $R/r24/run.sh; grep -c r24 $R/r24/run.sh
cd $R/r24 && (setsid nohup ./run.sh > run.out 2>&1 < /dev/null &)
echo started
