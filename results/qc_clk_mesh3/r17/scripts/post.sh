M="python3 die_plan/qc_clk_mesh3.py"
$M collect out/d43b/TT_s0*.json --out out/d43b/die_TT.json > out/d43b/collect_TT.log 2>&1
$M collect out/d43b/FF_s0*.json --out out/d43b/die_FF.json > out/d43b/collect_FF.log 2>&1
MS='{"TT": "out/d43b/die_TT.json", "FF": "out/d43b/die_FF.json"}'
$M pairs --r2 inputs/d43/r2_plan_d43.json --mesh-skew "$MS" --aocv die_plan/clk_aocv_table.json --out out/d43b/pairs > out/d43b/pairs.log 2>&1
$M sta-export --r2 inputs/d43/r2_plan_d43.json --mesh-skew "$MS" --aocv die_plan/clk_aocv_table.json --out out/d43b/sta_in > out/d43b/sta_in.log 2>&1
$M sta-export --r2 inputs/d43/r2_plan_d43.json --mesh-skew "$MS" --aocv die_plan/clk_aocv_table.json --core-view qfd_dv_s8_crh_rp1=231.2,254.4,181.9,203.8 --core-view qfd_dv_s8x_vmr=249.66,263.16,194.06,206.66 --out out/d43b/sta_in_cv > out/d43b/sta_in_cv.log 2>&1
python3 r11_hb_count.py inputs/d43/plan_d43.json out/d43b/pairs/hold_demand_fragment.json out/d43b/hb4_count.json > out/d43b/hb4.log 2>&1
chown -R 1000:1000 /w/out
