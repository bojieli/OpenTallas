set -e
M="python3 die_plan/qc_clk_mesh3.py"; O=out/isl; A=die_plan/clk_aocv_table.json
MS="{\"TT\": \"$O/die_TT.json\", \"FF\": \"$O/die_FF.json\"}"
$M pairs --r2 inputs/r2_plan_w.json --mesh-skew "$MS" --aocv $A --out $O/pairs > $O/pairs.log 2>&1
$M sta-export --r2 inputs/r2_plan_w.json --mesh-skew "$MS" --aocv $A --out $O/sta_in > $O/sta_in.log 2>&1
$M sta-export --r2 inputs/r2_plan_w.json --mesh-skew "$MS" --aocv $A --core-view qfd_dv_s8_crh_rp1=230.56,264.36,180.35,211.55 --core-view qfd_dv_s8x_vmr=249.66,263.16,194.06,206.66 --out $O/sta_in_cv > $O/sta_in_cv.log 2>&1
