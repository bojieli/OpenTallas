`timescale 1ns/1ps
`default_nettype none
// Source-owned target126, exact protected44-bit operation plane. The host
// transport is the existing registered F20/F24/F28/F2C and C10 broadcast.
module ot_hbm_sm_activation_host_static(
 input wire clk_program,clk_control,
 input wire [1:0] clk_aq_core,clk_aq_delay,clk_aq_encode,
 input wire [3:0] clk_code,input wire rst_n,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,
 input wire [255:0] cfg_data,input wire desc_v,
 input wire [11:0] desc_base,input wire [12:0] desc_limit,
 input wire [15:0] desc_loops,input wire launch_v,
 output wire [135:0] rq,input wire [2055:0] rr,
 output wire xw_en,output wire [6:0] xw_addr,xw_grp,output wire [2047:0] xw_data,
 output wire xw_last,busy,done,retire_fault,fault,configured
);
 wire we,start_v,programme_active,target_fault,engine_fault;
 wire [9:0] address,base;wire [10:0] limit;wire [15:0] loops;wire [255:0] data;
 wire [31:0] ordinal;
 ot_static_program_target #(.TARGET(8'd126),.PCW(10)) target(
  .clk(clk_control),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
  .program_active(busy||programme_active),.program_cfg_we(we),.program_cfg_addr(address),.program_cfg_data(data),
  .program_start_v(start_v),.program_start_base(base),.program_start_limit(limit),.program_start_loops(loops),
  .configured(configured),.fault(target_fault));
 wire safe_done,engine_retire_fault;
 ot_hbm_sm_activation_programmed_static engine(.clk_program(clk_program),.clk_control(clk_control),
  .clk_aq_core(clk_aq_core),.clk_aq_delay(clk_aq_delay),.clk_aq_encode(clk_aq_encode),.clk_code(clk_code),.rst_n(rst_n),
  .cfg_we(we),.cfg_addr(address),.cfg_data(data),.start_v(start_v),.start_base(base),.start_limit(limit),.start_loops(loops),
  .rq(rq),.rr(rr),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),.xw_last(xw_last),
  .busy(busy),.done(safe_done),.retire_fault(engine_retire_fault),.fault(engine_fault),
  .programme_active(programme_active),.programme_ordinal(ordinal));
 assign fault=target_fault||engine_fault;
 assign done=safe_done&&!target_fault;
 assign retire_fault=engine_retire_fault||(safe_done&&target_fault);
endmodule
`default_nettype wire
