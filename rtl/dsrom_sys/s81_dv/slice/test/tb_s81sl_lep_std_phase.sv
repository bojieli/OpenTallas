`timescale 1ns/1ps
// Full-shape old-reference miter: reference outward inputs delayed exactly the priced +1 edge.
module tb_s81sl_lep_std_phase #(parameter integer HOST=1,SEED=29);
reg clk=0;always #0.5 clk=~clk;reg rst_n=0;reg [1103:0] ro=0,rod=0;reg [76:0] th=0,thd=0;reg [53:0] tk=0,tkd=0;
reg v0=0,v1=0,cr0=0,cr1=0;reg [552:0] d0=0,d1=0;reg [1103:0] rxframe;integer cycle=0,bad=0,checked=0,frames=0;integer seed;
always @(posedge clk) begin rod<=ro;thd<=th;tkd<=tk;end
wire [1103:0] c_ri;
wire [1103:0] r_ri;
wire [0:0] c_lo0_v;
wire [0:0] r_lo0_v;
wire [0:0] c_lo1_v;
wire [0:0] r_lo1_v;
wire [552:0] c_lo0_d;
wire [552:0] r_lo0_d;
wire [552:0] c_lo1_d;
wire [552:0] r_lo1_d;
wire [0:0] c_li0_r;
wire [0:0] r_li0_r;
wire [0:0] c_li1_r;
wire [0:0] r_li1_r;
wire [1:0] c_rxv;
wire [1:0] r_rxv;
wire [514:0] c_f_host;
wire [514:0] r_f_host;
wire [52:0] c_f_ks;
wire [52:0] r_f_ks;
wire [0:0] c_fault;
wire [0:0] r_fault;
ot_s81sl_lep_core #(.DT(512),.DR(8),.HOST_EN(HOST),.NATIVE32_STD(1),.RX_SRAM(1),.IN_PIPE(1),.TXRP(1)) c_dut (.clk(clk),.rst_n(rst_n),.lo0_r(cr0),.lo1_r(cr1),.li0_v(v0),.li1_v(v1),.li0_d(d0),.li1_d(d1),.sl_f(1'b0),.l0_f(3'd0),.l1_f(3'd0),.l0_st(2'b10),.l1_st(2'b10),.mu_c(34'd0),.mu_rt(),.ml_wv(),.ml_wd(),.ml_rv(1'b0),.ml_rd(1104'd0),.ml_f(1'b0),.lo2_v(),.lo3_v(),.lo2_r(1'b0),.lo3_r(1'b0),.lo2_d(),.lo3_d(),.li2_v(1'b0),.li3_v(1'b0),.li2_r(),.li3_r(),.li2_d(553'd0),.li3_d(553'd0),.rxvb(),.l2_f(3'd0),.l3_f(3'd0),.f_lf(),.ro(ro),.t_host(th),.t_kd(tk),.ri(c_ri),.lo0_v(c_lo0_v),.lo1_v(c_lo1_v),.lo0_d(c_lo0_d),.lo1_d(c_lo1_d),.li0_r(c_li0_r),.li1_r(c_li1_r),.rxv(c_rxv),.f_host(c_f_host),.f_ks(c_f_ks),.fault(c_fault));
ot_s81sl_lep_slice3_reference_core #(.DT(512),.DR(8),.HOST_EN(HOST),.TXRP(1),.RXSA(1)) r_dut (.clk(clk),.rst_n(rst_n),.lo0_r(cr0),.lo1_r(cr1),.li0_v(v0),.li1_v(v1),.li0_d(d0),.li1_d(d1),.sl_f(1'b0),.l0_f(3'd0),.l1_f(3'd0),.l0_st(2'b10),.l1_st(2'b10),.mu_c(34'd0),.mu_rt(),.ml_wv(),.ml_wd(),.ml_rv(1'b0),.ml_rd(1104'd0),.ml_f(1'b0),.lo2_v(),.lo3_v(),.lo2_r(1'b0),.lo3_r(1'b0),.lo2_d(),.lo3_d(),.li2_v(1'b0),.li3_v(1'b0),.li2_r(),.li3_r(),.li2_d(553'd0),.li3_d(553'd0),.rxvb(),.l2_f(3'd0),.l3_f(3'd0),.f_lf(),.ro(rod),.t_host(thd),.t_kd(tkd),.ri(r_ri),.lo0_v(r_lo0_v),.lo1_v(r_lo1_v),.lo0_d(r_lo0_d),.lo1_d(r_lo1_d),.li0_r(r_li0_r),.li1_r(r_li1_r),.rxv(r_rxv),.f_host(r_f_host),.f_ks(r_f_ks),.fault(r_fault));
function automatic [1103:0] beat(input integer unused);
 integer i;reg [1103:0] b;begin
 for(i=0;i<34;i=i+1)b[i*32+:32]=$urandom;b[1103:1088]=$urandom;b[0]=1;beat=b;end endfunction
initial begin
 seed=SEED;seed=$urandom(seed);
 for(cycle=0;cycle<1800;cycle=cycle+1)begin
  @(negedge clk);rst_n=(cycle>=8);ro=0;th=0;tk=0;v0=0;v1=0;
  if(cycle>80 && cycle<1400)begin
   if(cycle%3==0)ro=beat(0);
   if(HOST!=0)begin
    th[76:65]=12'((cycle/47)%4096);th[63:0]={$urandom,$urandom};th[64]=(cycle%53==2);
    tk[53]=(cycle%59==4);tk[52:0]={$urandom,$urandom};
   end
   if(cycle%5==0)begin rxframe=beat(0);d0={1'(frames%2),rxframe[551:0]};v0=1;end
   if(cycle%5==1)begin d1={1'(frames%2),rxframe[1103:552]};v1=1;frames=frames+1;end
  end
 end
 repeat(20)@(negedge clk);
 if(bad || checked<100)$fatal(1,"LEP_STD_PHASE_FAIL HOST=%0d bad=%0d checked=%0d",HOST,bad,checked);
 $display("LEP_STD_PHASE_PASS HOST=%0d checked=%0d DT512 DR8 priced_outward_edges1 RX_edges0",HOST,checked);$finish;
end
always @(posedge clk)begin
 cr0<=c_lo0_v;cr1<=c_lo1_v;
 #0.05;
 if(rst_n && cycle>40)begin
  checked=checked+1;
  if(c_lo0_v!==r_lo0_v || c_lo1_v!==r_lo1_v || c_ri[0]!==r_ri[0] ||
     c_li0_r!==r_li0_r || c_li1_r!==r_li1_r || c_rxv!==r_rxv || c_fault!==r_fault ||
     (c_lo0_v && c_lo0_d!==r_lo0_d) || (c_lo1_v && c_lo1_d!==r_lo1_d) ||
     (c_ri[0] && c_ri!==r_ri) || c_f_host[0]!==r_f_host[0] || c_f_ks[52]!==r_f_ks[52] ||
     (c_f_host[0] && c_f_host!==r_f_host) || (c_f_ks[52] && c_f_ks!==r_f_ks))begin
    bad=bad+1;if(bad<6)$display("LEP_STD_PHASE_MISMATCH cycle=%0d ri=%b/%b lo=%b%b/%b%b fault=%b/%b",cycle,c_ri[0],r_ri[0],c_lo0_v,c_lo1_v,r_lo0_v,r_lo1_v,c_fault,r_fault);
  end
 end
end
endmodule
