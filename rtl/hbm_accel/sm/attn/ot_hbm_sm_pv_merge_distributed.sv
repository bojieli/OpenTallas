`timescale 1ns/1ps
`default_nettype none
// PRIVATE candidate. Source-owned input and output registers; disable automatic pin regs.
// L2H-SMATT/PVMD 10-19: MUT 1..5 = the SAFE2 core negative controls; wrapper negative controls of the distributed
// source (bench only, never a kit value): 6 ev_operand[5] taken from the first ev capture (one edge early); 7 the scheduler ev copy
// (ev2[96]) taken from the first capture (one edge early); 8 ev_write[9] from the first capture; 9 the e_busy
// reset group never asserted (stale state survives a reassert); 10 second-level node 3 asserted synchronously (no
// stopped-clock reset); 11 first_operand[7] from the first tag capture (one edge early).
module ot_hbm_sm_pv_merge_distributed #(parameter integer MUT=0)(
 input wire clk,rst_n,ev,input wire [511:0] sum,input wire [15:0] tag_d,
 output reg pv_v,output reg [511:0] pv_y,output reg [15:0] pv_tag,output reg fault,
 input wire pub_start,input wire [2:0] pub_slot,
 output reg pub_v,output reg [31:0] pub_data,output reg [3:0] pub_word,
 output reg [2:0] pub_out_slot,output reg [15:0] pub_tag,
 input wire fold_start,input wire [2:0] fold_a,fold_b
);
 // PVMD (L2H-SMATT 10-19): every register below drives <= 32 loads (fleet yosys census, results/arch/hbm_pvm_distributed_source_1019).
 // Reset: rst_n -> 2 first (D=1) -> 8 second -> 53 third release flops (async assert, sync release); the core sees its
 // reset release 3 edges after rst_n (SAFE2 reference: 2), the input captures 2 (as the reference's pin regs).
 // (54 third-level groups: core groups 0-53, see ot_hbm_sm_pv_merge_distributed_core; second node 6 drives 6.)
 localparam integer NEV = 137;                      // ev second captures: 64 operand + 64 write + 8 entry + 1 control
 wire [1:0] reset_first_n; wire [7:0] reset_second_n; wire [53:0] reset_core_n;
 generate
 for(genvar ri=0;ri<2;ri=ri+1) begin:g_reset_first
  ot_pvm_reset_release #(.ID(ri)) u(.clk(clk),.rn(rst_n),.q(reset_first_n[ri]));
 end
 for(genvar ri=0;ri<8;ri=ri+1) begin:g_reset_second
  ot_pvm_reset_release #(.ID(2+ri),.SYNC(MUT==10 && ri==3)) u(.clk(clk),.rn(reset_first_n[ri/4]),.q(reset_second_n[ri]));
 end
 for(genvar ri=0;ri<54;ri=ri+1) begin:g_reset_core
  ot_pvm_reset_release #(.ID(10+ri)) u(.clk(clk),.rn(reset_second_n[ri/8]),.q(reset_core_n[ri]));
 end
 endgenerate
 // ev: 5 first captures (<= 28 second copies each) -> 137 second copies (reset spread over the 8 second nodes)
 wire [4:0] ev1; wire [NEV-1:0] ev2; wire [1:0] first1; wire [63:0] first2;
 generate
 for(genvar ei=0;ei<5;ei=ei+1) begin:g_event_first
  ot_pvm_capture #(.ID(ei),.RESET(1)) u(.clk(clk),.rn(reset_second_n[ei]),.d(ev),.q(ev1[ei]));
 end
 for(genvar ei=0;ei<NEV;ei=ei+1) begin:g_event_second
  ot_pvm_capture #(.ID(8+ei),.RESET(1)) u(.clk(clk),.rn(reset_second_n[ei%8]),.d(ev1[ei/28]),.q(ev2[ei]));
 end
 for(genvar ti=0;ti<2;ti=ti+1) begin:g_first_tag1
  ot_pvm_capture #(.ID(200+ti)) u(.clk(clk),.rn(1'b1),.d(tag_d[14]),.q(first1[ti]));
 end
 for(genvar ti=0;ti<64;ti=ti+1) begin:g_first_tag
  ot_pvm_capture #(.ID(210+ti)) u(.clk(clk),.rn(1'b1),.d(first1[ti/32]),.q(first2[ti]));
 end
 endgenerate
 reg [511:0] sum1,sum2; reg [15:0] tag1,tag2;
 reg [2:0] pubslot1,pubslot2,folda1,folda2,foldb1,foldb2;
 (* keep *) reg [14:0] pubslot2t;                   // 5 kept pub_slot copies (node_tag read mux x4, slot0)
 always @(posedge clk) begin
  sum1<=sum;sum2<=sum1;tag1<=tag_d;tag2<=tag1;
  pubslot1<=pub_slot;pubslot2<=pubslot1;pubslot2t<={5{pubslot1}};
  folda1<=fold_a;folda2<=folda1;foldb1<=fold_b;foldb2<=foldb1;
 end
 // pub / fold commands: first capture -> control second capture (+ 4 fold_start copies for the fd0_k slices)
 wire pub1,pub2,fold1,fold2; wire [3:0] fold2c;
 ot_pvm_capture #(.ID(300),.RESET(1)) u_pub1(.clk(clk),.rn(reset_second_n[0]),.d(pub_start),.q(pub1));
 ot_pvm_capture #(.ID(301),.RESET(1)) u_pub2(.clk(clk),.rn(reset_second_n[0]),.d(pub1),.q(pub2));
 ot_pvm_capture #(.ID(302),.RESET(1)) u_fold1(.clk(clk),.rn(reset_second_n[1]),.d(fold_start),.q(fold1));
 ot_pvm_capture #(.ID(303),.RESET(1)) u_fold2(.clk(clk),.rn(reset_second_n[1]),.d(fold1),.q(fold2));
 wire [3:0] pub2c;
 generate for(genvar pi=0;pi<4;pi=pi+1) begin:g_pub_copy
  ot_pvm_capture #(.ID(320+pi),.RESET(1)) u(.clk(clk),.rn(reset_second_n[4+pi]),.d(pub1),.q(pub2c[pi]));
 end endgenerate
 generate for(genvar fi=0;fi<4;fi=fi+1) begin:g_fold_copy
  ot_pvm_capture #(.ID(310+fi),.RESET(1)) u(.clk(clk),.rn(reset_second_n[2+fi]),.d(fold1),.q(fold2c[fi]));
 end endgenerate
 // core-side copies (MUT 6..11 rewire one copy; MUT 0 = identity)
 wire [63:0] ev_op_c = (MUT==6) ? {ev2[63:6],ev1[0],ev2[4:0]} : ev2[63:0];
 wire [63:0] ev_wr_c = (MUT==8) ? {ev2[127:74],ev1[1],ev2[72:64]} : ev2[127:64];
 wire [7:0]  ev_en_c = ev2[135:128];
 wire        ev_sch_c = (MUT==7) ? ev1[3] : ev2[136];
 wire [63:0] first_c = (MUT==11) ? {first2[63:8],first1[0],first2[6:0]} : first2;
 wire [53:0] rcore_c = (MUT==9) ? {reset_core_n[53:14],1'b1,reset_core_n[12:0]} : reset_core_n;
 wire cpv,cpub,cfault;wire [511:0] cy;wire [15:0] ctag,cptag;wire[31:0] cdata;wire[3:0] cword;wire[2:0] cslot;
 ot_hbm_sm_pv_merge_distributed_core #(.TAGW(16),.LV(4),.MUT(MUT),.PUBLISH(1),.TURNREG(1),.SAFE(2)) u_core(
  .clk(clk),.rst_core_n(rcore_c),.ev_operand(ev_op_c),.ev_write(ev_wr_c),.ev_entry(ev_en_c),.fold_operand(fold2c),.pub_operand(pub2c),.pub_slot_tag(pubslot2t),
  .first_operand(first_c),
  .ev(ev_sch_c),.sum(sum2),.tag_d(tag2),.pv_v(cpv),.pv_y(cy),.pv_tag(ctag),.fault(cfault),
  .pub_start(pub2),.pub_slot(pubslot2),.pub_v(cpub),.pub_data(cdata),.pub_word(cword),.pub_out_slot(cslot),.pub_tag(cptag),
  .fold_start(fold2),.fold_a(folda2),.fold_b(foldb2));
 // Existing one output edge retained. Valid/fault reset distributed in <=32 group.
 always @(posedge clk) begin pv_y<=cy;pv_tag<=ctag;pub_data<=cdata;pub_word<=cword;pub_out_slot<=cslot;pub_tag<=cptag;end
 always @(posedge clk or negedge reset_core_n[15])
  if(!reset_core_n[15]) begin pv_v<=0;pub_v<=0;fault<=0;end
  else begin pv_v<=cpv;pub_v<=cpub;fault<=cfault;end
endmodule
// ID makes every kept copy a distinct paramod; native audit must verify survival.
// SYNC 1 = bench negative control only (MUT 10): synchronous assertion.
(* keep_hierarchy="yes" *) module ot_pvm_reset_release #(parameter integer ID=0,SYNC=0)(input wire clk,rn,(* keep *) output reg q);
 (* keep *) wire d=1'b1;
 // q is (* keep *) as well: the copy survives even when a flow flattens away keep_hierarchy (opt_merge)
 generate if(SYNC) begin:g_sync
  always @(posedge clk) if(!rn) q<=1'b0;else q<=d;
 end else begin:g_async
  always @(posedge clk or negedge rn) if(!rn) q<=1'b0;else q<=d;
 end endgenerate
endmodule
(* keep_hierarchy="yes" *) module ot_pvm_capture #(parameter integer ID=0,RESET=0)(input wire clk,rn,d,(* keep *) output reg q);
 generate if(RESET) begin:g_reset
  always @(posedge clk or negedge rn) if(!rn) q<=0;else q<=d;
 end else begin:g_data
  always @(posedge clk) q<=d;
 end endgenerate
endmodule
`default_nettype wire
