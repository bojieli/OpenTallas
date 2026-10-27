#!/bin/bash
# R18 pipe18.sh NAME [extra solve args]: MC 13+nom TT/FF on the R17 d43b plan (inputs read-only from the R17 pkg)
# -> collect / pairs / sta-export (plain + RP1 F4G RCX / VMR GRT core views) -> related-pair STA -> HB4 count.  UNCHECKED
P=/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg; R=/srv/opentallas-scratch2/claude/qc-mesh-r18/run; W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r18-1027
N=$1; shift; X="$*"
O=/o/$N; mkdir -p $R/$N
D="docker run --rm --memory 12g --cpus 2 -e PYTHONPATH=/w/die_plan -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -v $P:/w:ro -v $R:/o -v $W/tools/die_plan:/w/die_plan:ro -v $HOME/.cache/opentallas:/root/.cache/opentallas:ro -w /w ot-ngspice:r3"
PLAN=inputs/d43/plan_d43.json; R2=inputs/d43/r2_plan_d43.json
SA="--r2 $R2 --stage inputs/stage_table.json --lanes vss --islands type --feed periodic --island-edge-sym --row-at 10471.68=10445.76,5227.2=5218.56 --lift-lane deepest --row-slots holder --centre-channel 43.2 --centre-split 30.24"
for C in TT FF; do for S in $(seq 0 13); do
  F=$(printf %s_s%03d $C $S)
  echo "python3 die_plan/qc_clk_mesh3.py solve $SA --no-spine --top-w 16w --top-m 2 --top-reach 450 --thev inputs/thev_r2.json --slew-sens inputs/slew_sens.json --r9-dir r10_inputs --corner $C --sample $S $X --out $O/$F.json > $O/$F.log 2>&1"
done; done > $R/$N/solve.lst
split -n l/14 -d $R/$N/solve.lst $R/$N/solve_part_
[ -n "${POST_ONLY:-}" ] || { for f in $R/$N/solve_part_*; do $D sh /o/$N/$(basename $f) & done; wait; }
A=die_plan/clk_aocv_table.json
cat > $R/$N/post.sh <<EOP
M="python3 die_plan/qc_clk_mesh3.py"
\$M collect $O/TT_s0*.json --out $O/die_TT.json > $O/collect_TT.log 2>&1
\$M collect $O/FF_s0*.json --out $O/die_FF.json > $O/collect_FF.log 2>&1
MS='{"TT": "$O/die_TT.json", "FF": "$O/die_FF.json"}'
\$M pairs --r2 $R2 --mesh-skew "\$MS" --aocv $A --out $O/pairs > $O/pairs.log 2>&1
\$M sta-export --r2 $R2 --mesh-skew "\$MS" --aocv $A --out $O/sta_in > $O/sta_in.log 2>&1
\$M sta-export --r2 $R2 --mesh-skew "\$MS" --aocv $A --core-view qfd_dv_s8_crh_rp1=231.2,254.4,181.9,203.8 --core-view qfd_dv_s8x_vmr=249.66,263.16,194.06,206.66 --out $O/sta_in_cv > $O/sta_in_cv.log 2>&1
python3 r11_hb_count.py $PLAN $O/pairs/hold_demand_fragment.json $O/hb4_count.json > $O/hb4.log 2>&1
chown -R $(id -u):$(id -g) /o/$N
EOP
$D sh $O/post.sh
for v in sta sta_cv; do src=sta_in; [ $v = sta_cv ] && src=sta_in_cv
  python3 $W/tools/die_plan/die_sta_related.py $R/$N/$src --plan $P/$PLAN --out $R/$N/$v --pair-unc $R/$N/$src/pair_unc.json > $R/$N/$v.log 2>&1; done
echo DONE $N $(date)
