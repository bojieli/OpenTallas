# one landing per sink phase: A (src, phase 0) -> ot_dp_st(A) -> landing(fclk=A, clk=B, WNEG) -> ot_dp_st(B); latency in cycle index
import sys
ph=[x/10 for x in range(-48,49,4)]+[-0.1,0.1,0.0]
W=32
v=['`timescale 1ns/1ps','module tb;','reg rst_n=0; reg ca=0; integer cyca=0;',
   'initial begin #5; forever begin ca=1; cyca=cyca+1; #5; ca=0; #5; end end','initial #95 rst_n=1;',
   f'reg [{W-1}:0] src; reg sea; reg [{W-1}:0] h[0:4095]; initial begin src=0; sea=0; end',
   'always @(negedge ca) begin src=$urandom; sea=rst_n; h[cyca%4096]=src; end',
   f'wire [{W-1}:0] a1; wire a1e; ot_dp_st #(.W({W})) ua (.clk(ca),.rst_n(rst_n),.d(src),.ea(sea),.q(a1),.eq(a1e));']
for k,p in enumerate(ph):
    v+=[f'reg cb{k}=0; integer cy{k}=0; initial begin #({5+p:.3f}); forever begin cb{k}=1; cy{k}=cy{k}+1; #5; cb{k}=0; #5; end end',
        f'wire [{W-1}:0] q{k}, o{k}; wire qe{k}, oe{k}, r{k}, f{k};',
        f'ot_dp_clk_landing #(.W({W+1}),.WNEG(1)) ul{k} (.fclk(ca),.clk(cb{k}),.rst_n(rst_n),.d({{a1e,a1}}),.q({{qe{k},q{k}}}),.ready(r{k}),.fault(f{k}));',
        f'ot_dp_st #(.W({W})) ub{k} (.clk(cb{k}),.rst_n(rst_n),.d(q{k}),.ea(qe{k}),.q(o{k}),.eq(oe{k}));',
        f'integer n{k}, g{k}, lat{k}=-9, bad{k}=0;',
        f'always @(posedge cb{k}) begin #0.05; if (cy{k}>300 && cy{k}<1300) begin g{k}=-1; for (n{k}=0;n{k}<50;n{k}=n{k}+1) if (g{k}<0 && o{k}===h[(cy{k}-n{k})%4096]) g{k}=n{k}; if (!oe{k}||f{k}) bad{k}=bad{k}+1; if (lat{k}==-9) lat{k}=g{k}; else if (lat{k}!=g{k}) bad{k}=bad{k}+1; end end']
v.append('initial begin #14000;')
for k,p in enumerate(ph): v.append(f'$display("PH {p:+.2f} lat %0d bad %0d fault %b", lat{k}, bad{k}, f{k});')
v+=['$finish; end','endmodule']
open(sys.argv[1],'w').write('\n'.join(v)+'\n')
