`timescale 1ns/1ps
`default_nettype none
// SFU programme store (H-SU 2026-10-16, die slot sfus_<q> 1020 x 1412 um beside sfucore_<q>).
// Physical split of ot_hgi_sfu_scheduled_engine: BOTH fixed programme calendars (IO calendar 3 stripes,
// arithmetic calendar 8 stripes = all 22 ot_sram_1r1w_1024x256 SRAMs) leave the SFU core slot, which keeps
// the 16 lanes, the 80 operand SRAMs and the VM bridge (ot_hgi_sfu_core_split).
// Owner rule 10-15 19:50: every input and every output is registered at this tile's pins.
// Timing (static, compiler-visible): host cfg/start sampled at n, calendars run exactly as in the unsplit engine
// from n+1, every output registered once more -> io word and compiler_control leave at +2 vs the unsplit engine;
// the core registers them at its pins (+1): the whole SFU invocation is a uniform +3 stream edges after io_start_v.
// arithmetic start stays internal (IO word bit 470 starts the arithmetic calendar on the same edge as before).
// No queue, ready or credit. FAULT (sticky, registered): either calendar's stripe-disagreement fault.
module ot_hgi_sfu_programme_store #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output reg programme_active,programme_done,
 output reg [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output reg io_active,io_done,
 output reg [31:0] io_ordinal,
 output reg [470:0] io_word,
 output reg [1741:0] compiler_control,
 output reg fault
);
 // ---- input pin registers
 reg r_cfg_we,r_io_cfg_we,r_io_start_v;
 reg [2:0] r_cfg_stripe;
 reg [1:0] r_io_cfg_stripe;
 reg [AW-1:0] r_cfg_addr,r_io_cfg_addr,r_start_base,r_io_start_base;
 reg [255:0] r_cfg_data,r_io_cfg_data;
 reg [AW:0] r_start_limit,r_io_start_limit;
 reg [15:0] r_start_loops,r_io_start_loops;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin r_cfg_we<=0;r_io_cfg_we<=0;r_io_start_v<=0;end
  else begin r_cfg_we<=cfg_we;r_io_cfg_we<=io_cfg_we;r_io_start_v<=io_start_v;end
 always @(posedge clk)begin
  r_cfg_stripe<=cfg_stripe;r_cfg_addr<=cfg_addr;r_cfg_data<=cfg_data;
  r_start_base<=start_base;r_start_limit<=start_limit;r_start_loops<=start_loops;
  r_io_cfg_stripe<=io_cfg_stripe;r_io_cfg_addr<=io_cfg_addr;r_io_cfg_data<=io_cfg_data;
  r_io_start_base<=io_start_base;r_io_start_limit<=io_start_limit;r_io_start_loops<=io_start_loops;
 end
 // ---- the two unchanged calendars (exactly as in ot_hgi_sfu_scheduled_engine / ot_hgi_sfu_programmed_engine)
 wire [470:0] io;
 wire [1741:0] control;
 wire io_fault,program_fault,w_io_active,w_io_done,w_p_active,w_p_done;
 wire [31:0] w_io_ord,w_p_ord;
 ot_hgi_sfu_io_calendar_static #(.PAGE_AW(PAGE_AW)) u_io(
  .clk(clk),.rst_n(rst_n),.cfg_we(r_io_cfg_we),.cfg_stripe(r_io_cfg_stripe),.cfg_addr(r_io_cfg_addr),.cfg_data(r_io_cfg_data),
  .start_v(r_io_start_v),.start_base(r_io_start_base),.start_limit(r_io_start_limit),.start_loops(r_io_start_loops),
  .compiler_control(io),.control_v(),.ordinal(w_io_ord),.active(w_io_active),.done(w_io_done),.fault(io_fault));
 ot_hgi_sfu_calendar_paged_static #(.PAGE_AW(PAGE_AW)) u_programme(
  .clk(clk),.rst_n(rst_n),.cfg_we(r_cfg_we),.cfg_stripe(r_cfg_stripe),.cfg_addr(r_cfg_addr),.cfg_data(r_cfg_data),
  .start_v(io[470]),.start_base(r_start_base),.start_limit(r_start_limit),.start_loops(r_start_loops),
  .compiler_control(control),.control_v(),.ordinal(w_p_ord),
  .active(w_p_active),.done(w_p_done),.fault(program_fault));
 // ---- output pin registers
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   io_word<=0;compiler_control<=0;io_active<=0;io_done<=0;io_ordinal<=0;
   programme_active<=0;programme_done<=0;programme_ordinal<=0;fault<=0;
  end else begin
`ifdef OT_SFU_PSTORE_MUT_FLIP
   compiler_control<=control^1742'd1;          // bench negative control: one control bit corrupted on the crossing
`else
   compiler_control<=control;
`endif
   io_word<=io;io_active<=w_io_active;io_done<=w_io_done;io_ordinal<=w_io_ord;
   programme_active<=w_p_active;programme_done<=w_p_done;programme_ordinal<=w_p_ord;
   if(io_fault||program_fault)fault<=1;
  end
endmodule
`default_nettype wire
