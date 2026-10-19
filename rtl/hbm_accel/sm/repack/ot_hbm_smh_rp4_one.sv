// RP4f (owner 2026-10-16, neighbour-relative clocking): the rp4 tile runs from ONE regional root.
// Same body, same data edges and same hard children as ot_hbm_smh_rp4_entries; the 18 hard-child entries,
// 3 pin roots, 4 operand roots and 3 region roots (rp4e: 28 ports, -280 ps in-flow setup across
// clk_region[1]->[2] and -391 ps in rp4d across [0]->[1]) collapse into one port `clk`, so no path inside
// the tile crosses a root. Instance names are kept (g_strap[j].u_sr, u) so the hard-child placement is unchanged.
module ot_hbm_smh_rp4_one #(parameter integer MUT_CLKDROP=0)(input wire clk,input wire rst_n,
 input wire[8:0]xs_a1,input wire[4:0]xs_g1,input wire[6:0]xs_a2,input wire[4:0]xs_g2,
 input wire[8:0]xss_a1,input wire[4:0]xss_g1,input wire[6:0]xss_a2,input wire[4:0]xss_g2,
 input wire[1635:0]rin,input wire[2068:0]bin,output wire[1635:0]rout,output wire[2068:0]bout,
 input wire[99:0]gin,output wire[199:0]gout);
 // mutant (bench only): hard child 0 (leaf 0 x store) loses its clock
 wire[17:0]hc=(MUT_CLKDROP!=0)?{{17{clk}},1'b0}:{18{clk}};
 wire[2:0]cr={3{clk}};
 wire[17:0]sx_a1;wire[9:0]sx_g1,sx_g2;wire[13:0]sx_a2;
 wire[17:0]ia1={xss_a1,xs_a1};wire[9:0]ig1={xss_g1,xs_g1},ig2={xss_g2,xs_g2};wire[13:0]ia2={xss_a2,xs_a2};
 for(genvar j=0;j<2;j=j+1)begin:g_strap
  wire[25:0]q;
  ot_hbm_smh_rp4_strap #(.NORTH(j==0))u_sr(.clk_region(cr),
   .d({ig2[j*5+:5],ia2[j*7+:7],ig1[j*5+:5],ia1[j*9+:9]}),.q(q));
  assign{sx_g2[j*5+:5],sx_a2[j*7+:7],sx_g1[j*5+:5],sx_a1[j*9+:9]}=q;
 end
 ot_hbm_smh_rp4_core u(.clk_hard(hc),.clk_pin({3{clk}}),.clk_oper({4{clk}}),.clk_region(cr),.rst_n(rst_n),
  .xs_a1(sx_a1),.xs_g1(sx_g1),.xs_a2(sx_a2),.xs_g2(sx_g2),.rin(rin),.bin(bin),.rout(rout),.bout(bout),.gin(gin),.gout(gout));
endmodule
// Die-level clock-gating companion for the one-root tile: ONE existing ot_cg_tile.
module ot_hbm_smh_rp4_one_dist(input wire clk_raw,input wire rst_n,cgi,output wire cgo,output wire gclk);
 wire cgi_h;ot_hdly #(.W(1),.N(2))u_hdly_cgi(.a(cgi),.y(cgi_h));
 for(genvar i=0;i<1;i=i+1)begin:g_root
  ot_cg_tile #(.HOLD(64),.ENREG(1),.RSTEN(0),.RAWRST(0))u_cgt(.clk(clk_raw),.rst_n(rst_n),.cgi(cgi_h),.cgo(cgo),.gclk(gclk));
 end
endmodule
// Functional proof wrapper (same ports as ot_hbm_smh_rp4_gated).
module ot_hbm_smh_rp4_one_gated #(parameter integer MUT_CLKDROP=0)(
 input wire clk,rst_n,cgi,output wire cgo,input wire[17:0]xs_a1,input wire[9:0]xs_g1,
 input wire[13:0]xs_a2,input wire[9:0]xs_g2,input wire[1635:0]rin,input wire[2068:0]bin,
 output wire[1635:0]rout,output wire[2068:0]bout,input wire[99:0]gin,output wire[199:0]gout);
 wire gclk;
 ot_hbm_smh_rp4_one_dist u_clk(.clk_raw(clk),.rst_n(rst_n),.cgi(cgi),.cgo(cgo),.gclk(gclk));
 ot_hbm_smh_rp4_one #(.MUT_CLKDROP(MUT_CLKDROP)) u_tile(.clk(gclk),.rst_n(rst_n),
  .xs_a1(xs_a1[8:0]),.xs_g1(xs_g1[4:0]),.xs_a2(xs_a2[6:0]),.xs_g2(xs_g2[4:0]),
  .xss_a1(xs_a1[17:9]),.xss_g1(xs_g1[9:5]),.xss_a2(xs_a2[13:7]),.xss_g2(xs_g2[9:5]),
  .rin(rin),.bin(bin),.rout(rout),.bout(bout),.gin(gin),.gout(gout));
endmodule
