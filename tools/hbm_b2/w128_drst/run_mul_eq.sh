#!/bin/bash
# valid-masked mul equivalence (k-induction) + two mutants that must be caught
set -uo pipefail
cd "$(dirname "$0")"; Y=$HOME/.local/opentallas-tools/bin/yosys; S=../src
mkdir -p mul_eq; cd mul_eq
# mutant MV: cut C3 treats bit W3-2 (byp) as the valid -> real valid bit unreset (reset-delivery bug)
sed -e 's/module ot_hdc_fp32_mul_lat #(/module ot_hdc_fp32_mul_lat_mv #(/' -e 's/u_c3 (.clk/u_c3x (.clk/' \
    -e 's/(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-1))/(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-2))/' $S/ot_hdc_fp32_mul_lat.sv \
    | awk '/^module ot_hdc_fp32_mul_lat_mv/{p=1} p{print} p&&/^endmodule/{exit}' > mul_mv.sv
# mutant MD: one output data bit flipped in the valid-only-reset output stage
sed -e 's/module ot_hdc_fp32_mul_lat #(/module ot_hdc_fp32_mul_lat_md #(/' \
    -e 's/else begin y <= (e_code\[30:0\] == 31.d0) ? 32.d0 : e_code; err <= E_NONE; end\r\?$/&/' $S/ot_hdc_fp32_mul_lat.sv \
    | awk '/^module ot_hdc_fp32_mul_lat_md/{p=1} p{print} p&&/^endmodule/{exit}' \
    | awk '/g_output_valid_reset/{m=1} m&&/else begin y <= \(e_code/ && !done {sub(/: e_code;/,": e_code ^ 32'"'"'h1;"); done=1} {print}' > mul_md.sv
grep -c "W3-2" mul_mv.sv; grep -c "e_code ^ 32'h1" mul_md.sv
FILES="$S/ot_hdc_prefix.sv $S/ot_hdc_fastfp.sv $S/ot_hdc_fp32_add_lat.sv $S/ot_hdc_fp32_mul_lat.sv"
for mode in gate MUT_VALID MUT_DATA; do
  D=""; X=""; [ $mode = MUT_VALID ] && { D="-DMUT_VALID"; X=mul_mv.sv; }; [ $mode = MUT_DATA ] && { D="-DMUT_DATA"; X=mul_md.sv; }
  cat > $mode.ys <<YS
read_verilog -sv -DSYNTHESIS $D $FILES $X ../mul_miter.sv
hierarchy -check -top mul_miter
proc; flatten; opt_clean; async2sync; opt -fast
sat -tempinduct -prove ok 1 -set-at 1 rst_n 0 -maxsteps 24 -show-ports -dump_vcd $mode.vcd
YS
  $Y -ql $mode.log -s $mode.ys; rc=$?; echo "$mode rc=$rc" | tee -a status.txt
  grep -E "Induction step proven|SUCCESS|FAIL|failed|Reached maximum" $mode.log | tail -3
done
