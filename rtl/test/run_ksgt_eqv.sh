#!/bin/bash
# el1011-q-seq (2026-10-11): formal check of the FKS / PK prefix-tree arithmetic (ot_hdc_ksadd_k) against behavioural
# operators, all inputs (yosys SAT): gt32  = cout(a + ~b + 0) == (a > b)        (ctlm_i FKS argmax-merge compare)
#                                    add18 = s(a + b + C)       == a + b         (ctlm_i FKS index add; C = 1 mutant)
#                                    sub16 = s(a + ~b + C)      == a - b         (spctl PK progress subtract; C = 0 mutant)
# usage: run_ksgt_eqv.sh <outdir> <C-mode: 0 exact | 1 mutant>   (exact must PASS, mutant must FAIL)
set -e
O=$1; M=$2; mkdir -p "$O"
cat > "$O/ksgt_chk_$M.v" <<V
module chk(input [31:0] a, input [31:0] b, input [17:0] c, input [17:0] d, input [15:0] e, input [15:0] f, output ok);
    wire [31:0] s1; wire gt; wire [17:0] s2; wire c2; wire [15:0] s3; wire c3;
    ot_hdc_ksadd_k #(.W(32)) u_gt (.a(a), .b(~b), .cin(1'b0), .s(s1), .cout(gt));
    ot_hdc_ksadd_k #(.W(18)) u_sm (.a(c), .b(d), .cin(1'b$M), .s(s2), .cout(c2));
    ot_hdc_ksadd_k #(.W(16)) u_sb (.a(e), .b(~f), .cin(1'b$((1 - M))), .s(s3), .cout(c3));
    assign ok = (gt == (a > b)) && (s2 == c + d) && (s3 == e - f);
endmodule
V
if yosys -q -p "read_verilog -sv rtl/hdc/ot_hdc_prefix.sv $O/ksgt_chk_$M.v; prep -top chk; flatten; sat -prove ok 1 -verify" > "$O/ksgt_eqv_$M.log" 2>&1; then
    echo "PASS ksgt_eqv mode=$M (gt32 / add18 / sub16 prefix trees == behavioural for all inputs)"
else
    echo "FAIL ksgt_eqv mode=$M"; exit 1
fi
