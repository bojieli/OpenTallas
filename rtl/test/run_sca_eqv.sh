#!/bin/bash
# el1011-q-seq (2026-10-11): formal check of the spctl SC (a) pre-scale compare (ot_qwen_me_spctl_w12, BANDF, W 16 / IL 8 /
# NW 18 as ctlm_i's u_tt) against the original expression, all inputs (yosys SAT):
#   stage 1: d = mmode ? nout - lb : nout - nb  (kept KS, DW = NW + 3 bits, signed)
#   stage 2: d > c, c = pgi * (mmode ? W : W * IL)  <=>  sign of d + ~c (CWD bits) clear
#   original: mmode ? (lb + pgi*W < nout) : (nb + pgi*(W*IL) < nout)   (32-b unsigned context; pgi = {16'd0, g16} under BANDF)
# The two stages are composed combinationally (the RTL registers d and the fields together, so the composition is the
# per-edge function).  usage: run_sca_eqv.sh <outdir> <mode: 0 exact | 1 mutant (>= for >, SC bit 2)>
set -e
O=$1; M=$2; mkdir -p "$O"
cat > "$O/sca_chk_$M.v" <<V
module chk(input [18:0] nb, input [18:0] lb, input [18:0] nout, input mmode, input [15:0] g16, output ok);
    localparam integer W = 16, IL = 8, NW = 18, LW = 4;
    localparam integer DW = NW + 3;
    localparam integer CWD = ((DW > LW + 3 + 16) ? DW : LW + 3 + 16) + 2;
    wire [31:0] pgi = {16'd0, g16};
    wire orig = mmode ? (lb + pgi*W < nout) : (nb + pgi*(W*IL) < nout);
    wire [DW-1:0] dn, dl; wire cn, cl;
    ot_hdc_ksadd_k #(.W(DW)) u_dn (.a({2'b00, nout}), .b(~{2'b00, nb}), .cin(1'b1), .s(dn), .cout(cn));
    ot_hdc_ksadd_k #(.W(DW)) u_dl (.a({2'b00, nout}), .b(~{2'b00, lb}), .cin(1'b1), .s(dl), .cout(cl));
    wire [DW-1:0] d = mmode ? dl : dn;
    wire [CWD-1:0] c = {{(CWD-16){1'b0}}, pgi[15:0]} << (mmode ? LW : LW + 3);
    wire [CWD-1:0] gs; wire gco;
    ot_hdc_ksadd_k #(.W(CWD)) u_g (.a({{(CWD-DW){d[DW-1]}}, d}), .b(~c), .cin(1'b$M), .s(gs), .cout(gco));
    assign ok = (!gs[CWD-1]) == orig;
endmodule
V
Y=${YOSYS:-yosys}
if "$Y" -q -p "read_verilog -sv rtl/hdc/ot_hdc_prefix.sv $O/sca_chk_$M.v; prep -top chk; flatten; sat -prove ok 1 -verify" > "$O/sca_eqv_$M.log" 2>&1; then
    echo "PASS sca_eqv mode=$M (SC pre-scale compare == original for all nb / lb / nout / mmode / pgi)"
else
    echo "FAIL sca_eqv mode=$M"; exit 1
fi
