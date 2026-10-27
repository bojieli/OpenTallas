F = {
 'mid':      (8, "{3'b010, (2'(x4) ^ w), 3'b101}"),
 'nested':   (8, "{3'b011, {3'b010, (2'(x4) ^ w)}}"),
 'nested2':  (8, "{{3'b011, 3'b010}, (2'(x4) ^ w)}"),
 'repl':     (4, "{2{(2'(x4) ^ w)}}"),
 'repl2':    (7, "{3'b010, {2{(2'(x4) ^ w)}}}"),
 'two':      (7, "{3'b010, (2'(x4) ^ w), (2'(x4) & w)}"),
 'plusk':    (5, "(2'(x4) ^ w) + 5'd8"),
 'orK':      (5, "5'd8 | (2'(x4) ^ w)"),
 'sh':       (5, "(2'(x4) ^ w) << 3"),
 'cmp_in_cc':(4, "{3'b010, ((2'(x4) ^ w) == 2'd1)}"),
 'idx':      (5, "{3'b010, (2'(x4) ^ w)}"),
 'sub_bits': (5, "{3'b010, (x4[1:0] ^ w)}"),
 'sign_trunc':(5, "{3'b010, (2'($signed(x4)) ^ w)}"),
 'sz_param': (5, "{3'b010, (P2'(x4) ^ w)}"),
 'tern_cast_cond':(5, "{3'b010, (1'(x4) ? w : x2)}"),
 'cast_ext_of_trunc':(5, "{3'b010, (2'(1'(x4)) ^ w)}"),
 'eq_cast':  (4, "{3'b010, (2'(x4) == w)}"),
 'red':      (4, "{3'b010, (|2'(x4))}"),
 'lnot':     (4, "{3'b010, (!2'(x4))}"),
 'land':     (4, "{3'b010, (1'(x4) && c)}"),
 'lhs_concat':(5, None),
 'always':   (5, None),
 'func':     (5, None),
 'wide_lhs_noconcat': (8, "(2'(x4) ^ w)"),
}
for n,(wd,e) in F.items():
    if n=='lhs_concat': body="  wire [2:0] hi; assign {hi, y[1:0]} = {3'b010, (2'(x4) ^ w)}; assign y[4:2]=hi;"
    elif n=='always': body="  reg [4:0] r; always @* r = {3'b010, (2'(x4) ^ w)}; assign y=r;"
    elif n=='func': body="  function automatic [4:0] f(input [3:0] a, input [1:0] b); f = {3'b010, (2'(a) ^ b)}; endfunction\n  assign y = f(x4,w);"
    else: body=f"  assign y = {e};"
    open(f"p3/m_{n}.sv","w").write(f"module m_{n} #(parameter integer P2=2)(input wire [3:0] x4, input wire [1:0] x2, w, input wire x1, c, output wire [{wd-1}:0] y);\n{body}\nendmodule\n")
