`timescale 1ns/1ps
`default_nettype none
// One real protected programme SRAM, actual quantizers/fragment SRAM and original
// SM XWRITE pins. Configuration is the declared decoded host-target boundary.
module ot_hbm_sm_activation_programmed_static #(parameter integer MUT=0)(
 input wire clk_program,clk_control,
 input wire [1:0] clk_aq_core,clk_aq_delay,clk_aq_encode,
 input wire [3:0] clk_code,input wire rst_n,
 input wire cfg_we,input wire [9:0] cfg_addr,input wire [255:0] cfg_data,
 input wire start_v,input wire [9:0] start_base,input wire [10:0] start_limit,
 input wire [15:0] start_loops,
 output wire [135:0] rq,input wire [2055:0] rr,
 output wire xw_en,output wire [6:0] xw_addr,xw_grp,output wire [2047:0] xw_data,
 output wire xw_last,busy,done,retire_fault,fault,
 output wire programme_active,output wire [31:0] programme_ordinal
);
 wire [43:0] control;wire control_v,programme_done,programme_fault;
 wire core_done,core_fault,core_retire_fault;
 ot_vms_calendar_static #(.W(44)) programme(.clk(clk_program),.rst_n(rst_n),
  .cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),
  .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .calendar(control),.calendar_v(control_v),.ordinal(programme_ordinal),
  .active(programme_active),.done(programme_done),.fault(programme_fault));
 ot_hbm_sm_activation_static #(.MUT(MUT)) engine(.clk_control(clk_control),
  .clk_aq_core(clk_aq_core),.clk_aq_delay(clk_aq_delay),.clk_aq_encode(clk_aq_encode),
  .clk_code(clk_code),.rst_n(rst_n),.epoch_start(start_v),.control_v(control_v),.control(control),
  .rq(rq),.rr(rr),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .xw_last(xw_last),.busy(busy),.done(core_done),.retire_fault(core_retire_fault),.fault(core_fault));
 assign fault=programme_fault||core_fault;
 assign done=core_done&&!programme_fault;
 assign retire_fault=core_retire_fault||(core_done&&programme_fault);
endmodule
`default_nettype wire
