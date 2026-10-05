`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_host_bridge: host side of the GPU-organised HBM comparator system.
//
// The existing NVMe-style host interface rtl/host/ot_host_if.sv (reused
// unmodified, MODE 0) owns the submission/completion rings in host memory,
// the BAR registers, DMA and interrupts, and schedules one decode step at a
// time (eng_start {token, position} ... eng_done {next token}).  This bridge
// is the driver's per-GPU doorbell path: each step rings the doorbell of
// every die's command processor (ot_gpu_cmdproc), crossing clk_host ->
// clk_sm through ot_gpu_cdc_fifo, and returns eng_done when every die posted
// its completion (clk_sm -> clk_host).  eng_next_token is die 0's token; a
// die whose token differs, or any nonzero completion status, raises
// eng_fault.  eng_clr_req is acknowledged at once: the KV state belongs to
// the kernels (in HBM, addressed by position), the engine holds none.
//
// The loader port is the driver's module/graph load: a clk_host stream of
// {target, die, sm, addr, data} words crossed into clk_sm and delivered as
// command-memory writes (target 0) or SM instruction-memory writes (target 1).
// ENABLE = 0: inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_host_bridge #(
    parameter integer ENABLE = 0,
    parameter integer ND     = 2,
    parameter integer NSM    = 2,
    parameter integer CB     = 8,          // command-memory address bits
    parameter integer IMW    = 13          // SM instruction-memory address bits
) (
    input  wire                  clk_host,
    input  wire                  rst_host_n,
    input  wire                  clk_sm,
    input  wire                  rst_sm_n,
    // engine side of ot_host_if (clk_host)
    input  wire                  eng_start,
    input  wire [15:0]           eng_token,
    input  wire [15:0]           eng_pos,
    output reg                   eng_done,
    output reg  [15:0]           eng_next_token,
    output reg  [31:0]           eng_cycles,
    output reg                   eng_fault,
    input  wire                  eng_clr_req,
    output reg                   eng_clr_ack,
    // driver loader (clk_host)
    input  wire                  ld_v,
    output wire                  ld_rdy,
    input  wire                  ld_target,
    input  wire [3:0]            ld_die,
    input  wire [3:0]            ld_sm,
    input  wire [23:0]           ld_addr,
    input  wire [63:0]           ld_data,
    // per-die command processors (clk_sm)
    output wire [ND-1:0]         db_v,
    input  wire [ND-1:0]         db_rdy,
    output wire [ND*32-1:0]      db_tokpos,          // {pos, token} per die
    input  wire [ND-1:0]         cpl_v,
    output wire [ND-1:0]         cpl_rdy,
    input  wire [ND*52-1:0]      cpl_data,           // {cycles[31:0], status[3:0], token[15:0]} per die
    output reg  [ND-1:0]         cmd_we,
    output reg  [CB-1:0]         cmd_addr,
    output reg  [63:0]           cmd_wdata,
    output reg  [ND*NSM-1:0]     im_we,
    output reg  [IMW-1:0]        im_addr,
    output reg  [63:0]           im_data,
    output wire                  cdc_fault
);
generate if (ENABLE == 0) begin : g_off
    always @(posedge clk_host) begin
        eng_done <= 1'b0; eng_next_token <= 16'd0; eng_cycles <= 32'd0; eng_fault <= 1'b0; eng_clr_ack <= 1'b0;
    end
    always @(posedge clk_sm) begin
        cmd_we <= {ND{1'b0}}; cmd_addr <= {CB{1'b0}}; cmd_wdata <= 64'd0;
        im_we <= {ND*NSM{1'b0}}; im_addr <= {IMW{1'b0}}; im_data <= 64'd0;
    end
    assign ld_rdy = 1'b0; assign db_v = {ND{1'b0}}; assign db_tokpos = {ND*32{1'b0}};
    assign cpl_rdy = {ND{1'b0}}; assign cdc_fault = 1'b0;
end else begin : g_on
    // ---------------- doorbells: clk_host -> clk_sm, one FIFO per die
    wire [ND-1:0] db_in_rdy, db_ovf, cp_ovf, cp_out_v;
    wire [ND*52-1:0] cp_out_d;
    reg  [ND-1:0] got;
    reg  [15:0]   tok [0:ND-1];
    reg  [3:0]    sts [0:ND-1];
    reg  [31:0]   cyc [0:ND-1];
    genvar d;
    for (d = 0; d < ND; d = d + 1) begin : g_die
        ot_gpu_cdc_fifo #(.ENABLE(1), .W(32), .AW(2)) u_db (
            .wclk(clk_host), .wrst_n(rst_host_n), .in_v(eng_start), .in_rdy(db_in_rdy[d]), .in_d({eng_pos, eng_token}),
            .rclk(clk_sm), .rrst_n(rst_sm_n), .out_v(db_v[d]), .out_rdy(db_rdy[d]), .out_d(db_tokpos[d*32 +: 32]),
            .ovf_fault(db_ovf[d]));
        ot_gpu_cdc_fifo #(.ENABLE(1), .W(52), .AW(2)) u_cp (
            .wclk(clk_sm), .wrst_n(rst_sm_n), .in_v(cpl_v[d]), .in_rdy(cpl_rdy[d]), .in_d(cpl_data[d*52 +: 52]),
            .rclk(clk_host), .rrst_n(rst_host_n), .out_v(cp_out_v[d]), .out_rdy(!got[d]), .out_d(cp_out_d[d*52 +: 52]),
            .ovf_fault(cp_ovf[d]));
    end
    // ---------------- completion join (clk_host)
    reg busy_h, db_lost;
    integer i;
    reg all_ok;
    always @(posedge clk_host or negedge rst_host_n) begin
        if (!rst_host_n) begin
            got <= 0; busy_h <= 1'b0; eng_done <= 1'b0; eng_next_token <= 0; eng_cycles <= 0; eng_fault <= 1'b0;
            eng_clr_ack <= 1'b0; db_lost <= 1'b0;
            for (i = 0; i < ND; i = i + 1) begin tok[i] <= 0; sts[i] <= 0; cyc[i] <= 0; end
        end else begin
            eng_done <= 1'b0;
            eng_clr_ack <= eng_clr_req;
            if (eng_start) begin
                busy_h <= 1'b1;
                if (db_in_rdy != {ND{1'b1}}) db_lost <= 1'b1;        // a doorbell FIFO could not take the step
            end
            for (i = 0; i < ND; i = i + 1)
                if (cp_out_v[i] && !got[i]) begin
                    got[i] <= 1'b1; tok[i] <= cp_out_d[i*52 +: 16]; sts[i] <= cp_out_d[i*52+16 +: 4];
                    cyc[i] <= cp_out_d[i*52+20 +: 32];
                end
            if (busy_h && got == {ND{1'b1}}) begin
                all_ok = !db_lost;
                for (i = 0; i < ND; i = i + 1) if (sts[i] != 4'd0 || tok[i] != tok[0]) all_ok = 1'b0;
                eng_done <= 1'b1; eng_next_token <= tok[0]; eng_cycles <= cyc[0]; eng_fault <= !all_ok;
                got <= 0; busy_h <= 1'b0;
            end
        end
    end
    // ---------------- loader: clk_host -> clk_sm
    wire ld_ov; wire ld_out_v; wire [96:0] ld_out_d;
    ot_gpu_cdc_fifo #(.ENABLE(1), .W(97), .AW(3)) u_ld (
        .wclk(clk_host), .wrst_n(rst_host_n), .in_v(ld_v), .in_rdy(ld_rdy),
        .in_d({ld_target, ld_die, ld_sm, ld_addr, ld_data}),
        .rclk(clk_sm), .rrst_n(rst_sm_n), .out_v(ld_out_v), .out_rdy(1'b1), .out_d(ld_out_d), .ovf_fault(ld_ov));
    wire        lt  = ld_out_d[96];
    wire [3:0]  ldd = ld_out_d[95:92];
    wire [3:0]  lsm = ld_out_d[91:88];
    wire [23:0] la  = ld_out_d[87:64];
    always @(posedge clk_sm or negedge rst_sm_n) begin
        if (!rst_sm_n) begin
            cmd_we <= 0; cmd_addr <= 0; cmd_wdata <= 0; im_we <= 0; im_addr <= 0; im_data <= 0;
        end else begin
            cmd_we <= 0; im_we <= 0;
            if (ld_out_v) begin
                if (!lt) begin cmd_we[ldd] <= 1'b1; cmd_addr <= la[CB-1:0]; cmd_wdata <= ld_out_d[63:0]; end
                else begin im_we[ldd * NSM + lsm] <= 1'b1; im_addr <= la[IMW-1:0]; im_data <= ld_out_d[63:0]; end
            end
        end
    end
    assign cdc_fault = (|db_ovf) | (|cp_ovf) | ld_ov;
end endgenerate
endmodule
