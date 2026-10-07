// die_top_lint: REAL-INTERFACE shells (port lists parsed from the RTL named in each header; interiors are
// the element owners' lint scope).

// rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv
module ot_hbm_accel_sm_v #(parameter ENABLE = 1, parameter SUB = 4, parameter LBS = 2, parameter LSB = 16, parameter NC = 8, parameter RMAX = 4096, parameter XD = 128, parameter MAX_OUT = 512, parameter DS = 3, parameter DG = 3, parameter DW = 4, parameter PIO = 2) (
    input wire [0:0] clk,
    input wire [0:0] rst_n,
    input wire [0:0] start,
    input wire [12:0] op_rows,
    input wire [15:0] op_c,
    input wire [7:0] op_g,
    input wire [0:0] op_gs,
    input wire [1:0] op_fmt,
    output wire [0:0] busy,
    input wire [0:0] d_valid,
    output wire [0:0] d_ready,
    input wire [31:0] d_base,
    input wire [23:0] d_lines,
    output wire [0:0] req_v,
    input wire [0:0] req_ready,
    output wire [31:0] req_addr,
    output wire [9:0] req_tag,
    input wire [0:0] rsp_v,
    input wire [9:0] rsp_tag,
    input wire [1087:0] rsp_data,
    input wire [0:0] xw_en,
    input wire [6:0] xw_addr,
    input wire [6:0] xw_grp,
    input wire [2047:0] xw_data,
    output wire [0:0] rv,
    output wire [11:0] rrow,
    output wire [255:0] rdata,
    output wire [0:0] fault,
    output wire [0:0] arrive,
    input wire [0:0] release_in,
    output wire [0:0] released);
    wire lint_in = ^{^clk, ^rst_n, ^start, ^op_rows, ^op_c, ^op_g, ^op_gs, ^op_fmt, ^d_valid, ^d_base, ^d_lines, ^req_ready, ^rsp_v, ^rsp_tag, ^rsp_data, ^xw_en, ^xw_addr, ^xw_grp, ^xw_data, ^release_in};
    reg [0:0] r_busy; always @(posedge clk) r_busy <= {1{lint_in}}; assign busy = r_busy;
    reg [0:0] r_d_ready; always @(posedge clk) r_d_ready <= {1{lint_in}}; assign d_ready = r_d_ready;
    reg [0:0] r_req_v; always @(posedge clk) r_req_v <= {1{lint_in}}; assign req_v = r_req_v;
    reg [31:0] r_req_addr; always @(posedge clk) r_req_addr <= {32{lint_in}}; assign req_addr = r_req_addr;
    reg [9:0] r_req_tag; always @(posedge clk) r_req_tag <= {10{lint_in}}; assign req_tag = r_req_tag;
    reg [0:0] r_rv; always @(posedge clk) r_rv <= {1{lint_in}}; assign rv = r_rv;
    reg [11:0] r_rrow; always @(posedge clk) r_rrow <= {12{lint_in}}; assign rrow = r_rrow;
    reg [255:0] r_rdata; always @(posedge clk) r_rdata <= {256{lint_in}}; assign rdata = r_rdata;
    reg [0:0] r_fault; always @(posedge clk) r_fault <= {1{lint_in}}; assign fault = r_fault;
    reg [0:0] r_arrive; always @(posedge clk) r_arrive <= {1{lint_in}}; assign arrive = r_arrive;
    reg [0:0] r_released; always @(posedge clk) r_released <= {1{lint_in}}; assign released = r_released;
endmodule
