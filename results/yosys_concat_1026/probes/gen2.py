import itertools
# casts of different relative widths; x4 = 4-bit, x2 = 2-bit, x1 = 1-bit
casts = {'trunc':"2'(x4)", 'same':"2'(x2)", 'ext':"2'(x1)", 'none':"x2",
         'cc_trunc':"{1'(x4),1'(x4)}", 'cc_same':"{1'(x1),1'(x1)}", 'cc_plain':"{x1,x1}",
         'trunc_expr':"2'(x4+x4)", 'int_trunc':"2'(x4/2)", 'slice':"x4[1:0]"}
ops = {'xor':"({C} ^ w)", 'and':"({C} & w)", 'add':"({C} + w)", 'bare':"({C})", 'not':"(~{C})", 'tern':"(c ? {C} : w)", 'xorlit':"({C} ^ 2'd1)"}
outer = {'k3':("{3'b010, %s}",5), 'k3sig':("{x4[2:0], %s}",5), 'kafter':("{%s, 3'b101}",5)}
L=[]
for (cn,ce),(on,oe),(un,(ue,wd)),par in itertools.product(casts.items(),ops.items(),outer.items(),[0,1]):
    n=f"{cn}__{on}__{un}__p{par}"
    e=ue % oe.replace("{C}",ce)
    ph = "#(parameter integer P1=1)" if par else ""
    open(f"p2/m_{n}.sv","w").write(f"module m_{n} {ph}(input wire [3:0] x4, input wire [1:0] x2, w, input wire x1, c, output wire [{wd-1}:0] y);\n  assign y = {e};\nendmodule\n")
