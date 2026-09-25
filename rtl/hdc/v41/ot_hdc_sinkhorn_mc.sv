`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The latency-optimised Sinkhorn unit (ot_hdc_sinkhorn: one whole
// normalisation per unit clock) inside the V4.1 decode core, as the multicycle
// path its header prescribes: the unit is clocked once every STEP_CYC core
// cycles.  STEP_CYC = ceil(step_ns * f_core): the unit routes at 151.9 MHz on
// ASAP7 (results/physical_abi3/asap7/hdc/v41/ot_hdc_sinkhorn), 6.58 ns a step,
// so 7 core cycles at a 1 GHz core -- tools/decode_critical_path.py's figure.
//
// Interface in the core-clock domain (the divided clock is derived from it, so
// every crossing is synchronous):
//   req   level, held by the caller until `busy` rises (the unit accepts on
//         its next edge while idle); in_e must stay stable meanwhile;
//   done  a single core-cycle pulse when the unit's out_valid rises; y and
//         fault hold until the next request.
// ---------------------------------------------------------------------------
module ot_hdc_sinkhorn_mc #(
    parameter integer STEP_CYC = 7,
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         req,
    input  wire [511:0] in_e,
    output wire         busy,
    output wire         done,
    output wire [511:0] y,
    output wire         fault
);
    localparam integer CW = (STEP_CYC > 1) ? $clog2(STEP_CYC) : 1;
    reg [CW-1:0] cnt;
    reg          sclk;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cnt <= 0; sclk <= 1'b0; end
        else begin
            cnt <= (cnt == STEP_CYC - 1) ? {CW{1'b0}} : cnt + 1'b1;
            //: one rising edge of the unit clock per STEP_CYC core cycles
            sclk <= (cnt == STEP_CYC - 1);
        end
    end
    wire in_ready, ov, ubusy, uf;
    ot_hdc_sinkhorn #(.ITERS(ITERS), .EPS(EPS)) u (.clk(sclk), .rst_n(rst_n), .in_valid(req), .in_ready(in_ready),
        .in_e(in_e), .out_valid(ov), .y(y), .fault(uf), .busy(ubusy));
    reg ov_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov_q <= 1'b0; else ov_q <= ov;
    end
    assign done = ov && !ov_q;
    assign fault = uf;
    assign busy = ubusy || ov;
endmodule
