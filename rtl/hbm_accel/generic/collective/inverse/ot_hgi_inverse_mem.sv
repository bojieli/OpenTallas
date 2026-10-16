`timescale 1ns/1ps
`default_nettype none
// Packed independent SECDED39 records. Macro pin, capture, selection and decoder
// boundaries are registered. Writes touch precisely one39-bit record.
module ot_hgi_inverse_mem #(parameter integer BANKS=3)(
 input wire clk,rst_n, input wire rv,input wire[11:0]ra,
 output wire ov,output wire[31:0]rd,output wire ue,ce,
 input wire wv,input wire[11:0]wa,input wire[31:0]wd,output wire wdone,output reg ctrl_fault);
 wire[38:0]enc; ot_secded_enc #(.K(32),.R(7))e(.clk(clk),.d(wd),.q(enc));
 reg[11:0]waddr,waddrbar; reg wvalid,wvalidbar;reg[2:0]wvpipe,wvpipebar;
 reg[6:0]wrow;reg[1:0]wbank;reg[255:0]wdata,wmask;reg wpin,wpinbar;reg[6:0]wrowbar,rrowbar;reg[1:0]wbankbar,rbankbar;reg[2:0]rslotbar;reg[255:0]wmaskbar;reg[3:0]vpbar;reg[1:0]rb1bar;reg[2:0]rs1bar,rs2bar;
 reg[6:0]rrow;reg[1:0]rbank,rb1;reg[2:0]rslot,rs1,rs2;
 reg[3:0]vp; wire[255:0]rdata[0:BANKS-1];reg[255:0]capture;reg[38:0]record;
 wire[31:0]nc,nu;
 wire wb=(wvpipebar!=~wvpipe)||(wvalidbar!=~wvalid)||(wvalid&&waddrbar!=~waddr)||(wpinbar!=~wpin)||
  (wpin&&(wrowbar!=~wrow||wbankbar!=~wbank||wmaskbar!=~wmask));
 wire rb=(vpbar!=~vp)||(vp[0]&&(rrowbar!=~rrow||rbankbar!=~rbank||rslotbar!=~rslot))||(vp[1]&&(rb1bar!=~rb1||rs1bar!=~rs1))||(vp[2]&&rs2bar!=~rs2);
 always @(posedge clk or negedge rst_n) if(!rst_n) begin
   wvalid<=0;wvalidbar<=1;wpin<=0;wpinbar<=1;wvpipe<=0;wvpipebar<=3'h7;vp<=0;vpbar<=4'hf;ctrl_fault<=0;
 end else begin
   if(wb||rb)ctrl_fault<=1;wvalid<=wv;wvalidbar<=~wv; wvpipe<={wvpipe[1:0],wv};wvpipebar<=~{wvpipe[1:0],wv}; waddr<=wa;waddrbar<=~wa;
   wpin<=wvalid&&!wb;wpinbar<=~(wvalid&&!wb);wrowbar<=~7'((waddr/6)%128);wbankbar<=~2'((waddr/6)/128);wrow<=(waddr/6)%128;wbank<=(waddr/6)/128;
   wdata<={{217{1'b0}},enc}<<((waddr%6)*39);
   wmaskbar<=~({{217{1'b0}},{39{1'b1}}}<<((waddr%6)*39));
   wmask<={{217{1'b0}},{39{1'b1}}}<<((waddr%6)*39);
   vp<={vp[2:0],rv};vpbar<=~{vp[2:0],rv};rrowbar<=~7'((ra/6)%128);rbankbar<=~2'((ra/6)/128);rslotbar<=~3'(ra%6);rrow<=(ra/6)%128;rbank<=(ra/6)/128;rslot<=ra%6;
   rb1<=rbank;rb1bar<=~rbank;rs1<=rslot;rs1bar<=~rslot;rs2<=rs1;rs2bar<=~rs1;
   capture<=rdata[rb1];record<=capture[rs2*39+:39];
 end
 assign wdone=wvpipe[2];
 genvar b;generate for(b=0;b<BANKS;b=b+1)begin:m
   ot_sram_1r1w_128x256_m1_r2c2 ram(.clk(clk),.r_ce_in(vp[0]&&!rb&&rbank==b),.r_addr_in(rrow),.rd_out(rdata[b]),
    .w_ce_in(wpin&&!wb&&wbank==b),.w_addr_in(wrow),.wd_in(wdata),.w_mask_in(wmask),
    .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end endgenerate
 ot_secded_dec #(.K(32),.R(7))d(.clk(clk),.rst_n(rst_n),.v(vp[3]),.w(record),.ov(ov),.d(rd),.ce(ce),.ue(ue),.n_ce(nc),.n_ue(nu));
endmodule
`default_nettype wire
