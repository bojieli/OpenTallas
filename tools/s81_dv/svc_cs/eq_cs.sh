#!/bin/bash
# eq_cs.sh REPO UNIT [MUT]: yosys sequential equivalence of an S81 census-safe copy against its rtl/hdc original
# (gold = the original, gate = the copy; matched by flattened register names, equiv_simple + equiv_induct).
# UNIT: mul | add | add5x | exp | fdiv.  MUT=1 applies a mutant to the copy (must FAIL).  Run in the ORFS image (yosys on PATH).
set -u
R=${1:-/src}; U=$2; MUT=${3:-0}; T=${EQ_T:-$(mktemp -d)}; mkdir -p $T
D=$R/rtl/dsrom_sys/s81_svc
cp $D/ot_s81_svc_fp32_f12_cs.sv $D/ot_s81_svc_exp_cs.sv $D/ot_s81_svc_fdiv_f12_cs.sv $T/
if [ "$MUT" = 1 ]; then
  sed -i 's/top_b <= prod\[47\]/top_b <= prod[46]/; s/lzb <= lz_w\[4:0\];/lzb <= lz_w[4:0] ^ 5'"'"'d2;/' $T/ot_s81_svc_fp32_f12_cs.sv
  sed -i 's/f1_sh_b  <= (sh_full > 11.d25) ? 5.d25 : sh_full\[4:0\];/f1_sh_b <= sh_full[4:0] ^ 5'"'"'d1;/' $T/ot_s81_svc_fdiv_f12_cs.sv
  sed -i 's/nk <= nint_dn;/nk <= nint_dn ^ 8'"'"'h01;/' $T/ot_s81_svc_exp_cs.sv
fi
if [ "$MUT" = 1 ]; then n=0; for f in ot_s81_svc_fp32_f12_cs.sv ot_s81_svc_exp_cs.sv ot_s81_svc_fdiv_f12_cs.sv; do cmp -s $D/$f $T/$f || n=$((n+1)); done; [ $n -gt 0 ] || { echo "EQ $U MUT=1: ABORT (mutant not applied)"; exit 3; }; fi
H=$R/rtl/hdc
LIB="$H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_f12.sv $H/ot_hdc_fastfp_lat_f12.sv $H/ot_hdc_delay.sv $H/ot_hdc_sfu.sv $H/v41x/ot_hdc_v41x_sfu.sv $T/ot_s81_svc_fp32_f12_cs.sv $T/ot_s81_svc_exp_cs.sv $H/v41x/ot_dsrom_su_fdiv_f12.sv $T/ot_s81_svc_fdiv_f12_cs.sv $H/ot_hdc_cg.sv"
cat > $T/w.sv <<'V'
module g_mul(input clk, rst_n, valid_in, input [31:0] a, b, output [31:0] y, output [1:0] err, output valid_out, output [31:0] yx, yx2);
  ot_hdc_fp32_mul_f12 #(.CUTS(8'b01101010)) u(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(y),.err(err),.valid_out(valid_out));
  assign yx = y; assign yx2 = y;
endmodule
module c_mul(input clk, rst_n, valid_in, input [31:0] a, b, output [31:0] y, output [1:0] err, output valid_out, output [31:0] yx, yx2);
  ot_s81_svc_mul_f12_cs #(.CUTS(8'b01101010), .YXR(3)) u(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(y),.err(err),.valid_out(valid_out),.yx(yx),.yx2(yx2));
endmodule
module g_add(input clk, rst_n, valid_in, input [31:0] a, b, output [31:0] y, output [1:0] err, output valid_out);
  ot_hdc_fp32_add_f12 #(.CUTS(6'b101010)) u(.*);
endmodule
module c_add(input clk, rst_n, valid_in, input [31:0] a, b, output [31:0] y, output [1:0] err, output valid_out);
  ot_s81_svc_add_f12_cs #(.CUTS(6'b101010)) u(.*);
endmodule
module g_add5x(input clk, rst_n, valid_in, input [31:0] a, b, output [31:0] y, output [1:0] err, output valid_out);
  ot_hdc_fp32_add_f12_l5x u(.*);
endmodule
module c_add5x(input clk, rst_n, valid_in, input [31:0] a, b, output [31:0] y, output [1:0] err, output valid_out);
  ot_s81_svc_add_f12_l5x_cs u(.*);
endmodule
module g_exp(input clk, rst_n, v, input [31:0] x, output [31:0] y, output vo, fault);
  ot_hdc_v41x_exp #(.LM(5), .LA(4)) u(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(y),.vo(vo),.fault(fault));
endmodule
module c_exp(input clk, rst_n, v, input [31:0] x, output [31:0] y, output vo, fault);
  ot_s81_svc_exp_cs #(.LM(5), .LA(4)) u(.clk(clk),.rst_n({17{rst_n}}),.v(v),.x(x),.y(y),.vo(vo),.fault(fault));
endmodule
module g_fdiv(input clk, rst_n, v, input [31:0] a, b, output [31:0] y, output vo, fault);
  ot_dsrom_su_fdiv_f12 #(.NR(0)) u(.*);
endmodule
module c_fdiv(input clk, rst_n, v, input [31:0] a, b, output [31:0] y, output vo, fault);
  ot_s81_svc_fdiv_f12_cs #(.NR(0)) u(.*);
endmodule
V
cat > $T/eq.ys <<Y
read_verilog -sv -DSYNTHESIS $LIB $T/w.sv
prep -flatten -top g_$U; memory_map; opt_clean; rename g_$U gold; design -stash g
read_verilog -sv -DSYNTHESIS $LIB $T/w.sv
prep -flatten -top c_$U; memory_map; opt_clean; rename c_$U gate; design -stash c
design -copy-from g -as gold gold; design -copy-from c -as gate gate
async2sync
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 8
equiv_induct -seq 8
equiv_status -assert
Y
if yosys -q -l $T/eq.log $T/eq.ys > /dev/null 2>&1; then echo "EQ $U MUT=$MUT: PASS ($(grep -o 'Found [0-9]* \$equiv cells' $T/eq.log | tail -1))"; exit 0
elif grep -q "ERROR: Found [0-9]* unproven" $T/eq.log; then echo "EQ $U MUT=$MUT: FAIL ($(grep "ERROR: Found [0-9]* unproven" $T/eq.log | head -1))"; exit 1
else echo "EQ $U MUT=$MUT: ABORT (no equiv_status verdict: $(tail -n 1 $T/eq.log | cut -c1-120))"; exit 2; fi
