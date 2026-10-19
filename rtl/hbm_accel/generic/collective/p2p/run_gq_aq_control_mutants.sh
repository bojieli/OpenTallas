#!/bin/bash
set -euo pipefail
P=rtl/hbm_accel/generic/collective/p2p
O=$(realpath -m "${1:?output directory required}");mkdir -p "$O"
V=${VERILATOR:-verilator}
MEM=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sed 's/ot_hbm_xp_aq_tree13 #/ot_hgi_coll_aq13 #/' physical/hbm_xp_aq_tree13_1014/tb_aq_tree13.sv > "$O/tb.sv"
for m in EC SHIFT;do
 "$V" --binary --timing -j 8 -DOT_GQ_FAN32 -DOT_COLLQ_SRAM -DOT_GQ_MUT_${m}_CTL -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb --Mdir "$O/$m" "$O/tb.sv" "$P/ot_hgi_coll_aq13.sv" "$P/ot_hgi_coll_aq_scale13r.sv" rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_hc.sv rtl/hdc/ot_hdc_cg.sv "$MEM" > "$O/$m.build.log" 2>&1 || { tail -20 "$O/$m.build.log";exit 2; }
 "$O/$m/Vtb" > "$O/$m.log" 2>&1 || true
 grep -q 'AQ_TREE13_NUMERIC_MISMATCH' "$O/$m.log" || { tail -8 "$O/$m.log";echo "AQ_CONTROL_MUTANT $m escaped/invalid";exit 1; }
 grep -m1 AQ_TREE13_NUMERIC_MISMATCH "$O/$m.log"
 echo "AQ_CONTROL_MUTANT $m REJECTED"
done
"$V" --binary --timing -j 8 -DOT_GQ_FAN32 -DOT_GQ_MUT_SCALE_CTL -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_aq_scale13r_eq --Mdir "$O/SCALE" "$P/tb_aq_scale13r_eq.sv" "$P/ot_hgi_coll_aq_scale13r.sv" physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv > "$O/SCALE.build.log" 2>&1 || { tail -20 "$O/SCALE.build.log";exit 2; }
"$O/SCALE/Vtb_aq_scale13r_eq" > "$O/SCALE.log" 2>&1 || true
grep -q 'SCALE13R_EQ FAIL errors=' "$O/SCALE.log" || { tail -8 "$O/SCALE.log";echo 'SCALE_CONTROL_MUTANT escaped/invalid';exit 1; }
grep 'SCALE13R_EQ FAIL' "$O/SCALE.log"
echo 'AQ_CONTROL_MUTANT SCALE REJECTED'
"$V" --binary --timing -j 8 -DOT_GQ_FAN32 -DOT_GQ_MUT_SCALE_DATA -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_aq_scale13r_eq --Mdir "$O/DATA" "$P/tb_aq_scale13r_eq.sv" "$P/ot_hgi_coll_aq_scale13r.sv" physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv > "$O/DATA.build.log" 2>&1 || { tail -20 "$O/DATA.build.log";exit 2; }
"$O/DATA/Vtb_aq_scale13r_eq" > "$O/DATA.log" 2>&1 || true
grep -q 'SCALE13R_EQ FAIL errors=' "$O/DATA.log" || { tail -8 "$O/DATA.log";exit 1; }
grep 'SCALE13R_EQ FAIL' "$O/DATA.log"
echo 'AQ_CONTROL_MUTANT SCALE_DATA REJECTED' 
