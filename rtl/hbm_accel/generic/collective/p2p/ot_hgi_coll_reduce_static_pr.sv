`timescale 1ns/1ps
`default_nettype none
// HBM-P5-RTLB 10-23: over-cap SPLIT twin of the reduce core of ot_hfd_coll_q2_hard_v8g (cut ring_ag | reduce | body,
// physical/die_plan/hbm/over_cap_split/ot_hfd_coll_q2_hard_v8g.split.json).  Measured crossing classes
// (tools/hbm_split/port_regclass.py, Yosys 0.68 flattened RTL; results/.. in the split.json):
//   body -> reduce: clear (uop d3 flop), in_v / in_flit (qso slice flops), load_v .. pub_issue (uop d3 / AR_ITER t_*
//     flops), pub_meta / pub_release: LAUNCH reg, but the pinned reduce CAPTURES clear, in_v, in_flit, load_* , read_tag,
//     add_*, pub_read, pub_tag_*, pub_bf16, pub_issue in logic (tag decode / enables / adder operands) = UNREGISTERED.
//   reduce -> body: out_v / out_flit / fault_cause flops (captured by the qslots capture_pin_v2 flops: reg -> reg);
//     fault is COMB (OR of lane / sticky terms) into u_fj's flop = UNREGISTERED.
// This twin = the pinned ot_hgi_coll_reduce_static unchanged + ONE input pin register on EVERY data/control input
// (clk_control root, async reset on the valid / strobe bits, data unreset) + ONE fault output register.  Every input is
// delayed uniformly, so the reduce runs exactly 1 edge later: out_v / out_flit / fault_cause +1 edge, fault +2 edges.
// COST: +1 edge on every AR reduce publication (the qslots reduce-source capture slot moves 1 edge later in the
// compiled programme); the fault status +2 edges.  The ring_ag core needs nothing (its only body crossing, fault, is a
// flop captured by u_fj's flop; every other ring port is a master pin).
// MUT (bench): 1 = in_flit NOT registered (data one edge ahead of its control) -> must FAIL; 2 = fault not registered.
module ot_hgi_coll_reduce_static_pr #(parameter integer MUT_TAG=0,MUT_BF16=0,MUT=0,
 // Local physical profile can select kept replicas without editing generated
 // split-core tops. Normal/default builds retain the shared control stage.
 parameter integer LOCAL_CTRL=
`ifdef OT_HBM_REDUCE_LOCAL_CTRL
 1
`else
 0
`endif
)(
 input wire clk_control,input wire [15:0] clk_state,clk_add,
 input wire rst_n,clear,in_v,input wire [544:0] in_flit,
 input wire load_v,input wire [3:0] load_tag,
 input wire add_read,input wire [3:0] read_tag,input wire add_issue,
 input wire pub_read,input wire [3:0] pub_tag_a,pub_tag_b,
 input wire pub_bf16,input wire [32:0] pub_meta,input wire pub_release,pub_issue,
 output wire out_v,output wire [544:0] out_flit,
 output wire fault,output wire [7:0] fault_cause
);
 reg clear_q,in_v_q,load_v_q,add_read_q,add_issue_q,pub_read_q,pub_release_q,pub_issue_q;
 reg [544:0] in_flit_q; reg [3:0] load_tag_q,read_tag_q,pub_tag_a_q,pub_tag_b_q; reg pub_bf16_q; reg [32:0] pub_meta_q;
 always @(posedge clk_control or negedge rst_n)
  if(!rst_n)begin clear_q<=1'b0;in_v_q<=1'b0;load_v_q<=1'b0;add_read_q<=1'b0;add_issue_q<=1'b0;pub_read_q<=1'b0;
   pub_release_q<=1'b0;pub_issue_q<=1'b0;end
  else begin clear_q<=clear;in_v_q<=in_v;load_v_q<=load_v;add_read_q<=add_read;add_issue_q<=add_issue;
   pub_read_q<=pub_read;pub_release_q<=pub_release;pub_issue_q<=pub_issue;end
 always @(posedge clk_control)begin
  in_flit_q<=in_flit;load_tag_q<=load_tag;read_tag_q<=read_tag;pub_tag_a_q<=pub_tag_a;pub_tag_b_q<=pub_tag_b;
  pub_bf16_q<=pub_bf16;pub_meta_q<=pub_meta;
 end
 wire f_c;
`ifdef OT_HBM_REDUCE_LREP
 // DIE-HBM-61/CUTS 11-03 (opt-in define OT_HBM_REDUCE_LREP; without it the code below the `else is compiled, names and
 // netlist unchanged): per-lane KEPT copies of the lane control pin registers (same edge as the shared *_q registers,
 // same reset class), each driving one lane of ot_hgi_coll_reduce_static_lr. Census 766 ps (pub_tag_a_q fanout into 16
 // lanes' 16:1 read muxes) -> one lane per copy. 0 added cycles, every port edge unchanged.
 // LMUT (bench): 1 = lane 8 pub_tag_a copy captures pub_tag_b; 2 = lane 3 load_v copy one edge late; 3 = lane 5 read_tag
 // copy holds its value while add_read is low (equivalent mutant: bench cannot see it); 4 = lane 12 add_issue copy stuck 0.
 localparam integer LMUT=
`ifdef OT_HBM_REDUCE_LMUT
 `OT_HBM_REDUCE_LMUT
`else
 0
`endif
 ;
 (* keep = 1 *) reg [15:0] ln_load_v_q,ln_add_read_q,ln_pub_read_q,ln_add_issue_q;
 (* keep = 1 *) reg [63:0] ln_load_tag_q,ln_read_tag_q,ln_pub_tag_a_q,ln_pub_tag_b_q;
 reg lmut_lv_d;
 always @(posedge clk_control or negedge rst_n)
  if(!rst_n)begin ln_load_v_q<=16'd0;ln_add_read_q<=16'd0;ln_pub_read_q<=16'd0;ln_add_issue_q<=16'd0;lmut_lv_d<=1'b0;end
  else begin
   ln_load_v_q<={16{load_v}};ln_add_read_q<={16{add_read}};ln_pub_read_q<={16{pub_read}};
   ln_add_issue_q<={16{add_issue}};lmut_lv_d<=load_v;
   if(LMUT==2) ln_load_v_q[3]<=lmut_lv_d;
   if(LMUT==4) ln_add_issue_q[12]<=1'b0;
  end
 always @(posedge clk_control)begin
  ln_load_tag_q<={16{load_tag}};ln_pub_tag_a_q<={16{pub_tag_a}};ln_pub_tag_b_q<={16{pub_tag_b}};
  ln_read_tag_q<={16{read_tag}};
  if(LMUT==1) ln_pub_tag_a_q[4*8+:4]<=pub_tag_b;
  if(LMUT==3 && !add_read) ln_read_tag_q[4*5+:4]<=ln_read_tag_q[4*5+:4];
 end
 ot_hgi_coll_reduce_static_lr #(.MUT_TAG(MUT_TAG),.MUT_BF16(MUT_BF16),.LOCAL_CTRL(LOCAL_CTRL)) u_red(
  .ln_load_v(ln_load_v_q),.ln_add_read(ln_add_read_q),.ln_pub_read(ln_pub_read_q),.ln_add_issue(ln_add_issue_q),
  .ln_load_tag(ln_load_tag_q),.ln_read_tag(ln_read_tag_q),.ln_pub_tag_a(ln_pub_tag_a_q),.ln_pub_tag_b(ln_pub_tag_b_q),
  .clk_control(clk_control),.clk_state(clk_state),.clk_add(clk_add),.rst_n(rst_n),.clear(clear_q),.in_v(in_v_q),
  .in_flit((MUT==1)?in_flit:in_flit_q),.load_v(load_v_q),.load_tag(load_tag_q),.add_read(add_read_q),.read_tag(read_tag_q),
  .add_issue(add_issue_q),.pub_read(pub_read_q),.pub_tag_a(pub_tag_a_q),.pub_tag_b(pub_tag_b_q),.pub_bf16(pub_bf16_q),
  .pub_meta(pub_meta_q),.pub_release(pub_release_q),.pub_issue(pub_issue_q),
  .out_v(out_v),.out_flit(out_flit),.fault(f_c),.fault_cause(fault_cause));
`else
 ot_hgi_coll_reduce_static #(.MUT_TAG(MUT_TAG),.MUT_BF16(MUT_BF16),.LOCAL_CTRL(LOCAL_CTRL)) u_red(
  .clk_control(clk_control),.clk_state(clk_state),.clk_add(clk_add),.rst_n(rst_n),.clear(clear_q),.in_v(in_v_q),
  .in_flit((MUT==1)?in_flit:in_flit_q),.load_v(load_v_q),.load_tag(load_tag_q),.add_read(add_read_q),.read_tag(read_tag_q),
  .add_issue(add_issue_q),.pub_read(pub_read_q),.pub_tag_a(pub_tag_a_q),.pub_tag_b(pub_tag_b_q),.pub_bf16(pub_bf16_q),
  .pub_meta(pub_meta_q),.pub_release(pub_release_q),.pub_issue(pub_issue_q),
  .out_v(out_v),.out_flit(out_flit),.fault(f_c),.fault_cause(fault_cause));
`endif
 if(MUT==2)begin:g_fmut assign fault=f_c; end
 else begin:g_freg reg f_q; always @(posedge clk_control or negedge rst_n) if(!rst_n) f_q<=1'b0; else f_q<=f_c; assign fault=f_q; end
endmodule
`default_nettype wire
