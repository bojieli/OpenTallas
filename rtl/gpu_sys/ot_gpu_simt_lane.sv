`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_simt_lane: the lane-local integer / compare / convert datapath of one
// SIMT lane of ot_gpu_simt_sm (OTG-1, tools/gpu_sys/isa.py): XOR AND OR SHR
// SHL IADD ISUB IMUL UGT ULT, FCMPGT (IEEE >, NaN false, +0 == -0), F2I
// (truncate), CVTBF16 (cvt.rn.bf16.f32 as FP32 bits), CVTE4M3 (FP32 -> E4M3
// grid, RNE, saturating at 448, canonical +0: hdc_golden.to_fp8), MOVI,
// LANEID, MOVU.  Combinational; the SM registers the result.  Kept as its
// own (non-inlined) module so a simulator builds one lane, not NL copies.
// ---------------------------------------------------------------------------
module ot_gpu_simt_lane (
    input  wire [7:0]  op,
    input  wire [31:0] x,
    input  wire [31:0] y,
    input  wire [31:0] imm,
    input  wire [7:0]  lane,
    input  wire [31:0] uval,
    output reg  [31:0] z
);
    /*verilator no_inline_module*/
    function automatic [31:0] f_cmpgt(input [31:0] a, input [31:0] b);
        reg an, bn, az, bz;
        begin
            an = (a[30:23] == 8'hFF) && (a[22:0] != 0);
            bn = (b[30:23] == 8'hFF) && (b[22:0] != 0);
            az = (a[30:0] == 0); bz = (b[30:0] == 0);
            if (an || bn || (az && bz)) f_cmpgt = 32'd0;
            else if (!a[31] && b[31]) f_cmpgt = 32'd1;
            else if (a[31] && !b[31]) f_cmpgt = 32'd0;
            else if (!a[31]) f_cmpgt = {31'd0, a[30:0] > b[30:0]};
            else f_cmpgt = {31'd0, a[30:0] < b[30:0]};
        end
    endfunction
    function automatic [31:0] f_f2i(input [31:0] a);
        integer e; reg [62:0] m; reg [31:0] mag;
        begin
            e = a[30:23] - 127;
            m = {39'd0, 1'b1, a[22:0]};
            if (a[30:23] == 0 || e < 0) mag = 32'd0;
            else if (e >= 31) mag = 32'h7FFFFFFF;
            else if (e >= 23) mag = m[31:0] << (e - 23);
            else mag = m[31:0] >> (23 - e);
            f_f2i = a[31] ? (~mag + 32'd1) : mag;
        end
    endfunction
    function automatic [31:0] f_bf16(input [31:0] b);
        f_bf16 = (b + 32'h7FFF + {31'd0, b[16]}) & 32'hFFFF0000;
    endfunction
    function automatic [31:0] f_e4m3(input [31:0] a);       // hdc_golden.to_fp8, FP32 bits out
        integer e, qe, sh, p, ex; reg [23:0] sig; reg [23:0] k, rem, half; reg up; reg [31:0] r;
        begin
            if (a[30:23] == 0) f_e4m3 = 32'd0;
            else if (a[30:23] == 8'hFF || a[30:23] > 8'd135) f_e4m3 = {a[31], 31'h43E00000};
            else begin
                e = a[30:23] - 127;
                qe = ((e > -6) ? e : -6) - 3;
                sh = qe - e + 23;
                sig = {1'b1, a[22:0]};
                if (sh >= 25) k = 0;
                else begin
                    k = sig >> sh;
                    rem = sig & ((24'd1 << sh) - 24'd1);
                    half = 24'd1 << (sh - 1);
                    up = (rem > half) || ((rem == half) && k[0]);
                    k = k + {23'd0, up};
                end
                if (k == 0) f_e4m3 = 32'd0;
                else begin
                    p = 0;
                    for (integer i = 0; i < 5; i = i + 1) if (k[i]) p = i;
                    ex = qe + p;
                    r = {a[31], 8'(ex + 127), 23'((k << (23 - p)) & 24'h7FFFFF)};
                    if (ex > 8 || (ex == 8 && r[22:0] > 23'h600000)) r = {a[31], 31'h43E00000};
                    f_e4m3 = r;
                end
            end
        end
    endfunction
    always @* begin
        case (op)
            8'h03: z = x ^ y;
            8'h04: z = x & y;
            8'h05: z = x | y;
            8'h06: z = x >> y[4:0];
            8'h07: z = x << y[4:0];
            8'h08: z = x + y;
            8'h09: z = x - y;
            8'h12: z = x * y;
            8'h0A: z = {31'd0, x > y};
            8'h0B: z = {31'd0, x < y};
            8'h0C: z = f_cmpgt(x, y);
            8'h0D: z = f_f2i(x);
            8'h0E: z = f_bf16(x);
            8'h0F: z = f_e4m3(x);
            8'h20: z = imm;
            8'h21: z = {24'd0, lane};
            8'h22: z = uval;
            default: z = 32'd0;
        endcase
    end
endmodule

// ---------------------------------------------------------------------------
// ot_gpu_simt_fplane: one SIMT lane's FP32 add and multiply pipes (RNE, gradual
// underflow, canonical +0, fail closed to +0 with fault on a nonfinite operand
// or overflow), FLAT register stages each.  Non-inlined, as ot_gpu_simt_lane.
// ---------------------------------------------------------------------------
module ot_gpu_simt_fplane #(
    parameter integer FLAT = 7
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        add_v,
    input  wire        mul_v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] add_y,
    output wire        add_f,
    output wire [31:0] mul_y,
    output wire        mul_f
);
    /*verilator no_inline_module*/
    // FLAT = 5: the qualified pipes themselves (ot_hdc_fadd = rtl/proto/ot_fp32_add_rne_pipe, ot_hdc_fmul =
    // its proven cycle-equivalent ot_hdc_fp32_mul_pipe); FLAT = 7: the W11 1.2 GHz SS re-pipelined copies
    // (ot_gpu_fadd / ot_gpu_fmul), bit-identical.  Results are identical either way.
    if (FLAT == 5) begin : g_q
        ot_hdc_fadd u_add (.clk(clk), .rst_n(rst_n), .v(add_v), .a(a), .b(b), .y(add_y), .fault(add_f));
        ot_hdc_fmul u_mul (.clk(clk), .rst_n(rst_n), .v(mul_v), .a(a), .b(b), .y(mul_y), .fault(mul_f));
    end else begin : g_w11
        ot_gpu_fadd #(.LAT(FLAT)) u_add (.clk(clk), .rst_n(rst_n), .v(add_v), .a(a), .b(b), .y(add_y), .fault(add_f));
        ot_gpu_fmul #(.LAT(FLAT)) u_mul (.clk(clk), .rst_n(rst_n), .v(mul_v), .a(a), .b(b), .y(mul_y), .fault(mul_f));
    end
endmodule

