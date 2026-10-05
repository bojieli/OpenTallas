`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_tc16: ot_gpu_tc16 (rtl/gpu/ot_gpu_tc_col.sv, L = 16) with its bubble gate moved off the multiplier's
// first stage, for 1.2 GHz SS: the original forces a bubble lane's registered weight to +0 in front of
// ot_hdc_bmul's decode/exponent-add stage; here the weight enters unchanged and the bubble raises the multiplier's
// zero flag instead (ot_hbm_accel_bmul `kill`).  Same result bits: a zero operand already gives y = +0 whatever
// the other operand is, and the fault output is gated by the bubble's own valid (v = 0), as in the original.
// Its 8x8 significand product is also cut as two 8x4 partial products (stage 2) summed by a kept prefix adder in
// stage 3 in front of the normalise select (the biased exponents precomputed): LATENCY 5 kept, bit-identical.
// Zero added cycles.
// ---------------------------------------------------------------------------
module ot_hbm_accel_tc_col #(
    parameter integer L    = 32,        // defaults = the hardened macro (Qwen SM: 32 lanes, 16-bit tag)
    parameter integer IL   = 8,
    parameter integer TAGW = 16,
    parameter integer ALAT = 7          // adder latency: the IL-slot ring needs ALAT <= IL - 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            first,
    input  wire            last,
    input  wire [TAGW-1:0] tag,
    input  wire [L*16-1:0] w,
    input  wire [L*16-1:0] x,
    output wire            ov,
    output wire [31:0]     y,
    output wire [TAGW-1:0] otag,
    output wire            fault
);
    localparam integer FB = IL - ALAT;          // ring = acc register + adder + (FB - 1) delay = IL
    reg            v_q, first_q, last_q;
    reg [L-1:0]    v_ql;                // per-lane copy of v for the bubble gate
    reg [TAGW-1:0] tag_q;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v_q <= 1'b0; first_q <= 1'b0; last_q <= 1'b0; v_ql <= {L{1'b0}}; end
        else begin v_q <= v; first_q <= v && first; last_q <= v && last; v_ql <= {L{v}}; end
    end
    always @(posedge clk) begin
        w_q <= w;
        x_q <= x;
        tag_q <= tag;
    end
    wire [5:0] fl;
    ot_hdc_vline #(.D(5)) u_f (.clk(clk), .rst_n(rst_n), .v(first_q), .vd(fl));
    // chunk end: the lane's final sum leaves the adder 5 (mul) + 5 (add) cycles after the input register
    localparam integer LL = 5 + ALAT;
    wire [LL:0] ll;
    ot_hdc_vline #(.D(LL)) u_l (.clk(clk), .rst_n(rst_n), .v(last_q), .vd(ll));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LL)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d));
    wire [5:0] vl;
    ot_hdc_vline #(.D(5)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vl));
    wire [L*32-1:0] sum;
    wire [L-1:0] lf;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        wire f0, f1;
        // a bubble multiplies by +0: the slot's sum holds
        ot_hbm_accel_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q), .kill(!v_ql[l]), .a({w_q[16*l +: 16], 16'd0}),
                           .b({x_q[16*l +: 16], 16'd0}), .y(prod), .fault(f0));
        always @(posedge clk) acc_q <= fl[4] ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(vl[5]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        assign lf[l] = f0 | f1;
    end endgenerate
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(L), .TAGW(TAGW), .ALAT(ALAT)) u_tree (.clk(clk), .rst_n(rst_n), .v(ll[LL]), .d(sum), .tag(tag_d),
                                             .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    reg lane_fault, ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lane_fault <= 1'b0; ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin
            lane_fault <= lane_fault | (|lf);
            ov_q <= t_ov;
            fault_q <= lane_fault | tf;
        end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q;
endmodule

// The V4.1 SM's BF16 column as a fixed macro (16 lanes, the 16-bit tag of a 4,096-row SM): a distinct
// module name so the V4.1 SM can place it beside the Qwen SM's 32-lane ot_gpu_tc_col macro.
module ot_hbm_accel_tc16 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          first,
    input  wire          last,
    input  wire [15:0]   tag,
    input  wire [255:0]  w,
    input  wire [255:0]  x,
    output wire          ov,
    output wire [31:0]   y,
    output wire [15:0]   otag,
    output wire          fault
);
    ot_hbm_accel_tc_col #(.L(16), .IL(8), .TAGW(16), .ALAT(7)) u (.clk(clk), .rst_n(rst_n), .v(v), .first(first), .last(last),
        .tag(tag), .w(w), .x(x), .ov(ov), .y(y), .otag(otag), .fault(fault));
endmodule

// BF16 x BF16 -> FP32 multiply, exact.  Two 8-bit significands give at most 16
// significant bits, so the binary32 product needs no rounding whenever it is
// normal, or subnormal by at most 7 bits of shift; there it is bit-identical
// to ot_fp32_mul_rne_pipe on the same operands (RN of an exact value is that
// value).  Operands arrive as binary32 words whose low 16 bits are ignored.
// A zero operand gives +0.  A product too small to be exact, an overflow or a
// nonfinite operand FAILS CLOSED through `fault` (and y = +0) -- the qualified
// pipe would round or refuse there.  LATENCY 5, like the FP32 pipe, so a
// lane's schedule does not depend on which multiplier it has.
module ot_hbm_accel_bmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire        kill,       // the lane's bubble: the product is +0 (as an operand of +0 gives)
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    // stage 1: decode; a subnormal significand is normalised by its top bit
    function automatic [17:0] dec;   // {sig[7:0], E[9:0] signed}
        input [7:0] e;
        input [6:0] m;
        integer i;
        reg [2:0] p;
        begin
            if (e != 0) dec = {1'b1, m, e - 10'sd127};
            else begin
                p = 0;
                for (i = 0; i < 7; i = i + 1) if (m[i]) p = i[2:0];
                dec = {({1'b0, m} << (7 - p)), $signed(-10'sd133) + $signed({7'd0, p})};
            end
        end
    endfunction
    wire [17:0] da = dec(a[30:23], a[22:16]);
    wire [17:0] db = dec(b[30:23], b[22:16]);
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [10:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= v;
    end
    always @(posedge clk) begin
        s1_s <= a[31] ^ b[31];
        s1_z <= kill || (a[30:16] == 15'd0) || (b[30:16] == 15'd0);
        s1_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_e <= $signed(da[9:0]) + $signed(db[9:0]);
    end
    // stage 2: the 8x8 product
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [11:0] s2_pl, s2_ph;            // the 8x8 product as two 8x4 partial products (summed in stage 3)
    reg signed [10:0] s2_e8, s2_e7;     // the exponent with both normalisation biases, precomputed
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf;
        s2_e8 <= s1_e + 11'sd128; s2_e7 <= s1_e + 11'sd127;
        s2_pl <= s1_a * s1_b[3:0];
        s2_ph <= s1_a * s1_b[7:4];
    end
    // stage 3: normalise (leading bit 15 or 14) and bias
    wire [15:0] s2_p;
    wire        s2_pc;
    ot_hdc_ksadd_k #(.W(16)) u_psum (.a({4'd0, s2_pl}), .b({s2_ph, 4'd0}), .cin(1'b0), .s(s2_p), .cout(s2_pc));
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf;
        if (s2_p[15]) begin s3_f <= {s2_p[14:0], 8'd0}; s3_be <= s2_e8; end
        else          begin s3_f <= {s2_p[13:0], 9'd0}; s3_be <= s2_e7; end
    end
    // stage 4: encode; a subnormal result shifts right by 1 - biased (<= 7)
    reg        s4_v, s4_bad;
    reg [31:0] s4_y;
    wire [23:0] sig24 = {1'b1, s3_f};
    wire [3:0]  sub_sh = 4'd1 - s3_be[3:0];
    wire [23:0] sub_v = sig24 >> sub_sh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= s3_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (s3_z && !s3_nf) s4_y <= 32'd0;
        else if (s3_nf || s3_be > 11'sd254 || s3_be < -11'sd6) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (s3_be >= 11'sd1) s4_y <= {s3_s, s3_be[7:0], s3_f};
        else s4_y <= {s3_s, 8'd0, sub_v[22:0]};
    end
    // stage 5: output register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
endmodule
