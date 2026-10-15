#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
base=rtl/hbm_accel/generic/peers/static_hc
wm=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
xm=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
iverilog -g2012 -s tb_hgi_hc_weight_quarter_static -o "$out/weight.vvp" "$base/ot_hgi_hc_weight_quarter_static.sv" rtl/test/tb_hgi_hc_weight_quarter_static.sv "$wm" >"$out/weight.compile.log" 2>&1
for bank in 0 1 2 3 4 5 6 7;do for q in 0 1 2 3;do
 vvp "$out/weight.vvp" +bank=$bank +quarter=$q >"$out/weight-b$bank-q$q.log" 2>&1
 grep 'WEIGHT_QUARTER PASS' "$out/weight-b$bank-q$q.log"
done;done
iverilog -g2012 -s tb_hgi_hc_weight_quarter_static -Ptb_hgi_hc_weight_quarter_static.MUT=1 -o "$out/weight_mut.vvp" "$base/ot_hgi_hc_weight_quarter_static.sv" rtl/test/tb_hgi_hc_weight_quarter_static.sv "$wm" >"$out/weight_mut.compile.log" 2>&1
set +e
vvp "$out/weight_mut.vvp" +bank=3 +quarter=2 >"$out/weight_mut.log" 2>&1;rc1=$?
vvp "$out/weight.vvp" +bank=3 +quarter=2 +wrong_id=1 >"$out/weight_id_mut.log" 2>&1;rc2=$?
set -e
[[ $rc1 != 0 && $rc2 != 0 ]];grep 'WEIGHT_QUARTER mismatch' "$out/weight_mut.log" "$out/weight_id_mut.log"
iverilog -g2012 -s tb_hgi_hc_residual_half_static -o "$out/residual.vvp" "$base/ot_hgi_hc_residual_half_static.sv" rtl/test/tb_hgi_hc_residual_half_static.sv "$xm" >"$out/residual.compile.log" 2>&1
vvp "$out/residual.vvp" >"$out/residual.log" 2>&1;grep 'RESIDUAL_HALF PASS' "$out/residual.log"
python3 - "$base/ot_hgi_hc_residual_half_static.sv" "$out/residual_mut.sv" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text();assert '.w_ce_in(wv_q)' in s
pathlib.Path(sys.argv[2]).write_text(s.replace('.w_ce_in(wv_q)','.w_ce_in(write_v)'))
PY
iverilog -g2012 -s tb_hgi_hc_residual_half_static -o "$out/residual_mut.vvp" "$out/residual_mut.sv" rtl/test/tb_hgi_hc_residual_half_static.sv "$xm" >"$out/residual_mut.compile.log" 2>&1
set +e
vvp "$out/residual_mut.vvp" >"$out/residual_mut.log" 2>&1;rc=$?
set -e
[[ $rc != 0 ]];grep 'RESIDUAL_HALF write_phase mismatch' "$out/residual_mut.log"
