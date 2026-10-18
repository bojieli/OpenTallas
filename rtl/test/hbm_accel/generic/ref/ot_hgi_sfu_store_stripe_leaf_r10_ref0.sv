`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_store_stripe_leaf_r10 (SFU-PS-FUND 2026-10-17): ONE stripe of the SFU programme store (2048 x 256 = one
// 222-bit calendar field + 34-bit word check) as one small hardened "spine" leaf, replicated 11x by
// ot_hgi_sfu_programme_store_r10 (8 programme stripes + 3 IO stripes; one master, no variants).
// Why (design decision: claude-takeover lanes/SFU-PS-FUND.md): r7c4 .. r9d failed because many 831-pin SRAMs were stacked
// with the register mass, the pins and the clock entering from one side. Here the stripe uses FOUR narrow
// ot_sram_1r1w_512x256_m1_r2c2 macros (96.6 x 69.7 um, every read pin on the A edge) placed as 2 rows of a mirrored
// pair (MY | spine | R0): every macro A edge (clk, addr, rd_out, wd_in[136:0]) faces ONE centre std-cell spine that
// holds the read path (captured, page mux, calendar, stripe control); B edges (wd_in[255:137] + ties) face thin
// outer bands with no clock sinks. Inputs enter on the N face (N band: pin flops), outputs leave on the S face
// (S band: relay + gated output = the store output registers), clock enters at the S-face spine foot.
// Function per stripe = ot_hgi_sfu_program_stripe_r9 (= _rc, W=222) with four 512-row pages instead of two 1024-row
// pages (page = pc[10:9]; same one-edge synchronous read, so identical cycles).
// Added vs the r9 leaf (moved out of the store top so the top holds no wide register mass):
//  - configuration CHAIN: out_addr/out_data are the leaf's own pin flops, forwarded to the next leaf of its chain
//    (neighbour-only, short fat link; no 256-bit broadcast); in_we is this leaf's strobe, delayed by the top to match
//    the leaf's chain depth;
//  - relay + output gate (r9 top's io_p/ctl_p + control_v gate): out_cal = cv_q ? relay : 0, cv_q = pin flop of in_cv
//    (the top's combinational all-stripe control_v of the calendar edge) -> identical outputs and D = 4;
//  - out_hz = {|cal[221:188], |cal[221:27]} registered with the calendar (the top's exact narrow-W check for programme
//    stripe 7 / IO stripe 2), out_b26 = calendar[26] (IO stripe 2: arithmetic start, as r7c io[470]).
module ot_hgi_sfu_store_stripe_leaf_r10_ref0 #(
 parameter integer AW=11
)(
 input wire clk,
 input wire rst_a,                 // stage-A synchronous reset relay from the top (active low)
 input wire in_we,                 // this leaf's write strobe (reset-qualified + chain-depth delayed in the top)
 input wire [AW-1:0] in_addr,      // configuration chain in
 input wire [255:0] in_data,
 output wire [AW-1:0] out_addr,    // configuration chain out (= this leaf's pin flops)
 output wire [255:0] out_data,
 input wire in_start_v,            // reset-qualified in the top
 input wire [AW-1:0] in_start_base,
 input wire in_legal,
 input wire [AW:0] in_span,
 input wire [15:0] in_loops,
 input wire in_loops_one,
 input wire in_cv,                 // all-stripe control_v of the calendar edge (top, combinational of leaf flops)
 output reg [221:0] out_cal,       // gated calendar field, 2 edges after the calendar register (r9 io_word timing)
 output wire out_v,out_active,out_done,out_fault,
 output wire [31:0] out_ord,
 output reg [1:0] out_hz,
 output wire out_b26
);
 // ---- leaf pin flops (pure: pin -> D)
 (* keep = "true", dont_touch = "true" *) reg rb;           // stage-B reset relay
 reg we_q,start_v_q,legal_q,loops_one_q,cv_q;
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] addr_q;
 (* keep = "true", dont_touch = "true" *) reg [255:0] data_q;
 reg [AW-1:0] start_base_q;
 reg [AW:0] span_q;
 reg [15:0] loops_q;
 always @(posedge clk)begin
  rb<=rst_a;we_q<=in_we;addr_q<=in_addr;data_q<=in_data;cv_q<=in_cv;
  start_v_q<=in_start_v;start_base_q<=in_start_base;legal_q<=in_legal;span_q<=in_span;loops_q<=in_loops;
  loops_one_q<=in_loops_one;
 end
 assign out_addr=addr_q;
 assign out_data=data_q;
 // ---- stripe body (ot_hgi_sfu_program_stripe_r9, W=222, four 512-row pages)
 localparam integer W=222, PCLO=234-AW;
 reg running,loops_one;
 reg [AW-1:0] pc,base;
 reg [AW:0] rem,span;
 reg [15:0] loops_left;
 reg [31:0] issued;
 reg valid0,valid1,last0,last1;
 reg [AW-1:0] pc0,pc1;
 reg [31:0] ord0,ord1,ordinal;
 reg [255:0] captured;
 reg [221:0] calendar;
 reg calendar_v,active,done,fault;
 wire busy=running|valid0|valid1;
 wire final_issue=(rem=={{AW{1'b0}},1'b1}) && loops_one;
 wire word_ok=captured[255:240]==16'hc7a1 && captured[233:PCLO]==pc1 &&
              captured[239:234]==0 && captured[PCLO-1:W]==0;
 wire [255:0] page_data[0:3];
 reg [1:0] read_page;
 always @(posedge clk)read_page<=pc[AW-1:9];
 wire [255:0] macro_data=page_data[read_page];
 for(genvar p=0;p<4;p=p+1)begin:g_page
  ot_sram_1r1w_512x256_m1_r2c2 u_program(
   .clk(clk),.r_ce_in(running && pc[AW-1:9]==p),.r_addr_in(pc[8:0]),.rd_out(page_data[p]),
   .w_ce_in(we_q && !busy && !start_v_q && addr_q[AW-1:9]==p),.w_addr_in(addr_q[8:0]),
   .wd_in(data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 end
 wire cal_ok=valid1 && word_ok;
 always @(posedge clk)begin
  captured<=macro_data;
  pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
  calendar<=cal_ok?captured[W-1:0]:{W{1'b0}};
  out_hz<={cal_ok && |captured[221:188],cal_ok && |captured[221:27]};
  ordinal<=ord1;
 end
 always @(posedge clk)
  if(!rb)begin
   running<=0;issued<=0;
   valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
   active<=0;done<=0;fault<=0;
  end else begin
   valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
   calendar_v<=valid1;
   active<=busy;done<=valid1 && last1;
   if(valid1 && !word_ok)fault<=1;
   if(we_q && (busy || start_v_q))fault<=1;
   if(start_v_q)begin
    if(busy || we_q || !legal_q)fault<=1;
    else begin
     running<=1;pc<=start_base_q;base<=start_base_q;rem<=span_q;span<=span_q;
     loops_left<=loops_q;loops_one<=loops_one_q;issued<=0;
    end
   end
   if(running)begin
    issued<=issued+1;
    if(rem=={{AW{1'b0}},1'b1})begin
     if(loops_one)running<=0;
     else begin pc<=base;rem<=span;loops_left<=loops_left-1;loops_one<=loops_left==16'd2; end
    end else begin pc<=pc+1;rem<=rem-1; end
   end
  end
 // ---- S band: relay + gated output registers (no reset: data registers, as the r9 top)
 reg [221:0] relay;
 always @(posedge clk)begin
  relay<=calendar;
  out_cal<=cv_q?relay:222'd0;
 end
 assign out_v=calendar_v;
 assign out_active=active;
 assign out_done=done;
 assign out_fault=fault;
 assign out_ord=ordinal;
 assign out_b26=calendar[26];
endmodule
`default_nettype wire
