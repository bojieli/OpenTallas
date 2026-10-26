F = {
 'red_alone': (1, "|2'(x4)"),
 'red_alone_xor': (1, "^2'(x4)"),
 'red_wide': (3, "|2'(x4)"),
 'red_xor_in_expr': (2, "(|2'(x4)) ^ w[0]"),
 'pconst_tern': (5, "{3'b010, (w ^ 2'(P2!=0?1:0))}"),
 'pconst_mul': (5, "{3'b010, (w ^ 2'(P2*3))}"),
 'pconst_lit': (5, "{3'b010, (w ^ 2'(5))}"),
 'pconst_cc': (5, "{3'b010, ({1'(P2/2),1'(P2%2)} ^ w)}"),
 'sig_ext_in_cc': (5, "{3'b010, ({1'(x1),1'(c)} ^ w)}"),
 'red_cc': (4, "{3'b010, (|{1'(x4),1'(x4)})}"),
 'arg_idx': (4, "{3'b010, x4[2'(x4)]}"),
 'shift_amt': (5, "{3'b010, (w << 1'(x4))}"),
 'cmp_xor': (4, "{3'b010, ((2'(x4)==w) ^ c)}"),
 'typecast': (5, "{3'b010, (t2_t'(x4) ^ w)}"),
 'bitsel_cast_paren': (5, "{3'b010, (x4[3:2] ^ 2'(x4))}"),
 'xor_both_trunc': (5, "{3'b010, (2'(x4) ^ 2'(x4>>2))}"),
 'unsized_rhs_tern': (5, "{3'b010, (c ? 2'(x4) : 2'd1)}"),
}
for n,(wd,e) in F.items():
    open(f"p4/m_{n}.sv","w").write(f"module m_{n} #(parameter integer P2=2)(input wire [3:0] x4, input wire [1:0] x2, w, input wire x1, c, output wire [{wd-1}:0] y);\n  typedef logic [1:0] t2_t;\n  assign y = {e};\nendmodule\n")
