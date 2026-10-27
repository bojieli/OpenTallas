#!/bin/bash
# R24 post24.sh NAME: collect / pairs / sta-export (plain + R18 core views) -> HB4 counts -> main die_sta_related. UNCHECKED
P=/srv/opentallas-scratch2/claude/codex-qwen-1027/pkg; R=/srv/opentallas-scratch2/claude/qc-mesh-r24/run; W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r24-1027; S=/srv/opentallas-scratch2/claude/qc-mesh-r24
N=$1; O=/o/$N
D="docker run --rm --memory 12g --cpus 2 -u $(id -u):$(id -g) -e PYTHONPATH=/w/die_plan -e OMP_NUM_THREADS=2 -v $P:/w:ro -v $R:/o -v $W/tools/die_plan:/w/die_plan:ro -w /w ot-ngspice:r3"
PLAN=inputs/d51/plan_d43.json; R2=inputs/d51/r2_plan_d43.json; A=die_plan/clk_aocv_table.json
cat > $R/$N/post.sh <<EOP
M="python3 die_plan/qc_clk_mesh3.py"
\$M collect $O/TT_s0*.json --out $O/die_TT.json > $O/collect_TT.log 2>&1
\$M collect $O/FF_s0*.json --out $O/die_FF.json > $O/collect_FF.log 2>&1
MS='{"TT": "$O/die_TT.json", "FF": "$O/die_FF.json"}'
\$M pairs --r2 $R2 --mesh-skew "\$MS" --aocv $A --out $O/pairs > $O/pairs.log 2>&1
\$M sta-export --r2 $R2 --mesh-skew "\$MS" --aocv $A --out $O/sta_in > $O/sta_in.log 2>&1
\$M sta-export --r2 $R2 --mesh-skew "\$MS" --aocv $A --core-view qfd_dv_s8_crh_rp1=231.2,254.4,181.9,203.8 --core-view qfd_dv_s8x_vmr=249.66,263.16,194.06,206.66 --out $O/sta_in_cv > $O/sta_in_cv.log 2>&1
python3 r11_hb_count.py $PLAN $O/pairs/hold_demand_fragment.json $O/hb4_count.json > $O/hb4.log 2>&1
python3 r11_hb_count.py $PLAN $O/pairs/hold_demand_fragment.json $O/hb4_count_pe.json --per-endpoint > $O/hb4_pe.log 2>&1
EOP
$D sh $O/post.sh
for v in sta sta_cv; do src=sta_in; [ $v = sta_cv ] && src=sta_in_cv
  python3 $W/tools/die_plan/die_sta_related.py $R/$N/$src --plan $P/$PLAN --out $R/$N/$v --pair-unc $R/$N/$src/pair_unc.json > $R/$N/$v.log 2>&1; done
echo POSTDONE $N $(date)
