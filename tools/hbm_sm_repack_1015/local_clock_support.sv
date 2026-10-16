// Wires-only transport parents: each child clock is delivered independently.
module ot_hbm_smh_rp4_ptw(input wire[4:0]clk_hard,input wire rst_a,input wire[1635:0]rin,input wire[2068:0]bin,
 output wire[1635:0]rpm,output wire[2068:0]bm,output wire[817:0]rl1_n,rl1_s,
 output wire[2068:0]bk1_n,bk1_s,output wire[12:0]ohl1_n,ohl1_s);
 ot_smh_tr_group_row_w u_row0(.clk(clk_hard[0]),.rst_a(rst_a),.d(rin[817:0]),.first(rl1_n),.last(rpm[817:0]));
 ot_smh_tr_group_row_w u_row1(.clk(clk_hard[1]),.rst_a(rst_a),.d(rin[1635:818]),.first(rl1_s),.last(rpm[1635:818]));
 ot_smh_tr_group_beat_e u_beat_t(.clk(clk_hard[2]),.rst_a(rst_a),.d(bin),.last(bm));
 ot_smh_tr_group_land u_land_n(.clk(clk_hard[3]),.rst_a(rst_a),.d(bin),.q(bk1_n));
 ot_smh_tr_group_land u_land_s(.clk(clk_hard[4]),.rst_a(rst_a),.d(bin),.q(bk1_s));
 assign ohl1_n=bk1_n[2048+:13];assign ohl1_s=bk1_s[2048+:13];
endmodule
module ot_hbm_smh_rp4_pte(input wire[2:0]clk_hard,input wire rst_a,input wire[1635:0]rpm,input wire[2068:0]bm,
 output wire[1635:0]rout,output wire[2068:0]bout);
 ot_smh_tr_group_row_e u_row0(.clk(clk_hard[0]),.rst_a(rst_a),.d(rpm[817:0]),.last(rout[817:0]));
 ot_smh_tr_group_row_e u_row1(.clk(clk_hard[1]),.rst_a(rst_a),.d(rpm[1635:818]),.last(rout[1635:818]));
 ot_smh_tr_group_beat_e u_beat(.clk(clk_hard[2]),.rst_a(rst_a),.d(bm),.last(bout));
endmodule
module ot_hbm_smh_rp4_rst(input wire[2:0]clk_region,input wire rst_n,
 output wire gn,lhn,gm,ptw,pte,gs,lhs);
 (*keep*)reg p0,n1,n2,n3,t1,t2,m2,m3,s3,f_gn,f_lhn,f_gm,f_ptw,f_pte,f_gs,f_lhs;
 always @(posedge clk_region[0])begin p0<=rst_n;n1<=p0;n2<=n1;n3<=n2;t1<=p0;f_gn<=n3;f_lhn<=n3;end
 always @(posedge clk_region[1])begin t2<=t1;m2<=t1;m3<=m2;f_gm<=m3;f_ptw<=m3;f_pte<=m3;end
 always @(posedge clk_region[2])begin s3<=t2;f_gs<=s3;f_lhs<=s3;end
 assign gn=f_gn;assign lhn=f_lhn;assign gm=f_gm;assign ptw=f_ptw;assign pte=f_pte;assign gs=f_gs;assign lhs=f_lhs;
endmodule
module ot_hbm_smh_rp4_strap #(parameter integer NORTH=0)(input wire[2:0]clk_region,input wire[25:0]d,output wire[25:0]q);
 (*keep*)reg[25:0]s0,s1,s2,s3,s4;
 always @(posedge clk_region[0])begin s0<=d;s1<=s0;end
 wire cm=NORTH?clk_region[0]:clk_region[1],cs=NORTH?clk_region[0]:clk_region[2];
 always @(posedge cm)s2<=s1;
 always @(posedge cs)begin s3<=s2;s4<=s3;end
 assign q=s4;
endmodule
// The physical parent has eighteen direct hard-child clock entries and ten
// localized standard-cell entries. The die supplies each entry at phi-R.
// No clock tree or clock gate is hidden on a direct hard-child entry.
module ot_hbm_smh_rp4_entries(input wire[17:0]clk_hard,input wire[2:0]clk_pin,
 input wire[3:0]clk_oper,input wire[2:0]clk_region,input wire rst_n,
 input wire[17:0]xs_a1,input wire[9:0]xs_g1,input wire[13:0]xs_a2,input wire[9:0]xs_g2,
 input wire[1635:0]rin,input wire[2068:0]bin,output wire[1635:0]rout,output wire[2068:0]bout,
 input wire[99:0]gin,output wire[199:0]gout);
 wire[17:0]sx_a1;wire[9:0]sx_g1,sx_g2;wire[13:0]sx_a2;
 for(genvar j=0;j<2;j=j+1)begin:g_strap
  wire[25:0]q;
  ot_hbm_smh_rp4_strap #(.NORTH(j==0))u_sr(.clk_region(clk_region),
   .d({xs_g2[j*5+:5],xs_a2[j*7+:7],xs_g1[j*5+:5],xs_a1[j*9+:9]}),.q(q));
  assign{sx_g2[j*5+:5],sx_a2[j*7+:7],sx_g1[j*5+:5],sx_a1[j*9+:9]}=q;
 end
 ot_hbm_smh_rp4_core u(.clk_hard(clk_hard),.clk_pin(clk_pin),.clk_oper(clk_oper),.clk_region(clk_region),.rst_n(rst_n),
  .xs_a1(sx_a1),.xs_g1(sx_g1),.xs_a2(sx_a2),.xs_g2(sx_g2),.rin(rin),.bin(bin),.rout(rout),.bout(bout),.gin(gin),.gout(gout));
endmodule
// Actual die-level clock gating companion: one existing ot_cg_tile per root.
// Placement, raw root phases and gated trunk delivery remain die obligations.
module ot_hbm_smh_rp4_clock_dist(input wire[27:0]clk_raw,input wire rst_n,cgi,output wire cgo,output wire[27:0]gclk);
 wire cgi_h;ot_hdly #(.W(1),.N(2))u_hdly_cgi(.a(cgi),.y(cgi_h));
 wire[27:0]wake;
 for(genvar i=0;i<28;i=i+1)begin:g_root
  ot_cg_tile #(.HOLD(64),.ENREG(1),.RSTEN(0),.RAWRST(0))u_cgt(.clk(clk_raw[i]),.rst_n(rst_n),.cgi(cgi_h),.cgo(wake[i]),.gclk(gclk[i]));
 end
 assign cgo=wake[25];
endmodule
// Functional proof wrapper; the physical die uses the entries and distributor
// separately so each entry can receive its measured phi-R clock phase.
module ot_hbm_smh_rp4_gated #(parameter integer MUT_CLKDROP=0)(
 input wire clk,rst_n,cgi,output wire cgo,input wire[17:0]xs_a1,input wire[9:0]xs_g1,
 input wire[13:0]xs_a2,input wire[9:0]xs_g2,input wire[1635:0]rin,input wire[2068:0]bin,
 output wire[1635:0]rout,output wire[2068:0]bout,input wire[99:0]gin,output wire[199:0]gout);
 wire[27:0]gclk;
 ot_hbm_smh_rp4_clock_dist u_clk(.clk_raw({28{clk}}),.rst_n(rst_n),.cgi(cgi),.cgo(cgo),.gclk(gclk));
 wire[17:0]hc=(MUT_CLKDROP!=0)?(gclk[17:0]&~18'b1):gclk[17:0];
 ot_hbm_smh_rp4_entries u_tile(.clk_hard(hc),.clk_pin(gclk[20:18]),.clk_oper(gclk[24:21]),.clk_region(gclk[27:25]),.*);
endmodule
