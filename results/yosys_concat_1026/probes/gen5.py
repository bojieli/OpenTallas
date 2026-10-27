F = {
 'red_paren': (1, "|(2'(x4))"),
 'red_and': (1, "&2'(x4)"),
 'red_xorop': (1, "|(w ^ 2'(x4))"),
 'red_nor': (1, "~|2'(x4)"),
 'red_tern': (1, "|(c ? 2'(x4) : w)"),
 'red_ext': (1, "|3'(x2)"),
 'cmp_wide': (1, "(2'(x4) == 2'd0)"),
 'eq_signed': (1, "($signed(2'(x4)) < 0)"),
 'port_arg': (5, None),
 'red_cast_cc': (1, "|2'({x4,x4})"),
}
for n,(wd,e) in F.items():
    body = f"  assign y = {e};" if e else "  sub u(.i({3'b010, w}), .j(2'(x4) ^ w), .o(y));"
    open(f"p5/m_{n}.sv","w").write(f"module m_{n} (input wire [3:0] x4, input wire [1:0] x2, w, input wire x1, c, output wire [{wd-1}:0] y);\n{body}\nendmodule\n" + ("module sub(input [4:0] i, input [3:0] j, output [4:0] o); assign o = i ^ {1'b0,j}; endmodule\n" if not e else ""))
