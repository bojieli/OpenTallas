F = {
 'bin_or': (2, "x2 | 2'(x4)"),
 'bin_add': (2, "x2 + 2'(x4)"),
 'bin_xor_wide': (4, "x2 ^ 2'(x4)"),
 'un_minus': (2, "- 2'(x4)"),
 'un_plus': (2, "+2'(x4)"),
 'red_space': (1, "| 2'(x4)"),
 'red_param': (1, "|P2'(x4)"),
 'red_ext_space': (1, "| 3'(x2)"),
 'not_in_paren': (2, "~(2'(x4))"),
 'mul_cast': (4, "x2 * 2'(x4)"),
 'lt_cast': (1, "x2 < 2'(x4)"),
 'cc_bin_after': (5, "{3'b010, (2'(x4) ^ w)}"),
 'trunc_xor_wide_noconcat': (4, "2'(x4) ^ w"),
}
for n,(wd,e) in F.items():
    open(f"p6/m_{n}.sv","w").write(f"module m_{n} #(parameter integer P2=2)(input wire [3:0] x4, input wire [1:0] x2, w, input wire x1, c, output wire [{wd-1}:0] y);\n  assign y = {e};\nendmodule\n")
