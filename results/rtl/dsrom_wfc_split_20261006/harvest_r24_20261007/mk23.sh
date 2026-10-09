#!/bin/bash
# CLAUDE s81-die r23 = r22 recipe (pre-DRT FF hold ECO HM 32 + SS repair_design, out_* pad 60) with the hold-repair IO
# model at die150 on EVERY port (vclk widened 90 -> 150 ps; r22 signed die150 FF +3.2 on pr_q -> nu_tok and rst_n
# removal +7.6: pr_* / rst_n come from outside the WFC region, so the region 90 ps model under-repaired them)
R=/srv/opentallas-scratch/claude/dsrom-wfc-split
mkdir -p $R/r23/eco && cp $R/r22/eco/* $R/r23/eco/ && cp -a $R/r13/src_u55 $R/r23/
sed -i "s/\$lmin - 90\] \[get_clocks vclk\]/\$lmin - 150] [get_clocks vclk]/; s/\$lmax + 90\] \[get_clocks vclk\]/\$lmax + 150] [get_clocks vclk]/" $R/r23/eco/region_ff.sdc
grep -n "vclk\]" $R/r23/eco/region_ff.sdc
cd $R/r23/src_u55 && rm -f results/asap7/wfc_src_src_u55/base/{5_2*,5_3*,5_route*,6_*,route.guide} status wf_* sta.log check.* flow.log
sed -e "s#/r22#/r23#g; s#r22/#r23/#g; s#claude-wfc-r22#claude-wfc-r23#g" $R/r22/run.sh > $R/r23/run.sh
chmod +x $R/r23/run.sh; grep -c r23 $R/r23/run.sh
cd $R/r23 && (setsid nohup ./run.sh > run.out 2>&1 < /dev/null &)
echo started
