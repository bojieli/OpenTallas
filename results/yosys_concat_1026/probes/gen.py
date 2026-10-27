import sys
# name -> (output width, expression)
F = {
 'A_cc_xor_cast':      (5, "{3'b010, ({1'(a),1'(b)} ^ 2'(x))}"),
 'B_cc_xor_lit':       (5, "{3'b010, ({1'(a),1'(b)} ^ 2'd0)}"),
 'C_cc_xor_wire':      (5, "{3'b010, ({1'(a),1'(b)} ^ w)}"),
 'D_plaincc_xor_cast': (5, "{3'b010, ({a[0],b[0]} ^ 2'(x))}"),
 'E_wire_xor_cast':    (5, "{3'b010, (w ^ 2'(x))}"),
 'F_cc_only':          (5, "{3'b010, {1'(a),1'(b)}}"),
 'G_cc_not':           (5, "{3'b010, ~{1'(a),1'(b)}}"),
 'H_cc_and_wire':      (5, "{3'b010, ({1'(a),1'(b)} & w)}"),
 'H2_cc_add_wire':     (5, "{3'b010, ({1'(a),1'(b)} + w)}"),
 'I_cc1_xor_wire':     (4, "{3'b010, ({1'(a)} ^ w[0])}"),
 'J_cast_xor_wire':    (5, "{3'b010, (2'(a) ^ w)}"),
 'K_cc1cast2_xor':     (5, "{3'b010, ({2'(a)} ^ w)}"),
 'L_mixcc_xor':        (5, "{3'b010, ({w[0],1'(a)} ^ w2)}"),
 'M_cc_eq':            (4, "{3'b010, ({1'(a),1'(b)} == w)}"),
 'N_tern':             (5, "{3'b010, (c ? {1'(a),1'(b)} : w)}"),
 'P_noouter':          (2, "({1'(a),1'(b)} ^ w)"),
 'Q_const_after':      (8, "{3'b010, ({1'(a),1'(b)} ^ w), 3'b101}"),
 'R_sig_before':       (6, "{a, ({1'(a),1'(b)} ^ w)}"),
 'S_repl':             (5, "{3'b010, ({2{1'(a)}} ^ w)}"),
 'T_signed':           (5, "{3'b010, ({signed'(a[0:0]),b[0]} ^ w)}"),
 'U_paramcast':        (5, "{3'b010, ({P1'(a),P1'(b)} ^ w)}"),
 'V_ccc_xor_wire':     (5, "{3'b010, ({1'(a),{1'(b)}} ^ w)}"),
 'W_cc_or_cc':         (5, "{3'b010, ({1'(a),1'(b)} | {1'(b),1'(a)})}"),
 'X_cc_lsh':           (5, "{3'b010, ({1'(a),1'(b)} << 1)}"),
 'Y_repl_outer':       (5, "{{3{c}}, ({1'(a),1'(b)} ^ w)}"),
 'Z_cc_xor_paren2':    (5, "{3'b010, (({1'(a),1'(b)}) ^ w)}"),
 'AA_cc_widecast':     (7, "{3'b010, ({2'(a),2'(b)} ^ w4)}"),
 'AB_cc_xor_inner_k':  (5, "{3'b010, ({1'b1,1'(b)} ^ w)}"),
 'AC_slice_of_cast':   (5, "{3'b010, ({a[1:1],1'(b)} ^ w)}"),
 'AD_cc_mul':          (5, "{3'b010, ({1'(a),1'(b)} * w)}"),
 'AE_cc_minus':        (5, "{3'b010, (-{1'(a),1'(b)})}"),
 'AF_redxor':          (4, "{3'b010, (^{1'(a),1'(b)})}"),
 'AG_cc_xor_const_k':  (5, "{3'b010, ({1'(a),1'(b)} ^ 2'b01)}"),
 'AH_expr_cast_cc':    (5, "{3'b010, ({1'(a+b),1'(a&b)} ^ w)}"),
 'AI_sz_cast_of_cc':   (5, "{3'b010, (2'({1'(a),1'(b)}) ^ w)}"),
 'AJ_cc_xor_assign_wide': (5, "({1'(a),1'(b)} ^ w)"),
}
def mod(n,wd,e):
    return f"""module m_{n} #(parameter integer P1=1)(input wire [3:0] a, b, x, input wire [1:0] w, w2, input wire [3:0] w4, input wire c, output wire [{wd-1}:0] y);
  assign y = {e};
endmodule
"""
for n,(wd,e) in F.items():
    open(f"m_{n}.sv","w").write(mod(n,wd,e))
open("list.txt","w").write("\n".join(F)+"\n")
