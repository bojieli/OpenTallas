`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_store_leaf_r9 (SFU-STORE-9 2026-10-17): ONE hardened bank leaf of the SFU programme store, replicated
// 4x by ot_hgi_sfu_programme_store_r9 (3 x NS=3 = 6 SRAMs, 1 x NS=2 = 4 SRAMs; 22 SRAMs = 11 stripes = the r7c
// address map: programme stripes 0-2 / 3-5 / 6-7, IO stripes 0-2).
// Why (r7c4 CLOSED but native FAIL capture 222.0 ps on cfg_we): one control pin broadcast to 22 SRAMs over a 1 mm
// tile on one clock root. Here every leaf input pin goes straight into a plain flop (no reset AND, no logic) and the
// leaf owns its registered copy of cfg we/addr/data, its launch arguments and its synchronous reset relays, so no
// control net crosses more than one ~430 x 250 um leaf. Leaf = own clock root (~2.2k sinks).
// Function per stripe is ot_hgi_sfu_program_stripe_rc with its input registers moved to the leaf pins (the top
// precomputes launch legality / span / loops==1 and folds reset qualification in front of the leaf pins) and W fixed
// at 222 (the top applies the narrower W=188/27 zero check exactly; see the top). Ordinal agreement: the leaf
// outputs its first stripe's ordinal and a registered per-stripe mismatch bit (same edge as the ordinal register).
module ot_hgi_sfu_store_leaf_r9 #(
 parameter integer NS=3, PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,
 input wire rst_a,                 // stage-A synchronous reset relay from the top (active low)
 input wire [NS-1:0] in_we,        // per-stripe write strobe (decoded + reset-qualified in the top)
 input wire [AW-1:0] in_addr,
 input wire [255:0] in_data,
 input wire in_start_v,            // reset-qualified in the top
 input wire [AW-1:0] in_start_base,
 input wire in_legal,
 input wire [AW:0] in_span,
 input wire [15:0] in_loops,
 input wire in_loops_one,
 output wire [222*NS-1:0] out_cal,
 output wire [NS-1:0] out_v,out_active,out_done,out_fault,
 output wire [31:0] out_ord,       // ordinal of the leaf's first stripe
 output reg [NS-1:1] out_mm        // stripe s ordinal != first stripe ordinal (registered with the ordinals)
);
 // ---- leaf pin flops (pure: pin -> D)
 (* keep = "true", dont_touch = "true" *) reg [NS-1:0] rb;   // stage-B reset relay, one per stripe
 reg [NS-1:0] we_q;
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] addr_q;
 (* keep = "true", dont_touch = "true" *) reg [255:0] data_q;
 reg start_v_q,legal_q,loops_one_q;
 reg [AW-1:0] start_base_q;
 reg [AW:0] span_q;
 reg [15:0] loops_q;
 always @(posedge clk)begin
  rb<={NS{rst_a}};we_q<=in_we;addr_q<=in_addr;data_q<=in_data;
  start_v_q<=in_start_v;start_base_q<=in_start_base;legal_q<=in_legal;span_q<=in_span;loops_q<=in_loops;
  loops_one_q<=in_loops_one;
 end
 wire [31:0] ord1[0:NS-1];
 wire [31:0] ord[0:NS-1];
 for(genvar s=0;s<NS;s=s+1)begin:g_stripe
  ot_hgi_sfu_program_stripe_r9 #(.PAGE_AW(PAGE_AW)) u_program(
   .clk(clk),.rst_n(rb[s]),.cfg_we_q(we_q[s]),.cfg_addr_q(addr_q),.cfg_data_q(data_q),
   .start_v_q(start_v_q),.start_base_q(start_base_q),.legal_q(legal_q),.span_q(span_q),.start_loops_q(loops_q),
   .loops_one_q(loops_one_q),
   .calendar(out_cal[222*s+:222]),.calendar_v(out_v[s]),.ordinal(ord[s]),.ord1(ord1[s]),
   .active(out_active[s]),.done(out_done[s]),.fault(out_fault[s]));
 end
 assign out_ord=ord[0];
 for(genvar s=1;s<NS;s=s+1)begin:g_mm
  always @(posedge clk)out_mm[s]<=ord1[s]!=ord1[0];
 end
endmodule

// Stripe body = ot_hgi_sfu_program_stripe_rc (W=222) with the launch / config registers supplied by the leaf.
module ot_hgi_sfu_program_stripe_r9 #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire cfg_we_q,
 input wire [AW-1:0] cfg_addr_q,
 input wire [255:0] cfg_data_q,
 input wire start_v_q,
 input wire [AW-1:0] start_base_q,
 input wire legal_q,
 input wire [AW:0] span_q,
 input wire [15:0] start_loops_q,
 input wire loops_one_q,
 output reg [221:0] calendar,
 output reg calendar_v,
 output reg [31:0] ordinal,
 output wire [31:0] ord1,
 output reg active,done,fault
);
 localparam integer W=222, PCLO=234-AW, PAGES=1<<PAGE_AW;
 initial if(W>PCLO-1 || PAGE_AW!=1)$fatal(1,"SFU r9 leaf geometry invalid");
 reg running,loops_one;
 reg [AW-1:0] pc,base;
 reg [AW:0] rem,span;
 reg [15:0] loops_left;
 reg [31:0] issued;
 reg valid0,valid1,last0,last1;
 reg [AW-1:0] pc0,pc1;
 reg [31:0] ord0,ord1_r;
 reg [255:0] captured;
 wire [255:0] macro_data;
 wire busy=running|valid0|valid1;
 wire final_issue=(rem=={{AW{1'b0}},1'b1}) && loops_one;
 wire word_ok=captured[255:240]==16'hc7a1 && captured[233:PCLO]==pc1 &&
              captured[239:234]==0 && captured[PCLO-1:W]==0;
 wire [255:0] page_data[0:PAGES-1];
 reg [PAGE_AW-1:0] read_page;
 always @(posedge clk)read_page<=pc[AW-1:10];
 assign macro_data=page_data[read_page];
 assign ord1=ord1_r;
 for(genvar p=0;p<PAGES;p=p+1)begin:g_page
  ot_sram_1r1w_1024x256_m2_r2c2 u_program(
   .clk(clk),.r_ce_in(running && pc[AW-1:10]==p),.r_addr_in(pc[9:0]),.rd_out(page_data[p]),
   .w_ce_in(cfg_we_q && !busy && !start_v_q && cfg_addr_q[AW-1:10]==p),.w_addr_in(cfg_addr_q[9:0]),
   .wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 end
 always @(posedge clk)begin
  captured<=macro_data;
  pc0<=pc;pc1<=pc0;ord0<=issued;ord1_r<=ord0;
  calendar<=valid1 && word_ok?captured[W-1:0]:{W{1'b0}};
  ordinal<=ord1_r;
 end
 always @(posedge clk)
  if(!rst_n)begin
   running<=0;issued<=0;
   valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
   active<=0;done<=0;fault<=0;
  end else begin
   valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
   calendar_v<=valid1;
   active<=busy;done<=valid1 && last1;
   if(valid1 && !word_ok)fault<=1;
   if(cfg_we_q && (busy || start_v_q))fault<=1;
   if(start_v_q)begin
    if(busy || cfg_we_q || !legal_q)fault<=1;
    else begin
     running<=1;pc<=start_base_q;base<=start_base_q;rem<=span_q;span<=span_q;
     loops_left<=start_loops_q;loops_one<=loops_one_q;issued<=0;
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
endmodule

// The two hardened variants (distinct masters for the cluster binder).
// r9c (HBM-SFU9 10-17): the configuration data port is split by PHYSICAL destination side, so each bit has one pin
// face in the column leaf (all-R0 SRAM stack: A edge carries wd_in[0:135], B edge wd_in[136:255]). Bit-identical:
// u_leaf.in_data = {in_data_hi,in_data_lo}.
module ot_hgi_sfu_store_leaf3_r9 #(parameter integer PAGE_AW=1, AW=10+PAGE_AW)(
 input wire clk,rst_a,
 input wire [2:0] in_we,
 input wire [AW-1:0] in_addr,
 input wire [135:0] in_data_lo,   // r9c: data bits 0..135 = SRAM wd_in on the macro A edge (leaf W face)
 input wire [119:0] in_data_hi,   // r9c: data bits 136..255 = SRAM wd_in on the macro B edge (leaf E face)
 input wire in_start_v,
 input wire [AW-1:0] in_start_base,
 input wire in_legal,
 input wire [AW:0] in_span,
 input wire [15:0] in_loops,
 input wire in_loops_one,
 output wire [221:0] out_cal0,out_cal1,out_cal2,      // one port per stripe: one W-face pin range per macro row
 output wire [2:0] out_v,out_active,out_done,out_fault,
 output wire [31:0] out_ord,
 output wire [2:1] out_mm
);
 ot_hgi_sfu_store_leaf_r9 #(.NS(3),.PAGE_AW(PAGE_AW)) u_leaf(.clk(clk),.rst_a(rst_a),.in_we(in_we),.in_addr(in_addr),
  .in_data({in_data_hi,in_data_lo}),.in_start_v(in_start_v),.in_start_base(in_start_base),.in_legal(in_legal),.in_span(in_span),
  .in_loops(in_loops),.in_loops_one(in_loops_one),.out_cal({out_cal2,out_cal1,out_cal0}),.out_v(out_v),.out_active(out_active),
  .out_done(out_done),.out_fault(out_fault),.out_ord(out_ord),.out_mm(out_mm));
endmodule

module ot_hgi_sfu_store_leaf2_r9 #(parameter integer PAGE_AW=1, AW=10+PAGE_AW)(
 input wire clk,rst_a,
 input wire [1:0] in_we,
 input wire [AW-1:0] in_addr,
 input wire [135:0] in_data_lo,   // r9c: data bits 0..135 = SRAM wd_in on the macro A edge (leaf W face)
 input wire [119:0] in_data_hi,   // r9c: data bits 136..255 = SRAM wd_in on the macro B edge (leaf E face)
 input wire in_start_v,
 input wire [AW-1:0] in_start_base,
 input wire in_legal,
 input wire [AW:0] in_span,
 input wire [15:0] in_loops,
 input wire in_loops_one,
 output wire [221:0] out_cal0,out_cal1,
 output wire [1:0] out_v,out_active,out_done,out_fault,
 output wire [31:0] out_ord,
 output wire out_mm            // scalar: stripe 1 ordinal != stripe 0 ordinal
);
 ot_hgi_sfu_store_leaf_r9 #(.NS(2),.PAGE_AW(PAGE_AW)) u_leaf(.clk(clk),.rst_a(rst_a),.in_we(in_we),.in_addr(in_addr),
  .in_data({in_data_hi,in_data_lo}),.in_start_v(in_start_v),.in_start_base(in_start_base),.in_legal(in_legal),.in_span(in_span),
  .in_loops(in_loops),.in_loops_one(in_loops_one),.out_cal({out_cal1,out_cal0}),.out_v(out_v),.out_active(out_active),
  .out_done(out_done),.out_fault(out_fault),.out_ord(out_ord),.out_mm(out_mm));
endmodule
`default_nettype wire
