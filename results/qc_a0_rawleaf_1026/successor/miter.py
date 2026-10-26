#!/usr/bin/env python3
"""Smallest sequential lockstep for the actual adder-cell expansion, with mutant."""
import importlib.util
from pathlib import Path
import sys

p=Path(__file__).with_name('generate.py')
s=importlib.util.spec_from_file_location('gen',p)
g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
out=Path(sys.argv[1]);out.mkdir(exist_ok=True)
old='''module cells(input a,b,c,output [3:0] q);
HAxp5_ASAP7_75t_R h (.A(a),.B(b),.CON(q[0]),.SN(q[1]));
FAx1_ASAP7_75t_R f (.A(a),.B(b),.CI(c),.CON(q[2]),.SN(q[3]));
endmodule
'''
new,_=g.expand(old.replace('module cells','module expanded'))
mut=new.replace('module expanded','module mutant').replace('assign q[3] = ~((a) ^ (b) ^ (c));','assign q[3] = ((a) ^ (b) ^ (c));')
assert mut!=new.replace('module expanded','module mutant')
for tag,body,mod in [('exact',new,'expanded'),('mutant',mut,'mutant')]:
    text=old+body+f'''module miter(input clk,a,b,c,output bad);
wire [3:0] x,y;
reg [3:0] rx,ry;
cells r(a,b,c,x);
{mod} t(a,b,c,y);
always @(posedge clk) begin rx<=x;ry<=y;end
assign bad=|(rx^ry);
endmodule
'''
    (out/(tag+'.v')).write_text(text)
