#!/bin/bash
# R15 post: collect MC -> pairs -> sta-export (plain + RP1 F4G RCX + VMR GRT core views) -> related-pair die STA. UNCHECKED
P=/srv/opentallas-scratch2/claude/qc-mesh-r12/pkg; W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r15-1026
O=out/r15; cd $P
D="docker run --rm --memory 16g --cpus 4 -v $P:/w -v $W/tools/die_plan:/w/die_plan:ro -w /w ot-ngspice:r3"
M="python3 die_plan/qc_clk_mesh3.py"; A=die_plan/clk_aocv_table.json
$D sh -c "$M collect $O/TT_s0*.json --out $O/die_TT.json > $O/collect_TT.log 2>&1; $M collect $O/FF_s0*.json --out $O/die_FF.json > $O/collect_FF.log 2>&1;
MS='{\"TT\": \"$O/die_TT.json\", \"FF\": \"$O/die_FF.json\"}';
$M pairs --r2 inputs/r2_plan_w.json --mesh-skew \"\$MS\" --aocv $A --out $O/pairs > $O/pairs.log 2>&1;
$M sta-export --r2 inputs/r2_plan_w.json --mesh-skew \"\$MS\" --aocv $A --out $O/sta_in > $O/sta_in.log 2>&1;
$M sta-export --r2 inputs/r2_plan_w.json --mesh-skew \"\$MS\" --aocv $A --core-view qfd_dv_s8_crh_rp1=231.2,254.4,181.9,203.8 --core-view qfd_dv_s8x_vmr=249.66,263.16,194.06,206.66 --out $O/sta_in_cv > $O/sta_in_cv.log 2>&1;
chown -R $(id -u):$(id -g) /w/out"
for v in sta sta_cv; do
  src=sta_in; [ $v = sta_cv ] && src=sta_in_cv
  python3 $W/tools/die_plan/die_sta_related.py $P/$O/$src --plan $P/inputs/candidate_oneqc0733.json --out $P/$O/$v --pair-unc $P/$O/$src/pair_unc.json > $P/$O/$v.log 2>&1
done
tail -3 $O/sta.log $O/sta_cv.log
