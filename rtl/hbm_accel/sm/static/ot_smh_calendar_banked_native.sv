`timescale 1ns/1ps
`default_nettype none
// Explicit actual clock roots; each cross-region path has a normal one-edge contract.
// This composition is functional source, NOT physical adoption or a slot grant.
module ot_smh_calendar_banked_regions #(parameter integer W=135,AW=11,XW=46,MUT=0)(
 input wire clk_core,clk_bank0,clk_bank1,
 input wire rst_n,cfg_we,input wire[AW-1:0]cfg_addr,input wire[255:0]cfg_data,
 input wire start_v,input wire[AW-1:0]start_base,input wire[AW:0]start_limit,
 input wire[15:0]start_loops,input wire[XW-1:0]start_ctx,
 output wire[W-1:0]calendar,output wire[XW-1:0]calendar_ctx,output wire[15:0]calendar_iter,
 output wire calendar_lastit,calendar_v,output wire[31:0]ordinal,output wire active,done,fault
);
 localparam integer TW=62+XW,QW=(W+15)/16;
 wire cfg0_we,cfg1_we;wire[9:0]bank_cfg_addr;wire[255:0]bank_cfg_data;
 wire[TW-1:0]request0,request1,token0,token1;wire[W-1:0]row0,row1;wire[QW-1:0]ok0,ok1;
 ot_smh_calendar_banked_central #(.W(W),.AW(AW),.XW(XW),.MUT(MUT)) u_central(
  .clk(clk_core),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),.calendar(calendar),.calendar_ctx(calendar_ctx),.calendar_iter(calendar_iter),.calendar_lastit(calendar_lastit),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault),
  .cfg0_we(cfg0_we),.cfg1_we(cfg1_we),.bank_cfg_addr(bank_cfg_addr),.bank_cfg_data(bank_cfg_data),
  .request0(request0),.request1(request1),.row0(row0),.row1(row1),.ok0(ok0),.ok1(ok1),.token0(token0),.token1(token1));
 ot_smh_calendar_bank_leaf #(.W(W),.XW(XW),.BANK(0),.MUT(MUT)) u_bank0(
  .clk(clk_bank0),.rst_n(rst_n),.cfg_we(cfg0_we),.cfg_addr(bank_cfg_addr),.cfg_data(bank_cfg_data),
  .read_token(request0),.row(row0),.word_ok(ok0),.row_token(token0));
 ot_smh_calendar_bank_leaf #(.W(W),.XW(XW),.BANK(1),.MUT(MUT)) u_bank1(
  .clk(clk_bank1),.rst_n(rst_n),.cfg_we(cfg1_we),.cfg_addr(bank_cfg_addr),.cfg_data(bank_cfg_data),
  .read_token(request1),.row(row1),.word_ok(ok1),.row_token(token1));
endmodule

// Explicit opt-in old-port compatibility wrapper; regional root ports exist above.
module ot_smh_calendar_banked_native #(parameter integer W=135,AW=11,XW=46,MUT=0)(
 input wire clk,
 input wire rst_n,cfg_we,input wire[AW-1:0]cfg_addr,input wire[255:0]cfg_data,
 input wire start_v,input wire[AW-1:0]start_base,input wire[AW:0]start_limit,
 input wire[15:0]start_loops,input wire[XW-1:0]start_ctx,
 output wire[W-1:0]calendar,output wire[XW-1:0]calendar_ctx,output wire[15:0]calendar_iter,
 output wire calendar_lastit,calendar_v,output wire[31:0]ordinal,output wire active,done,fault
);
 wire[W-1:0]c;wire[XW-1:0]x;wire[15:0]it;wire li,v;wire[31:0]ord;wire a,d,f;
 ot_smh_calendar_banked_regions #(.W(W),.AW(AW),.XW(XW),.MUT(MUT)) u_regions(
 .clk_core(clk),.clk_bank0(clk),.clk_bank1(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),
 .calendar(c),.calendar_ctx(x),.calendar_iter(it),.calendar_lastit(li),.calendar_v(v),.ordinal(ord),.active(a),.done(d),.fault(f));
 generate if(MUT==3)begin:g_wrong_delay
  reg[W+XW+16+1+1+32+3-1:0]bad_q;
  always @(posedge clk)bad_q<={c,x,it,li,v,ord,a,d,f};
  assign {calendar,calendar_ctx,calendar_iter,calendar_lastit,calendar_v,ordinal,active,done,fault}=bad_q;
 end else begin:g_normal
  assign {calendar,calendar_ctx,calendar_iter,calendar_lastit,calendar_v,ordinal,active,done,fault}={c,x,it,li,v,ord,a,d,f};
 end endgenerate
endmodule
`default_nettype wire
