`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_programme_store_r6 (H-SU 2026-10-16; successor of ot_hgi_sfu_programme_store, which is unchanged).
// r5 hbm_sfu_programme_store_1016-r5-eface-cb302f3ff routed NEEDS_RTL TT -187.68 (input->reg: rst_n recovery into
// ~3,300 async-reset flops incl. the 2,213 io_word/compiler_control output registers spread over 447 x 1024 um, TT clock
// insertion ~852 ps) / reg2reg -80.0 (stripe calendar -> W-face output register across the 447 um tile) / FF -50.1.
// r6: (1) rst_n drives only ot_rst_relay (regions: IO calendar, arithmetic calendar, store regs; release +3 edges);
// (2) io_word / compiler_control output registers carry NO reset (pure data: the calendars present 0 whenever not
// valid, and the clock runs during reset, so they read 0 before release exactly as before); (3) ONE relay register
// stage between the calendars and the W-face output registers (placed mid-tile): io_word and compiler_control leave
// at +3 vs the unsplit engine (was +2); with the core pin register the SFU invocation is a uniform +4 stream edges
// after io_start_v (was +3): the compiler issues io_start_v one edge earlier (static constant; no queue/credit).
// Status outputs (active/done/ordinal/fault) keep their +2 (no relay). Bench: tb_hgi_sfu_split_equiv SFU_PSTORE_R6
// (D = 4). Host contract: configuration writes start >= 3 edges after rst_n release (ot_rst_relay RELEASE_CYCLES).
// OT_SFU_PSTORE_MUT_FLIP as before.
module ot_hgi_sfu_programme_store_r6 #(
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
 wire [2:0] rr;   // 0 IO calendar, 1 arithmetic calendar, 2 store pin/status regs
 ot_rst_relay #(.REGIONS(3),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 always @(posedge clk or negedge rr[2])
  if(!rr[2])begin r_cfg_we<=0;r_io_cfg_we<=0;r_io_start_v<=0;end
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
  .clk(clk),.rst_n(rr[0]),.cfg_we(r_io_cfg_we),.cfg_stripe(r_io_cfg_stripe),.cfg_addr(r_io_cfg_addr),.cfg_data(r_io_cfg_data),
  .start_v(r_io_start_v),.start_base(r_io_start_base),.start_limit(r_io_start_limit),.start_loops(r_io_start_loops),
  .compiler_control(io),.control_v(),.ordinal(w_io_ord),.active(w_io_active),.done(w_io_done),.fault(io_fault));
 ot_hgi_sfu_calendar_paged_static #(.PAGE_AW(PAGE_AW)) u_programme(
  .clk(clk),.rst_n(rr[1]),.cfg_we(r_cfg_we),.cfg_stripe(r_cfg_stripe),.cfg_addr(r_cfg_addr),.cfg_data(r_cfg_data),
  .start_v(io[470]),.start_base(r_start_base),.start_limit(r_start_limit),.start_loops(r_start_loops),
  .compiler_control(control),.control_v(),.ordinal(w_p_ord),
  .active(w_p_active),.done(w_p_done),.fault(program_fault));
 // ---- relay stage (mid-tile) + output pin registers: data registers without reset
 reg [470:0] io_p;
 reg [1741:0] ctl_p;
 always @(posedge clk)begin
  io_p<=io;
`ifdef OT_SFU_PSTORE_MUT_FLIP
  ctl_p<=control^1742'd1;          // bench negative control: one control bit corrupted on the crossing
`else
  ctl_p<=control;
`endif
  io_word<=io_p;compiler_control<=ctl_p;
 end
 always @(posedge clk or negedge rr[2])
  if(!rr[2])begin
   io_active<=0;io_done<=0;io_ordinal<=0;programme_active<=0;programme_done<=0;programme_ordinal<=0;fault<=0;
  end else begin
   io_active<=w_io_active;io_done<=w_io_done;io_ordinal<=w_io_ord;
   programme_active<=w_p_active;programme_done<=w_p_done;programme_ordinal<=w_p_ord;
   if(io_fault||program_fault)fault<=1;
  end
endmodule
`default_nettype wire
