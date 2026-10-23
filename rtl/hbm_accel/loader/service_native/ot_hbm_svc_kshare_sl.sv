`timescale 1ns/1ps
`default_nettype none
// STEWARD-HBM/COLL-KS 2026-10-21: bit-sliced storage for ot_hbm_svc_vm_kshare_splitstrap (r4).  The r3 mapped netlist
// failed the pre-gate native census (301 drivers > 32 loads, max 1088): every wide register (2-entry pin skids 277..340 b,
// the H9b response ring 277 b, the 279 b x 8 fill CDC FIFO, the 105/36 b command FIFOs) had ONE enable / select / pointer
// net for its whole width.  Here each wide store is split into <= SW-bit slices, each slice owning private (kept) copies
// of the control state, so every pointer / enable / select drives <= ~32 pins.  All slices see the same clock, reset
// release edge and handshake, so their private state stays in lockstep; public cycle behaviour is unchanged.
// A shared handshake bit enters each slice through ONE kept 2-input AND leaf (keep_hierarchy, so synthesis cannot
// re-spread it over the slice logic); the AND's second input is a per-slice dynamic signal (the slice's own state or
// its reset leaf), never a constant, so it is a real load boundary.

// One kept AND: a load boundary for a shared handshake bit (one pin per slice).
(* keep_hierarchy = "yes" *)
module ot_hbm_svc_ks_and2(input wire a,b,output wire y);
 assign y=a&b;
endmodule

// Two-entry pin skid, exact ot_hbm_svc_pin_skid2 behaviour (head/tail), sliced: NS = ceil(WIDTH/SW) slices, each with
// its own head_valid/tail_valid copy; push_s = in_v & !tail_s, pop_s = out_r & head_s.  in_r / out_v leave from slice 0
// (in_r also low during reset).
// SW 14 (r4b census: 16-bit slices put 33 pins on the tail enable).  rst_n: NR = ceil(NS/13) reset leaves (each <= 26
// flop clears + in_r), slice s on leaf s/13.
module ot_hbm_svc_skid2_sl #(parameter integer WIDTH=1,SW=14,NS=(WIDTH+SW-1)/SW,NR=(NS+12)/13)(
 input wire clk,input wire [NR-1:0]rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire [WIDTH-1:0]out_data
);
 wire [NS-1:0]hv,tv;
 // in_r is low while the skid is held in reset (the leaf releases +2 edges after the pin reset flop), so no push is
 // offered into a clearing slice; afterwards it is !tail_valid exactly as ot_hbm_svc_pin_skid2.
 assign in_r=rst_n[0]&&!tv[0];assign out_v=hv[0];
 genvar s;
 generate for(s=0;s<NS;s=s+1)begin:g_s
  localparam integer B=(WIDTH-s*SW<SW)?WIDTH-s*SW:SW;
  (* keep="true" *) reg head_valid,tail_valid;
  reg [B-1:0]head_data,tail_data;
  wire push,pop;
  (* keep="true" *) ot_hbm_svc_ks_and2 u_push(.a(in_v),.b(!tail_valid),.y(push));
  (* keep="true" *) ot_hbm_svc_ks_and2 u_pop(.a(out_r),.b(head_valid),.y(pop));
  assign hv[s]=head_valid;assign tv[s]=tail_valid;
  assign out_data[s*SW+:B]=head_data;
  // valid bits: async clear from the slice leaf; data registers are unreset and outside the reset block (a reset-
  // qualified data enable would hang every data bit on the leaf: r4a census 56..58 pins per leaf)
  always @(posedge clk or negedge rst_n[s/13])begin
   if(!rst_n[s/13])begin head_valid<=0;tail_valid<=0;end
   else case({push,pop})
    2'b10:if(!head_valid)head_valid<=1;else tail_valid<=1;
    2'b01:begin head_valid<=tail_valid;tail_valid<=0;end
    2'b11:begin head_valid<=1;tail_valid<=0;end
    default:;
   endcase
  end
  always @(posedge clk)begin
   if(push&&(pop||!head_valid))head_data<=in_data[s*SW+:B];
   else if(pop&&tail_valid)head_data<=tail_data;
   if(push&&!pop&&head_valid)tail_data<=in_data[s*SW+:B];
  end
 end endgenerate
endmodule

// DEPTH-entry response ring, exact ot_hbm_svc_ring_h9b_ff behaviour (synchronous reset, write at wp on in_v, read at rp,
// cnt / cnt_next / fault from one control copy), sliced: each SW-bit (12: r4a census 16-bit rp / write decode 33..35) slice owns kept wp/rp copies; the shared in_v / pop
// reach a slice through one kept AND with the slice's reset leaf (reset-gated: while a leaf is low the slice pointers
// clear anyway and the unreset entries are don't-care).  rst_n[0] = control; slice s on leaf 1+s/4 (<= 4 slices x 6 pins).
// PINREG (STEWARD-HBMd/PINREG-KS 2026-10-23): DEPTH may be 2..4 (entry e3 exists only for DEPTH 4), and GRP > 0 routes
// the shared in_v / pop through ceil(NS/GRP) kept group ANDs (leaf of the group's first slice) before the per-slice ANDs,
// so a ring with > ~28 slices keeps in_v / pop <= 32 loads.  GRP 0 / DEPTH <= 3 = the r5a structure unchanged.
module ot_hbm_svc_ring_sl #(parameter integer WIDTH=1,DEPTH=3,SW=12,NS=(WIDTH+SW-1)/SW,NR=1+(NS+3)/4,GRP=0)(
 input wire clk,input wire [NR-1:0]rst_n,
 input wire in_v,input wire [WIDTH-1:0]in_data,
 output wire out_v,input wire pop,output wire [WIDTH-1:0]out_data,
 output reg [2:0]cnt,output wire [2:0]cnt_next,output reg fault
);
 assign out_v=cnt!=3'd0;
 assign cnt_next=cnt+{2'b0,in_v}-{2'b0,pop};
 always @(posedge clk)
  if(!rst_n[0])begin cnt<=0;fault<=0;end
  else begin
   cnt<=cnt_next;
   if((in_v&&!pop&&cnt==DEPTH)||(pop&&cnt==0)) fault<=1'b1;
  end
 localparam integer GD=(GRP>0)?GRP:1,NGR=(GRP>0)?(NS+GD-1)/GD:1;
 wire [NGR-1:0]gin,gpop;
 genvar s,g;
 generate if(GRP>0)begin:g_grp
  for(g=0;g<NGR;g=g+1)begin:g_g
   (* keep="true" *) ot_hbm_svc_ks_and2 u_gw(.a(in_v),.b(rst_n[1+(g*GD)/4]),.y(gin[g]));
   (* keep="true" *) ot_hbm_svc_ks_and2 u_gp(.a(pop),.b(rst_n[1+(g*GD)/4]),.y(gpop[g]));
  end
 end else begin:g_nogrp
  assign gin[0]=in_v;assign gpop[0]=pop;
 end
 for(s=0;s<NS;s=s+1)begin:g_s
  localparam integer B=(WIDTH-s*SW<SW)?WIDTH-s*SW:SW;
  localparam integer GI=(GRP>0)?s/GD:0;
  wire rl=rst_n[1+s/4];
  (* keep="true" *) reg [1:0]wp,rp;
  reg [B-1:0]e0,e1,e2;
  wire wv,pv;
  (* keep="true" *) ot_hbm_svc_ks_and2 u_wv(.a(gin[GI]),.b(rl),.y(wv));
  (* keep="true" *) ot_hbm_svc_ks_and2 u_pv(.a(gpop[GI]),.b(rl),.y(pv));
  always @(posedge clk)begin
   if(wv&&wp==2'd0)e0<=in_data[s*SW+:B];
   if(wv&&wp==2'd1)e1<=in_data[s*SW+:B];
   if(wv&&wp==2'd2&&DEPTH>2)e2<=in_data[s*SW+:B];
  end
  always @(posedge clk)
   if(!rl)begin wp<=0;rp<=0;end
   else begin
    if(wv)wp<=(wp==DEPTH-1)?2'd0:wp+2'd1;
    if(pv)rp<=(rp==DEPTH-1)?2'd0:rp+2'd1;
   end
  if(DEPTH>3)begin:g_d4
   reg [B-1:0]e3;
   always @(posedge clk)if(wv&&wp==2'd3)e3<=in_data[s*SW+:B];
   assign out_data[s*SW+:B]=(rp==2'd0)?e0:(rp==2'd1)?e1:(rp==2'd2)?e2:e3;
  end else begin:g_d3
   assign out_data[s*SW+:B]=(rp==2'd0)?e0:(rp==2'd1)?e1:e2;
  end
 end endgenerate
endmodule

// Lockstep bit-sliced async FIFO: NS instances of the reviewed ot_hbm_svc_async_fifo (byte-identical module, only WIDTH
// differs, <= SW bits each so its read mux / write decode stay <= ~28 pins), own pointers / synchronisers / reset syncs
// per instance.  wr_ready = &slice wr_ready and rd_valid = &slice rd_valid, and a slice is written / popped only when ALL
// are ready / valid, so every instance fires on the same edges and all heads hold the same word while rd_valid (a slice
// whose synchroniser resolves one edge later only delays the AND).  wr_overflow / rd_underflow are sticky over the
// AND-ed handshake (as the primitive's own flags).  Each slice has its OWN reset leaf per domain (wr_rst_n[k],
// rd_rst_n[k]): distinct both_reset nets, so synthesis cannot merge the per-slice ot_reset_sync pipes into one
// high-fanout reset; the leaf also gates the slice's fire AND (fires happen only long after release).  The shared fire
// reaches the slices through NG = ceil(NS/16) kept group ANDs, then one kept AND per slice.
module ot_hbm_svc_afifo_sl #(parameter integer WIDTH=32,DEPTH=8,SW=7,NS=(WIDTH+SW-1)/SW)(
 input wire wr_clk,input wire [NS-1:0]wr_rst_n,input wire wr_valid,output wire wr_ready,
 input wire [WIDTH-1:0]wr_data,output reg wr_overflow,
 input wire rd_clk,input wire [NS-1:0]rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0]rd_data,output reg rd_underflow
);
 localparam integer NG=(NS+15)/16;
 wire [NS-1:0]s_wr_ready,s_rd_valid,s_ov,s_un,s_wv,s_rr;
 wire [NG-1:0]g_wv,g_rr;
 assign wr_ready=&s_wr_ready;assign rd_valid=&s_rd_valid;
 wire wfire=wr_valid&&wr_ready,rfire=rd_ready&&rd_valid;
 always @(posedge wr_clk or negedge wr_rst_n[0])
  if(!wr_rst_n[0])wr_overflow<=0;else if((wr_valid&&!wr_ready)||(|s_ov))wr_overflow<=1;
 always @(posedge rd_clk or negedge rd_rst_n[0])
  if(!rd_rst_n[0])rd_underflow<=0;else if((rd_ready&&!rd_valid)||(|s_un))rd_underflow<=1;
 genvar g,k;
 generate for(g=0;g<NG;g=g+1)begin:g_g
  (* keep="true" *) ot_hbm_svc_ks_and2 u_gw(.a(wfire),.b(wr_rst_n[g*16]),.y(g_wv[g]));
  (* keep="true" *) ot_hbm_svc_ks_and2 u_gr(.a(rfire),.b(rd_rst_n[g*16]),.y(g_rr[g]));
 end
 for(k=0;k<NS;k=k+1)begin:g_s
  localparam integer B=(WIDTH-k*SW<SW)?WIDTH-k*SW:SW;
  (* keep="true" *) ot_hbm_svc_ks_and2 u_wv(.a(g_wv[k/16]),.b(wr_rst_n[k]),.y(s_wv[k]));
  (* keep="true" *) ot_hbm_svc_ks_and2 u_rr(.a(g_rr[k/16]),.b(rd_rst_n[k]),.y(s_rr[k]));
  ot_hbm_svc_async_fifo #(.WIDTH(B),.DEPTH(DEPTH)) u_f(
   .wr_clk(wr_clk),.wr_rst_n(wr_rst_n[k]),.wr_valid(s_wv[k]),.wr_ready(s_wr_ready[k]),.wr_data(wr_data[k*SW+:B]),
   .wr_overflow(s_ov[k]),
   .rd_clk(rd_clk),.rd_rst_n(rd_rst_n[k]),.rd_valid(s_rd_valid[k]),.rd_ready(s_rr[k]),.rd_data(rd_data[k*SW+:B]),
   .rd_underflow(s_un[k]));
 end endgenerate
endmodule
`default_nettype wire
