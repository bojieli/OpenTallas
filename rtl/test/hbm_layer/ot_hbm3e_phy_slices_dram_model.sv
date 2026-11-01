`timescale 1ps/1fs
// OFFCHIP SIMULATION ONLY: adapt the three physical PHY slice interfaces to
// the existing 32-PC sparse DRAM model. All PCs retain their global native
// address identity. This adds no controller, on-die producer or cycle.
// The bound slices receive clk_hbm directly at the plan's 833-ps period.
// Preserve the inherited 23.524-ns external service assumption: ceil=29 edges.
// This is a behavioral boundary assumption, not physical signoff.
module ot_hbm_phy_slice_dram_adapter #(
    parameter integer PC_BASE=0, NPC=10,
    parameter string IMAGE_KEY="",
    parameter bit REQUIRE_INITIALIZED=1'b1,
    parameter integer CLOCK_PERIOD_PS=833,
    parameter integer READ_LATENCY=(23524+CLOCK_PERIOD_PS-1)/CLOCK_PERIOD_PS
)(
    input wire clk, rst_n,
    input wire [NPC-1:0] row_v, col_v, col_we,
    input wire [NPC*3-1:0] row_op,
    input wire [NPC*5-1:0] row_bank, col_bank, col_col,
    input wire [NPC*19-1:0] row_row,
    input wire [NPC*256-1:0] col_data,
    input wire [NPC*32-1:0] col_strb,
    output wire [NPC-1:0] dram_rvalid,
    output wire [NPC*256-1:0] dram_rdata
);
    wire [31:0] rv=32'(row_v)<<PC_BASE, cv=32'(col_v)<<PC_BASE, cw=32'(col_we)<<PC_BASE;
    wire [95:0] ro=96'(row_op)<<(PC_BASE*3);
    wire [159:0] rb=160'(row_bank)<<(PC_BASE*5), cb=160'(col_bank)<<(PC_BASE*5), cc=160'(col_col)<<(PC_BASE*5);
    wire [607:0] rr=608'(row_row)<<(PC_BASE*19);
    wire [8191:0] cd=8192'(col_data)<<(PC_BASE*256);
    wire [1023:0] cs=1024'(col_strb)<<(PC_BASE*32);
    wire [31:0] rvalid;
    wire [8191:0] rdata;
    initial if(PC_BASE<0 || NPC<1 || PC_BASE+NPC>32) $fatal(1,"HBM_MODEL_FAIL invalid slice");
    ot_hbm3e_phy_rc_e8p5 #(.IMAGE_KEY(IMAGE_KEY), .IMAGE_PARENT_PATH(1'b1), .REQUIRE_INITIALIZED(REQUIRE_INITIALIZED),.CLOCK_PERIOD_PS(CLOCK_PERIOD_PS),.READ_LATENCY(READ_LATENCY)) u_dram(
        .clk(clk),.rst_n(rst_n),.row_v(rv),.row_op(ro),.row_bank(rb),.row_row(rr),
        .col_v(cv),.col_we(cw),.col_bank(cb),.col_col(cc),.col_data(cd),.col_strb(cs),
        .dram_rvalid(rvalid),.dram_rdata(rdata));
    assign dram_rvalid=rvalid[PC_BASE+:NPC];
    assign dram_rdata=rdata[PC_BASE*256+:NPC*256];
endmodule

module ot_hbm3e_phy_rc_e8p5_pc0_9 #(parameter string IMAGE_KEY="", parameter bit REQUIRE_INITIALIZED=1'b1, parameter integer CLOCK_PERIOD_PS=833, parameter integer READ_LATENCY=(23524+CLOCK_PERIOD_PS-1)/CLOCK_PERIOD_PS)(
    input wire clk,rst_n,
    input wire [9:0] row_v,
    input wire [29:0] row_op,
    input wire [49:0] row_bank,
    input wire [189:0] row_row,
    input wire [9:0] col_v,
    input wire [9:0] col_we,
    input wire [49:0] col_bank,
    input wire [49:0] col_col,
    input wire [2559:0] col_data,
    input wire [319:0] col_strb,
    output wire [9:0] dram_rvalid,
    output wire [2559:0] dram_rdata
);
    ot_hbm_phy_slice_dram_adapter #(.PC_BASE(0),.NPC(10),.IMAGE_KEY(IMAGE_KEY),.REQUIRE_INITIALIZED(REQUIRE_INITIALIZED),.CLOCK_PERIOD_PS(CLOCK_PERIOD_PS),.READ_LATENCY(READ_LATENCY)) u_external(.*);
endmodule

module ot_hbm3e_phy_rc_e8p5_pc10_21 #(parameter string IMAGE_KEY="", parameter bit REQUIRE_INITIALIZED=1'b1, parameter integer CLOCK_PERIOD_PS=833, parameter integer READ_LATENCY=(23524+CLOCK_PERIOD_PS-1)/CLOCK_PERIOD_PS)(
    input wire clk,rst_n,
    input wire [11:0] row_v,
    input wire [35:0] row_op,
    input wire [59:0] row_bank,
    input wire [227:0] row_row,
    input wire [11:0] col_v,
    input wire [11:0] col_we,
    input wire [59:0] col_bank,
    input wire [59:0] col_col,
    input wire [3071:0] col_data,
    input wire [383:0] col_strb,
    output wire [11:0] dram_rvalid,
    output wire [3071:0] dram_rdata
);
    ot_hbm_phy_slice_dram_adapter #(.PC_BASE(10),.NPC(12),.IMAGE_KEY(IMAGE_KEY),.REQUIRE_INITIALIZED(REQUIRE_INITIALIZED),.CLOCK_PERIOD_PS(CLOCK_PERIOD_PS),.READ_LATENCY(READ_LATENCY)) u_external(.*);
endmodule

module ot_hbm3e_phy_rc_e8p5_pc22_31 #(parameter string IMAGE_KEY="", parameter bit REQUIRE_INITIALIZED=1'b1, parameter integer CLOCK_PERIOD_PS=833, parameter integer READ_LATENCY=(23524+CLOCK_PERIOD_PS-1)/CLOCK_PERIOD_PS)(
    input wire clk,rst_n,
    input wire [9:0] row_v,
    input wire [29:0] row_op,
    input wire [49:0] row_bank,
    input wire [189:0] row_row,
    input wire [9:0] col_v,
    input wire [9:0] col_we,
    input wire [49:0] col_bank,
    input wire [49:0] col_col,
    input wire [2559:0] col_data,
    input wire [319:0] col_strb,
    output wire [9:0] dram_rvalid,
    output wire [2559:0] dram_rdata
);
    ot_hbm_phy_slice_dram_adapter #(.PC_BASE(22),.NPC(10),.IMAGE_KEY(IMAGE_KEY),.REQUIRE_INITIALIZED(REQUIRE_INITIALIZED),.CLOCK_PERIOD_PS(CLOCK_PERIOD_PS),.READ_LATENCY(READ_LATENCY)) u_external(.*);
endmodule
