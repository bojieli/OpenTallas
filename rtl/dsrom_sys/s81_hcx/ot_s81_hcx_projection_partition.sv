`timescale 1ns/1ps
`default_nettype none
// One real resident-ROM projection row, replicated six times per TP4 die.
// Arithmetic is the SAME ot_hdc_v41x_hcp used inside exact ot_hgi_hc_unit.
// No numerical rewrite: canonical chunk8 products/tree, RMS scaling, eps.
// All ROM, local x SRAM, arithmetic and status flops belong to this leaf.
// Serial 0.9-GHz domain; stage bus is compiler-reserved, 80 consecutive beats
// of eight native packed-BF16 rows (4096b/beat). Commands follow SRAM visibility.
// Native static calendar must reserve the full prefetch; no credit/ready gating.
module ot_s81_hcx_projection_partition #(parameter IMAGE="hcx_r0",parameter integer MUT_BANK=0,MUT_PAGE=0)(
 input wire clk,rst_n,
 input wire [31:0] clk_lane,
 input wire [4:0] clk_tree,
 input wire [7:0] clk_bank,
 input wire stage_begin,stage_v,
 input wire [6:0] stage_word,
 input wire [4095:0] stage_d,
 input wire cmd_v,cmd_ffn,
 input wire [5:0] cmd_layer,
 input wire [31:0] norm_eps,
 output wire o_v,
 output wire [31:0] o_d,
 output wire fault
);
 wire [7:0] wr,xr,lane_gov,lane_first,lane_done;
 wire [127:0] wa,xa;
 wire [8191:0] wd2,sums;
 wire [4095:0] xd2;
 wire [87:0] lane_meta;
 wire [31:0] lane_faults;
 wire [4:0] tree_faults;
 wire [127:0] quarter_sum;
 wire [3:0] quarter_vo;
 wire [31:0] final_sum;
 wire final_vo;
 // The parent is pure wiring. Every state bit lives in an actual hard child.
 ot_s81_hcx_projection_control control(
  .clk(clk),.rst_n(rst_n),.stage_begin(stage_begin),.stage_v(stage_v),.stage_word(stage_word),
  .cmd_v(cmd_v),.cmd_ffn(cmd_ffn),.cmd_layer(cmd_layer),.norm_eps(norm_eps),
  .o_v(o_v),.o_d(o_d),.fault(fault),.wr(wr),.xr(xr),.wa(wa),.xa(xa),
  .lane_meta(lane_meta),.lane_gov(lane_gov),.lane_first(lane_first),.lane_done(lane_done),
  .lane_faults(lane_faults),.tree_faults(tree_faults),.final_sum(final_sum),.final_vo(final_vo));
 generate for(genvar b=0;b<8;b=b+1)begin:g_bank
  wire[511:0] bank_stage;
  for(genvar l=0;l<32;l=l+1)begin:g_scatter
   assign bank_stage[l*16+:16]=stage_d[16*(8*l+b)+:16];
  end
  ot_s81_hcx_hcp_bank #(.IMAGE(IMAGE),.BANK(b),.MUT_BANK(MUT_BANK),.MUT_PAGE(MUT_PAGE))child(
   .clk(clk_bank[b]),.rst_n(rst_n),.stage_d(bank_stage),.stage_v(stage_v),.stage_word(stage_word),
   .wr(wr[b]),.wa(wa[b*16+:16]),.xr(xr[b]),.xa(xa[b*16+:16]),
   .wd(wd2[b*1024+:1024]),.xd(xd2[b*512+:512]));
 end endgenerate

 generate for(genvar g=0;g<8;g=g+1)begin:g_group
  for(genvar q=0;q<4;q=q+1)begin:g_lane8
   wire [2047:0] bank_w;
   wire [1023:0] bank_x;
   for(genvar bk=0;bk<8;bk=bk+1)begin:g_bank_slice
    assign bank_w[bk*256+:256]=wd2[bk*1024+q*256+:256];
    assign bank_x[bk*128+:128]=xd2[bk*512+q*128+:128];
   end
   ot_s81_hcx_hcp_lane8 child(
    .clk(clk_lane[g*4+q]),.rst_n(rst_n),.cfg_group(3'(g)),.cfg_base(6'(q*8)),.meta(lane_meta),.bank_w(bank_w),.bank_x(bank_x),
    .gov(lane_gov[g]),.first(lane_first[g]),.sum(sums[g*1024+q*256+:256]),.fault_q(lane_faults[g*4+q]));
  end
 end endgenerate
 generate for(genvar q=0;q<4;q=q+1)begin:g_quarter_tree
  wire [2047:0] partials;
  for(genvar g=0;g<8;g=g+1)begin:g_partial
   assign partials[g*256+:256]=sums[g*1024+q*256+:256];
  end
  ot_s81_hcx_hcp_quarter_tree child(.clk(clk_tree[q]),.rst_n(rst_n),.partials(partials),.done(lane_done),
   .y(quarter_sum[q*32+:32]),.vo(quarter_vo[q]),.fault(tree_faults[q]));
 end endgenerate
 ot_s81_hcx_hcp_final_tree final_tree(.clk(clk_tree[4]),.rst_n(rst_n),.x(quarter_sum),.v(quarter_vo),
  .y(final_sum),.vo(final_vo),.fault(tree_faults[4]));
endmodule

module ot_s81_hcx_projection_control(
 input wire clk,rst_n,stage_begin,stage_v,
 input wire [6:0] stage_word,
 input wire cmd_v,cmd_ffn,
 input wire [5:0] cmd_layer,
 input wire [31:0] norm_eps,
 input wire [31:0] lane_faults,
 input wire [4:0] tree_faults,
 input wire [31:0] final_sum,
 input wire final_vo,
 output reg o_v,output reg [31:0] o_d,output reg fault,
 output wire [7:0] wr,xr,lane_gov,lane_first,lane_done,
 output wire [127:0] wa,xa,
 output wire [87:0] lane_meta
);
 reg[6:0]staged;
 wire ready,hfault,last,idle;
 reg stage_v_q,cmd_v_q,stage_begin_q;
 reg [6:0]stage_word_q;
 reg cmd_ffn_q;
 reg [5:0]cmd_layer_q;
 reg [31:0]norm_eps_q;
 wire hv;wire[31:0]hd;
 wire[0:0]pos;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin stage_v_q<=0;cmd_v_q<=0;o_v<=0;stage_begin_q<=0;end
  else begin stage_v_q<=stage_v;cmd_v_q<=cmd_v;o_v<=hv;stage_begin_q<=stage_begin;end
 always @(posedge clk)begin
  stage_word_q<=stage_word;cmd_ffn_q<=cmd_ffn;cmd_layer_q<=cmd_layer;norm_eps_q<=norm_eps;o_d<=hd;
 end
 ot_s81_hcx_hcp_control #(.W(32),.TL(7),.PMAX(2),.OMAX(2),.AW(16),.CW(16),.ML(3))hcp(
  .clk(clk),.rst_n(rst_n),.cmd_valid(cmd_v_q),.cmd_ready(ready),.cmd_npos(2'd1),.cmd_nout(2'd1),
  .cmd_nchunk(16'd2560),.cmd_scale(1'b1),.cmd_nf(32'h46a00000),.cmd_eps(norm_eps_q),
  .cmd_wbase(16'((2*cmd_layer_q+cmd_ffn_q)*80)),.cmd_xbase(16'd0),
  .w_re(wr),.w_addr(wa),.x_re(xr),.x_addr(xa),
  .o_valid(hv),.o_ready(1'b1),.o_pos(pos),.o_idx(),.o_data(hd),.o_last(last),.fault(hfault),.idle(idle),
  .sd_v(),.sd_ss(),.sd_nv(),.sd_wa(),.sd_xa(),.sys_sum(1024'd0),.sys_fault(1'b0),.lane_faults(lane_faults),.tree_faults(tree_faults),.final_sum(final_sum),.final_vo(final_vo),
  .lane_meta(lane_meta),.lane_gov(lane_gov),.lane_first(lane_first),.lane_done(lane_done));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin staged<=0;fault<=0;end
  else begin
   if(stage_begin_q)begin if(!idle)fault<=1;staged<=0;end
   if(stage_v_q)begin
    if(stage_word_q!=staged || staged>=80 || !idle)fault<=1;
    staged<=staged+1'b1;
   end
   // Availability is a check; it never moves the command's compiled cycle.
   if(cmd_v_q && (!ready || staged!=80 || cmd_layer_q>42))fault<=1;
   if(hfault)fault<=1;
  end
 end
endmodule

// A real clock-owned bank with eight resident ROMs and two mutable x SRAMs.
// Captures are relocated from the original leaf and HCP, never added/deleted.
module ot_s81_hcx_hcp_bank #(parameter IMAGE="hcx_r0",parameter integer BANK=0,MUT_BANK=0,MUT_PAGE=0)(
 input wire clk,rst_n,stage_v,wr,xr,
 input wire [6:0] stage_word,
 input wire [511:0] stage_d,
 input wire [15:0] wa,xa,
 output reg [1023:0] wd,
 output reg [511:0] xd
);
 reg [511:0] stage_d_q;
 reg page_q;
 reg wr_q,xr_q,stage_v_q;
 reg [15:0] wa_q,xa_q;
 reg [6:0] stage_word_q;
 wire [1023:0] wd1;
 wire [511:0] xd1;
 reg [1023:0] wd2;
 reg [511:0] xd2;
 always @(posedge clk)begin
  stage_d_q<=stage_d;wd2<=wd1;xd2<=xd1;wd<=wd2;xd<=xd2;
  wa_q<=wa;xa_q<=xa;stage_word_q<=stage_word;
  if(wr_q)page_q<=wa_q[12];
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin wr_q<=0;xr_q<=0;stage_v_q<=0;end
  else begin wr_q<=wr;xr_q<=xr;stage_v_q<=stage_v;end
 for(genvar m=0;m<4;m=m+1)begin:g_rom
  wire [265:0] q[0:1];
  for(genvar pg=0;pg<2;pg=pg+1)begin:g_page
`ifndef SYNTHESIS
   ot_rom_4096x266_m8 #(.INSTANCE($sformatf("%s_b%0d_l%0d_p%0d",IMAGE,BANK,m,pg)))rom(
`else
   ot_rom_4096x266_m8 rom(
`endif
    .clk(clk),.ce_in(wr_q && wa_q[12]==pg),.addr_in(wa_q[11:0]),.rd_out(q[pg]));
  end
  assign wd1[m*256+:256]=((MUT_BANK && BANK==7)||(MUT_PAGE&&page_q))?256'd0:q[page_q][255:0];
 end
 for(genvar m=0;m<2;m=m+1)begin:g_x
  ot_sram_1r1w_128x256_m1_r2c2 ram(
   .clk(clk),.r_ce_in(xr_q),.r_addr_in(xa_q[6:0]),.rd_out(xd1[m*256+:256]),
   .w_ce_in(stage_v_q),.w_addr_in(stage_word_q),.wd_in(stage_d_q[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 end
endmodule

`default_nettype wire
