`timescale 1ns/1ps
// Real SRAM calendar source joined to the actual production SM arithmetic.
// Program loading/start are initialization. Normal operation has no ready port.
module ot_hbm_accel_smh_programmed(
 input wire clk,rst_n,
 input wire cfg_we,input wire [9:0] cfg_addr,input wire [255:0] cfg_data,
 input wire start_v,input wire [9:0] start_base,input wire [10:0] start_limit,
 input wire [15:0] start_loops,
 input wire [1098:0] packet,
 input wire xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
 output wire [42:0] expected_request,
 output wire rv,output wire [11:0] rrow,output wire [255:0] rdata,
 output wire fault,schedule_fault,program_fault,program_active,program_done
`ifdef OT_SMH_CG
 ,input wire cg_en
`endif
);
 wire [82:0] command;
 wire calendar_v;
 wire [31:0] ordinal;
 ot_smh_calendar_static #(.W(83)) u_calendar(
  .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .calendar(command),.calendar_v(calendar_v),.ordinal(ordinal),
  .active(program_active),.done(program_done),.fault(program_fault));
 // Invalid programme cycles are fixed idle slots. Availability never reschedules.
 ot_hbm_accel_smh_static u_sm(.clk(clk),.rst_n(rst_n),
  .command(calendar_v?command:83'd0),.packet(packet),.expected_request(expected_request),
  .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .rv(rv),.rrow(rrow),.rdata(rdata),.fault(fault),.schedule_fault(schedule_fault)
`ifdef OT_SMH_CG
  ,.cg_en(cg_en)
`endif
 );
endmodule
