`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery lever "router_act" (default-off, new file): the router's sqrt(softplus) on LANES parallel
// lanes, placed at the router field's output root (1.2 GHz domain), instead of one element a cycle through
// lane 0's scalar side pipe of the stream unit (0.9 GHz, behind the hub network).
//
//   r = sqrt(softplus(x)) of tools/hdc_golden_v41 (exp, t + 2, t / den, Horner in u^2, 2 u p, max(x,0) + l,
//   sqrt), every rounding unchanged: each lane is ot_hdc_v41x_softplus #(LM, LA) itself (IMPL 0; with the
//   1.2 GHz FILE SWAP rtl/hdc/ot_hdc_fastfp_lat_f12.sv the multiplier is ot_hdc_fp32_mul_f12_l5 and the adder
//   ot_hdc_fp32_add_f12_l4, bit- and cycle-identical to the serial build) or the short unit
//   ot_hdc_v41x_softplus_s #(PCUT 1) of rtl/hdc/v41x/ot_hdc_v41x_spshort.sv (IMPL 1, the same bits, exhaustive
//   2^32 evidence in results/rtl/w11_softplus_short.json).
//
//   A beat carries LANES scores (in_x lane l = row b*LANES + l of the die's rows).  IN_STAGES / OUT_STAGES
//   register stages are the wire from the field's output root to the lanes and from the lanes to the
//   collective endpoint (ceil(L / 504 um) at 1.2 GHz SS).  Latency in_valid -> out_valid:
//   IN_STAGES + DEPTH + OUT_STAGES (+1 output register).
// ---------------------------------------------------------------------------
module ot_dsrom_su_spsqrt #(
    parameter integer LANES      = 24,
    parameter integer IMPL       = 0,      // 0: ot_hdc_v41x_softplus #(LM, LA); 1: ot_hdc_v41x_softplus_s #(PCUT 1)
    parameter integer LM         = 5,
    parameter integer LA         = 4,
    parameter integer IN_STAGES  = 2,
    parameter integer OUT_STAGES = 2
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                in_valid,
    input  wire [LANES*32-1:0] in_x,
    output wire                out_valid,
    output wire [LANES*32-1:0] out_r,
    output wire                out_fault
);
    // -- input wire stages ----------------------------------------------------------------
    wire                v_l;
    wire [LANES*32-1:0] x_l;
    generate if (IN_STAGES > 0) begin : g_in
        reg                v_s [1:IN_STAGES];
        reg [LANES*32-1:0] x_s [1:IN_STAGES];
        integer i;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) for (i = 1; i <= IN_STAGES; i = i + 1) v_s[i] <= 1'b0;
            else begin v_s[1] <= in_valid; for (i = 2; i <= IN_STAGES; i = i + 1) v_s[i] <= v_s[i-1]; end
        end
        always @(posedge clk) begin
            x_s[1] <= in_x;
            for (i = 2; i <= IN_STAGES; i = i + 1) x_s[i] <= x_s[i-1];
        end
        assign v_l = v_s[IN_STAGES];
        assign x_l = x_s[IN_STAGES];
    end else begin : g_in0
        assign v_l = in_valid;
        assign x_l = in_x;
    end endgenerate

    // -- lanes ----------------------------------------------------------------------------
    wire [LANES*32-1:0] r_l;
    wire [LANES-1:0]    vo_l, f_l;
    genvar l;
    generate
        for (l = 0; l < LANES; l = l + 1) begin : g_lane
            if (IMPL == 0) begin : g_ser
                ot_hdc_v41x_softplus #(.LM(LM), .LA(LA)) u (.clk(clk), .rst_n(rst_n), .v(v_l), .x(x_l[32*l +: 32]),
                    .sp(), .r(r_l[32*l +: 32]), .vo(vo_l[l]), .fault(f_l[l]));
            end else begin : g_short
                ot_hdc_v41x_softplus_s #(.PCUT(1)) u (.clk(clk), .rst_n(rst_n), .v(v_l), .x(x_l[32*l +: 32]),
                    .sp(), .r(r_l[32*l +: 32]), .vo(vo_l[l]), .fault(f_l[l]));
            end
        end
    endgenerate

    // -- output register + wire stages to the collective endpoint ---------------------------
    reg                vq, fq;
    reg [LANES*32-1:0] rq;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vq <= 1'b0; fq <= 1'b0; end
        else begin vq <= vo_l[0]; fq <= vo_l[0] && (|f_l); end
    end
    always @(posedge clk) rq <= r_l;
    generate if (OUT_STAGES > 0) begin : g_out
        reg                v_s [1:OUT_STAGES];
        reg                f_s [1:OUT_STAGES];
        reg [LANES*32-1:0] r_s [1:OUT_STAGES];
        integer i;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) for (i = 1; i <= OUT_STAGES; i = i + 1) begin v_s[i] <= 1'b0; f_s[i] <= 1'b0; end
            else begin
                v_s[1] <= vq; f_s[1] <= fq;
                for (i = 2; i <= OUT_STAGES; i = i + 1) begin v_s[i] <= v_s[i-1]; f_s[i] <= f_s[i-1]; end
            end
        end
        always @(posedge clk) begin
            r_s[1] <= rq;
            for (i = 2; i <= OUT_STAGES; i = i + 1) r_s[i] <= r_s[i-1];
        end
        assign out_valid = v_s[OUT_STAGES];
        assign out_fault = f_s[OUT_STAGES];
        assign out_r = r_s[OUT_STAGES];
    end else begin : g_out0
        assign out_valid = vq;
        assign out_fault = fq;
        assign out_r = rq;
    end endgenerate
endmodule

// One lane, registered in and out: the minimum component for the 1.2 GHz screen / route.
module ot_dsrom_su_spsqrt_lane #(parameter integer IMPL = 0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    input  wire [31:0] in_x,
    output wire        out_valid,
    output wire [31:0] out_r,
    output wire        out_fault
);
    ot_dsrom_su_spsqrt #(.LANES(1), .IMPL(IMPL), .IN_STAGES(1), .OUT_STAGES(0)) u (.clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_x(in_x), .out_valid(out_valid), .out_r(out_r), .out_fault(out_fault));
endmodule

// Parameter-free tops for the screen (the runner's --param path is avoided): IMPL 0 / IMPL 1 lanes.
module ot_dsrom_su_spsqrt_lane0 (
    input wire clk, input wire rst_n, input wire in_valid, input wire [31:0] in_x,
    output wire out_valid, output wire [31:0] out_r, output wire out_fault
);
    ot_dsrom_su_spsqrt_lane #(.IMPL(0)) u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_x(in_x),
        .out_valid(out_valid), .out_r(out_r), .out_fault(out_fault));
endmodule

module ot_dsrom_su_spsqrt_lane1 (
    input wire clk, input wire rst_n, input wire in_valid, input wire [31:0] in_x,
    output wire out_valid, output wire [31:0] out_r, output wire out_fault
);
    ot_dsrom_su_spsqrt_lane #(.IMPL(1)) u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_x(in_x),
        .out_valid(out_valid), .out_r(out_r), .out_fault(out_fault));
endmodule
