`timescale 1ns/1ps
// SIMULATION-ONLY stand-in for ot_hdc_fp32_add_lat_nr (rtl/hdc/ot_hdc_fp32_add_lat_nr.sv), the precedent of
// sim_nhb_fp_lat_dpi.sv applied to the _nr variant: the same ports and parameters, LAT register stages, II 1, the same
// function (IEEE binary32 RNE with gradual underflow via nhb_fadd: every zero result +0, a nonfinite operand -> err 1,
// an overflowing result -> err 2, y = 0 on error), and the same reset-visible output register (y / err / valid_out
// reset to 0; y / err follow the operands every cycle, as the real unit's unreset data stages do).
// el1011-q-kvd 2026-10-12: the hierarchical head (KVD_HSUB: 4 stacks x 4 heads x 16 ot_qkh_lane8, each with 8 + 7 real
// _nr adders) put ~3,800 bit-level adders into the HD 128 layer bench; Verilator reached 491 GiB RSS (VmHWM) and never
// finished (earlyoom SIGTERM at 336 GiB on ot-epyc1tb, 10-12 08:52).  build_qkvd_tb.sh HSUB=1 swaps this module in for
// the real one; rtl/test/nearhbm/run_nr_standin_equiv.sh checks it cycle-exact against the real unit.
// HSPLIT / HMUT / CUTS are accepted and ignored (HMUT is not used by the HSUB benches; KVD_HSMUT lives in the K tree).
// Never synthesised.
module ot_hdc_fp32_add_lat_nr #(
    parameter integer LAT = 3,
    parameter integer CUTS = -1,
    parameter integer HSPLIT = 1,
    parameter integer HMUT = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    import "DPI-C" function int unsigned nhb_fadd(input int unsigned a, input int unsigned b, output int err);
    reg [31:0] yl [0:LAT-2];
    reg [1:0]  el [0:LAT-2];
    reg [LAT-2:0] vl;
    int e;
    integer i;
    always @(posedge clk) begin
        yl[0] <= nhb_fadd(a, b, e);
        el[0] <= e[1:0];
        for (i = 1; i < LAT - 1; i = i + 1) begin yl[i] <= yl[i-1]; el[i] <= el[i-1]; end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vl <= 0; y <= 32'd0; err <= 2'd0; valid_out <= 1'b0; end
        else begin
            vl <= {vl, valid_in};
            y <= yl[LAT-2]; err <= el[LAT-2]; valid_out <= vl[LAT-2];
        end
    end
endmodule
