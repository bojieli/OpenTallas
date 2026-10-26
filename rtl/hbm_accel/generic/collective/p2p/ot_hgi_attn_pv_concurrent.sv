`timescale 1ns/1ps
`default_nettype none
// Qwen8192 PV after canonical SM128-row subtree publication. Thirty-two actual
// native stager read ports provide packed512b rows. All computation and link
// registers below are RTL. One operation always issues128fixed input edges;
// unavailable/misaligned producers fault and never stretch that timeline.
// No physical view or full-SM qualification is inherited by this parent.
module ot_hgi_attn_pv_concurrent #(
 parameter integer LINK_A=2,LINK_B=2,
 parameter integer MUT_PAIR=0,MUT_SLOT=0,MUT_DATA=0
)(
 input wire clk,rst_n,start,
 input wire [7:0] epoch0,epoch1,
 input wire bank0,bank1,
 input wire [31:0] row_v,
 input wire [32*512-1:0] row_data,
 input wire [32*6-1:0] row_sequence,
 input wire [32*8-1:0] row_epoch,
 input wire [31:0] row_bank,
 output wire input_slot,
 output wire [5:0] expected_sequence,
 output wire [7:0] expected_epoch,
 output wire expected_bank,
 output wire out_v,
 output wire [511:0] out_data,
 output wire [5:0] out_sequence,
 output wire [7:0] out_epoch,
 output wire out_group,
 output reg done,
 output wire fault
);
 generate if(LINK_A<1 || LINK_B<1)begin:g_illegal_links
  concurrent_pv_requires_registered_links illegal_configuration();
 end endgenerate
 localparam integer TW=15;
 localparam integer LAST=128+6*8+LINK_A+LINK_B;
 reg active;
 reg [8:0] cycle;
 reg [7:0] e0,e1;
 reg b0,b1;
 reg control_fault;
 wire [8:0] ordinal=cycle-9'd4;
 assign input_slot=active && cycle>=4 && cycle<132;
 assign expected_sequence=ordinal[5:0];
 assign expected_epoch=ordinal[6]?e1:e0;
 assign expected_bank=ordinal[6]?b1:b0;
 wire [TW-1:0] issue_tag={expected_epoch,ordinal[6],ordinal[5:0]};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;cycle<=0;e0<=0;e1<=0;b0<=0;b1<=0;control_fault<=0;done<=0;end
  else begin
   done<=0;
   if(start)begin
    if(active)control_fault<=1;
    active<=1;cycle<=0;e0<=epoch0;e1<=epoch1;b0<=bank0;b1<=bank1;
    if(bank0==bank1 || epoch0==epoch1)control_fault<=1;
   end else if(active)begin
    cycle<=cycle+1'b1;
    if(cycle==LAST+8)begin active<=0;done<=1;end
   end
   if(row_v!={32{input_slot}})control_fault<=1;
   if(input_slot)for(integer s=0;s<32;s=s+1)begin
    if(row_sequence[s*6+:6]!=expected_sequence || row_epoch[s*8+:8]!=expected_epoch || row_bank[s]!=expected_bank)
     control_fault<=1;
   end
  end
 end
 wire [4*8*256-1:0] a_send,a_keep;
 wire [4*8*256-1:0] a_wire,a_local,a_result;
 wire a_input_v,a_v;
 wire [TW-1:0] a_input_context,a_context;
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(LINK_A)) a_control(
  .clk(clk),.rst_n(rst_n),.d({input_slot,issue_tag}),.q({a_input_v,a_input_context}));
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(8)) a_tag(
  .clk(clk),.rst_n(rst_n),.d({a_input_v,a_input_context}),.q({a_v,a_context}));
 wire [31:0] a_fault,a_align_fault;
 for(genvar q=0;q<4;q=q+1)begin:g_aq
  for(genvar sm=0;sm<8;sm=sm+1)begin:g_sm
   localparam integer S=q*8+sm;
   for(genvar h=0;h<2;h=h+1)begin:g_head
    for(genvar t=0;t<2;t=t+1)begin:g_time
     for(genvar half=0;half<2;half=half+1)begin:g_half
      localparam integer lane=4*h+2*t+half;
      localparam integer keep_word=8*t+2*(2*h+(q%2))+half;
      localparam integer send_word=8*t+2*(2*h+(1-q%2))+half;
      assign a_keep[S*256+lane*32+:32]=row_data[S*512+keep_word*32+:32];
      assign a_send[S*256+lane*32+:32]=row_data[S*512+send_word*32+:32];
     end
    end
   end
   ot_hgi_pv_fixed_delay #(.W(256),.D(LINK_A),.RESET(0)) u_send(
    .clk(clk),.rst_n(rst_n),.d(a_send[S*256+:256]),.q(a_wire[S*256+:256]));
   ot_hgi_pv_fixed_delay #(.W(256),.D(LINK_A),.RESET(0)) u_keep(
    .clk(clk),.rst_n(rst_n),.d(a_keep[S*256+:256]),.q(a_local[S*256+:256]));
   localparam integer PEER=(q^1)*8+sm;
   wire av;
   ot_hgi_pv_vector_add #(.N(8)) u_add(
    .clk(clk),.rst_n(rst_n),.v(a_input_v),
    .a(a_local[S*256+:256]),.b(MUT_DATA?256'b0:a_wire[PEER*256+:256]),
    .ov(av),.y(a_result[S*256+:256]),.fault(a_fault[S]));
   // All scalar lanes issue on the compiler slot, independently of data.
   assign a_align_fault[S]=av ^ a_v;
  end
 end
 wire [4*8*128-1:0] b_send,b_keep,b_wire,b_local,b_result;
 wire b_input_v,b_v;
 wire [TW-1:0] b_input_context,b_context;
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(LINK_B)) b_control(
  .clk(clk),.rst_n(rst_n),.d({a_v,a_context}),.q({b_input_v,b_input_context}));
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(8)) b_tag(
  .clk(clk),.rst_n(rst_n),.d({b_input_v,b_input_context}),.q({b_v,b_context}));
 wire [31:0] b_fault,b_align_fault;
 for(genvar q=0;q<4;q=q+1)begin:g_bq
  for(genvar sm=0;sm<8;sm=sm+1)begin:g_sm
   localparam integer S=q*8+sm;
   localparam integer KEEP=q/2;
   assign b_keep[S*128+:128]=a_result[S*256+KEEP*128+:128];
   assign b_send[S*128+:128]=a_result[S*256+(1-KEEP)*128+:128];
   ot_hgi_pv_fixed_delay #(.W(128),.D(LINK_B),.RESET(0)) u_send(
    .clk(clk),.rst_n(rst_n),.d(b_send[S*128+:128]),.q(b_wire[S*128+:128]));
   ot_hgi_pv_fixed_delay #(.W(128),.D(LINK_B),.RESET(0)) u_keep(
    .clk(clk),.rst_n(rst_n),.d(b_keep[S*128+:128]),.q(b_local[S*128+:128]));
   localparam integer PEER=(q^(MUT_PAIR?1:2))*8+sm;
   wire bv;
   ot_hgi_pv_vector_add #(.N(4)) u_add(
    .clk(clk),.rst_n(rst_n),.v(b_input_v),.a(b_local[S*128+:128]),.b(b_wire[PEER*128+:128]),
    .ov(bv),.y(b_result[S*128+:128]),.fault(b_fault[S]));
   assign b_align_fault[S]=bv ^ b_v;
  end
 end
 // Consecutive native SRAM rows alternate blockslot0/1 at each dimension pair.
 // One actual128bit register/SM retains slot0 until slot1 arrives one edge later.
 reg [4095:0] slot_hold;
 reg slot_valid;
 reg [TW-2:0] slot_context;
 reg slot_fault;
 wire slot_issue=b_v && b_context[0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin slot_valid<=0;slot_context<=0;slot_fault<=0;end
  else if(b_v)begin
   if(!b_context[0])begin
    if(slot_valid)slot_fault<=1;
    slot_valid<=1;slot_context<=b_context[TW-1:1];
   end else begin
    if(!slot_valid || slot_context!=b_context[TW-1:1])slot_fault<=1;
    slot_valid<=0;
   end
  end
 end
 always @(posedge clk)if(b_v && !b_context[0])slot_hold<=b_result;
 wire [4095:0] slot_result;
 wire slot_v;
 wire [TW-1:0] slot_tag;
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(8)) slot_control(
  .clk(clk),.rst_n(rst_n),.d({slot_issue,b_context}),.q({slot_v,slot_tag}));
 wire [31:0] s_fault,s_align_fault;
 for(genvar s=0;s<32;s=s+1)begin:g_slot
  wire sv;
  ot_hgi_pv_vector_add #(.N(4)) u_add(
   .clk(clk),.rst_n(rst_n),.v(slot_issue),.a(MUT_SLOT?b_result[s*128+:128]:slot_hold[s*128+:128]),
   .b(b_result[s*128+:128]),.ov(sv),.y(slot_result[s*128+:128]),.fault(s_fault[s]));
  assign s_align_fault[s]=sv ^ slot_v;
 end
 wire [2047:0] tree0;
 wire [1023:0] tree1;
 wire [511:0] tree2;
 wire t0v,t1v,t2v;
 wire [TW-1:0] t0tag,t1tag,t2tag;
 wire [15:0] tf0,ta0;wire [7:0] tf1,ta1;wire [3:0] tf2,ta2;
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(8)) t0c(.clk(clk),.rst_n(rst_n),.d({slot_v,slot_tag}),.q({t0v,t0tag}));
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(8)) t1c(.clk(clk),.rst_n(rst_n),.d({t0v,t0tag}),.q({t1v,t1tag}));
 ot_hgi_pv_fixed_delay #(.W(1+TW),.D(8)) t2c(.clk(clk),.rst_n(rst_n),.d({t1v,t1tag}),.q({t2v,t2tag}));
 for(genvar q=0;q<4;q=q+1)begin:g_tree
  for(genvar p=0;p<4;p=p+1)begin:g_l0
   wire v;
   ot_hgi_pv_vector_add #(.N(4)) u_add(.clk(clk),.rst_n(rst_n),.v(slot_v),
    .a(slot_result[(q*8+2*p)*128+:128]),.b(slot_result[(q*8+2*p+1)*128+:128]),
    .ov(v),.y(tree0[(q*4+p)*128+:128]),.fault(tf0[q*4+p]));
   assign ta0[q*4+p]=v ^ t0v;
  end
  for(genvar p=0;p<2;p=p+1)begin:g_l1
   wire v;
   ot_hgi_pv_vector_add #(.N(4)) u_add(.clk(clk),.rst_n(rst_n),.v(t0v),
    .a(tree0[(q*4+2*p)*128+:128]),.b(tree0[(q*4+2*p+1)*128+:128]),
    .ov(v),.y(tree1[(q*2+p)*128+:128]),.fault(tf1[q*2+p]));
   assign ta1[q*2+p]=v ^ t1v;
  end
  wire v;
  ot_hgi_pv_vector_add #(.N(4)) u_add(.clk(clk),.rst_n(rst_n),.v(t1v),
   .a(tree1[(q*2)*128+:128]),.b(tree1[(q*2+1)*128+:128]),
   .ov(v),.y(tree2[q*128+:128]),.fault(tf2[q]));
  assign ta2[q]=v ^ t2v;
 end
 assign out_v=t2v;assign out_data=tree2;
 assign out_sequence=t2tag[5:0];assign out_group=t2tag[6];assign out_epoch=t2tag[14:7];
 assign fault=control_fault|slot_fault|(|a_align_fault)|(|b_align_fault)|(|s_align_fault)|(|ta0)|(|ta1)|(|ta2)|(|a_fault)|(|b_fault)|(|s_fault)|(|tf0)|(|tf1)|(|tf2);
endmodule

// Exact reused native LAT8 scalar leaf. Parent replication is not a new claim
// of physical signoff; each instance still needs actual clock/pin integration.
module ot_hgi_pv_vector_add #(parameter integer N=4)(
 input wire clk,rst_n,v,input wire [N*32-1:0] a,b,
 output wire ov,output wire [N*32-1:0] y,output wire fault
);
 wire [N-1:0] valid;
 for(genvar l=0;l<N;l=l+1)begin:g_add
  ot_hgi_coll_pring_static_add_lane #(.LAT(8)) lane(
   .clk(clk),.rst_n(rst_n),.valid_in(v),.a(a[l*32+:32]),.b(b[l*32+:32]),
   .valid_out(valid[l]),.y(y[l*32+:32]));
 end
 assign ov=valid[0];assign fault=valid!={N{valid[0]}};
endmodule

// Real pipeline registers, not latency-only arithmetic or link substitutions.
module ot_hgi_pv_fixed_delay #(parameter integer W=1,D=1,RESET=1)(
 input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q
);
 reg [W-1:0] p[0:D-1];
 generate if(RESET)begin:g_reset
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)for(integer k=0;k<D;k=k+1)p[k]<=0;
  else begin p[0]<=d;for(integer k=1;k<D;k=k+1)p[k]<=p[k-1];end
 end
 end else begin:g_data
  always @(posedge clk)begin p[0]<=d;for(integer k=1;k<D;k=k+1)p[k]<=p[k-1];end
 end endgenerate
 assign q=p[D-1];
endmodule
`default_nettype wire
