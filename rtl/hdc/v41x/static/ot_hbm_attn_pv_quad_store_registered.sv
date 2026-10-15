`timescale 1ns/1ps
`default_nettype none
// Quad-local D successor. Input is the producer's literal four-head quad order,
// not four consecutive logical heads. Epoch rows are independent real SRAM rows.
// Write face adds one availability edge; read face adds one read edge.
module ot_hbm_attn_pv_quad_store_registered(
 input wire clk,rst_n,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[127:0]capture_data,input wire[3:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[1:0]drain_lane,
 output reg output_v,output reg[511:0]drain_data,
 output reg[15:0]drain_flags
);
 reg wv,wepoch;reg[3:0]wdim;reg[127:0]wd;reg[3:0]wf;
 reg rv;reg[1:0]lane_q;
 wire[127:0]mq[0:15];wire[3:0]fq[0:15];
 always @(posedge clk)begin
  wepoch<=capture_epoch;wdim<=capture_dim;wd<=capture_data;wf<=capture_flags;
  if(drain_v)lane_q<=drain_lane;
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin wv<=0;rv<=0;output_v<=0;end
 else begin wv<=capture_v;rv<=drain_v;output_v<=rv;end
 genvar c,e;
 generate for(c=0;c<16;c=c+1)begin:g_dim
  wire wr=wv&&wdim==4'(c);
  ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),.r_ce_in(drain_v),
   .r_addr_in({4'd0,drain_epoch}),.rd_out(mq[c]),
   .w_ce_in(wr),.w_addr_in({4'd0,wepoch}),.wd_in(wd),.w_mask_in({128{1'b1}}));
  wire[7:0]flags_epochs;
  for(e=0;e<2;e=e+1)begin:g_epoch
   reg[3:0]stored;
   always @(posedge clk)if(wr&&wepoch==1'(e))stored<=wf;
   assign flags_epochs[e*4+:4]=stored;
  end
  reg[3:0]read_flags;
  always @(posedge clk)if(drain_v)read_flags<=flags_epochs[drain_epoch*4+:4];
  assign fq[c]=read_flags;
  always @(posedge clk)if(rv)begin
   drain_data[c*32+:32]<=mq[c][lane_q*32+:32];
   drain_flags[c]<=fq[c][lane_q];
  end
 end endgenerate
endmodule

// Real registered four-cohort boundary; select is captured before decode.
// Source input capture and output register are two separately priced edges.
module ot_hbm_attn_pv_cohort_select_registered(
 input wire clk,rst_n,capture_v,input wire[1:0]cohort_select,
 input wire[2047:0]quad_data,input wire[63:0]quad_flags,
 output reg output_v,output reg[511:0]tile_data,
 output reg[15:0]tile_flags
);
 reg[2047:0]data_q;reg[63:0]flags_q;reg[1:0]select_q;reg valid_q;
 always @(posedge clk)begin
  data_q<=quad_data;flags_q<=quad_flags;select_q<=cohort_select;
  if(valid_q)begin
   tile_data<=data_q[select_q*512+:512];
   tile_flags<=flags_q[select_q*16+:16];
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin valid_q<=0;output_v<=0;end
 else begin valid_q<=capture_v;output_v<=valid_q;end
endmodule
`default_nettype wire
