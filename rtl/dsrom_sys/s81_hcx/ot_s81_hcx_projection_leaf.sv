`timescale 1ns/1ps
`default_nettype none
// One real resident-ROM projection row, replicated six times per TP4 die.
// Arithmetic is the SAME ot_hdc_v41x_hcp used inside exact ot_hgi_hc_unit.
// No numerical rewrite: canonical chunk8 products/tree, RMS scaling, eps.
// All ROM, local x SRAM, arithmetic and status flops belong to this leaf.
// Serial 0.9-GHz domain; stage bus is compiler-reserved, 80 consecutive beats
// of eight native packed-BF16 rows (4096b/beat). Commands follow SRAM visibility.
// Native static calendar must reserve the full prefetch; no credit/ready gating.
module ot_s81_hcx_projection_leaf #(parameter string IMAGE="hcx_r0",parameter integer MUT_BANK=0)(
 input wire clk,rst_n,
 input wire stage_begin,stage_v,
 input wire [6:0] stage_word,
 input wire [4095:0] stage_d,
 input wire cmd_v,cmd_ffn,
 input wire [31:0] norm_eps,
 output reg o_v,
 output reg [31:0] o_d,
 output reg fault
);
 wire [7:0] wr,xr;wire[127:0]wa,xa;
 wire[8191:0]wd1;reg[8191:0]wd2;
 wire[4095:0]xd1;reg[4095:0]xd2;
 reg[6:0]staged;
 wire ready,hfault,last,idle;
 reg stage_v_q,cmd_v_q;
 reg [6:0]stage_word_q;
 reg [4095:0]stage_d_q;
 reg cmd_ffn_q;
 reg [31:0]norm_eps_q;
 wire hv;wire[31:0]hd;
 wire[0:0]pos;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin stage_v_q<=0;cmd_v_q<=0;o_v<=0;end
  else begin stage_v_q<=stage_v;cmd_v_q<=cmd_v;o_v<=hv;end
 always @(posedge clk)begin
  stage_word_q<=stage_word;stage_d_q<=stage_d;cmd_ffn_q<=cmd_ffn;norm_eps_q<=norm_eps;o_d<=hd;
 end
 genvar b,m;
 generate for(b=0;b<8;b=b+1)begin:g_bank
  for(m=0;m<16;m=m+1)begin:g_rom
   wire[71:0]q;
   // Each macro carries two FP32 lanes, 64 payload bits, no ROM ECC.
   // Address 0..79 attn,128..207 ffn; each image is a released fn row.
`ifndef SYNTHESIS
   ot_rom_4096x72_m8 #(.INSTANCE($sformatf("%s_b%0d_l%0d",IMAGE,b,m)))rom(
`else
   ot_rom_4096x72_m8 rom(
`endif
    .clk(clk),.ce_in(wr[b]),.addr_in(wa[16*b+:12]),.rd_out(q));
   assign wd1[b*1024+m*64+:64]=(MUT_BANK && b==7) ? 64'd0 : q[63:0];
  end
  for(m=0;m<2;m=m+1)begin:g_x
   wire[255:0]d,q;
   for(genvar l=0;l<16;l=l+1)begin:g_scatter
    assign d[16*l+:16]=stage_d_q[16*(8*(16*m+l)+b)+:16];
   end
   ot_sram_1r1w_128x256_m1_r2c2 ram(
    .clk(clk),.r_ce_in(xr[b]),.r_addr_in(xa[16*b+:7]),.rd_out(q),
    .w_ce_in(stage_v_q),.w_addr_in(stage_word_q),.wd_in(d),.w_mask_in({256{1'b1}}),
    .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
   assign xd1[b*512+m*256+:256]=q;
  end
 end endgenerate
 always @(posedge clk)begin wd2<=wd1;xd2<=xd1;end
 ot_hdc_v41x_hcp #(.W(32),.TL(7),.PMAX(2),.OMAX(2),.AW(16),.CW(16),.ML(2))hcp(
  .clk(clk),.rst_n(rst_n),.cmd_valid(cmd_v_q),.cmd_ready(ready),.cmd_npos(2'd1),.cmd_nout(2'd1),
  .cmd_nchunk(16'd2560),.cmd_scale(1'b1),.cmd_nf(32'h46a00000),.cmd_eps(norm_eps_q),
  .cmd_wbase(cmd_ffn_q ? 16'd128 : 16'd0),.cmd_xbase(16'd0),
  .w_re(wr),.w_addr(wa),.w_data(wd2),.x_re(xr),.x_addr(xa),.x_data(xd2),
  .o_valid(hv),.o_ready(1'b1),.o_pos(pos),.o_idx(),.o_data(hd),.o_last(last),.fault(hfault),.idle(idle),
  .sd_v(),.sd_ss(),.sd_nv(),.sd_wa(),.sd_xa(),.sys_sum(1024'd0),.sys_fault(1'b0));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin staged<=0;fault<=0;end
  else begin
   if(stage_begin)begin if(!idle)fault<=1;staged<=0;end
   if(stage_v_q)begin
    if(stage_word_q!=staged || staged>=80 || !idle)fault<=1;
    staged<=staged+1'b1;
   end
   // Availability is a check; it never moves the command's compiled cycle.
   if(cmd_v_q && (!ready || staged!=80))fault<=1;
   if(hfault)fault<=1;
  end
 end
endmodule
`default_nettype wire
