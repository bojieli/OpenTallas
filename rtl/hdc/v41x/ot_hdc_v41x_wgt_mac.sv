`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// BF16/FP32-weight MAC lane of the V4.1x weight engine (block `wgt`, the "ME"):
// the product of tools/hdc_golden_v41.matvec_c / dots under R-ARITH,
// mul(w, to_bf16(x)) -- one IEEE binary32 multiply, RNE, gradual underflow,
// a zero operand giving +0 -- by the qualified ot_hdc_qmul with the
// activation's low 16 bits tied to zero (x is BF16: synthesis keeps a 24 x 8
// significand product).  The chunk's adds are the chain
// (ot_hdc_v41x_wgt_chain): a chunk of 8 = a chain of 8 MACs.
//
// OPERAND WORD (34 bits per lane): {fmt[1:0], data[31:0]}, the format carried
// per word so one row may mix formats (attention's p.v sums window rows and
// compressed rows in one block):
//   fmt 0: data is the weight's binary32 bits -- a BF16 weight (lm_head, the
//          router gate, the compressor, the index projection) as {bf16, 16'h0}
//          (the ROM bank is 16 bits wide, the read network appends the zeros);
//          an FP32 weight as stored.
//   fmt 1: FP8 E4M3 code data[7:0] with its UE8M0 scale byte data[15:8] -- wo_a
//          (one scale per 32 x 32 block, broadcast by the read network) and, in
//          the pooled tile, a window KV row (one scale per 32 elements).  The
//          lane dequantises EXACTLY (a 4-bit significand times a power of two:
//          the golden's to_bf16 of it is the identity); a NaN code or a value
//          outside the binary32 normal range fails closed.
//   fmt 2 (POOL only): FP4 E2M1 code data[3:0] with its E4M3 scale data[15:8] --
//          a compressed KV row (qdq_fp4_e4m3, one scale per 16).  The value is
//          a 2-bit times a 4-bit significand: a 6-bit exact product, normal in
//          binary32 for every code pair, so the golden's to_bf16 is again the
//          identity.  A NaN scale code fails closed.
// M positions (MTP lane multiplier, or attention heads) share the operand word.
// LATENCY 5: P0 input register, D decode register, the 3-cycle multiply.
// z forces +0.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_mlane #(
    parameter integer M = 1,
    parameter integer POOL = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            z,
    input  wire [33:0]     w,
    input  wire [M*16-1:0] x,
    output wire            ov,
    output wire [M*32-1:0] y,
    output wire [M-1:0]    f
);
    reg            p0_v, p0_z;
    reg [33:0]     p0_w;
    reg [M*16-1:0] p0_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p0_v <= 1'b0;
        else p0_v <= v;
    end
    always @(posedge clk) begin
        p0_z <= z;
        p0_w <= w;
        p0_x <= x;
    end
    wire [1:0] fmt = p0_w[33:32];

    // -- D, fmt 1: E4M3 x 2^(s-127) -> binary32 ---------------------------------------------------
    wire [7:0] c = p0_w[7:0];
    wire [7:0] s = p0_w[15:8];
    wire [3:0] ce = c[6:3];
    wire [2:0] cm = c[2:0];
    //: a subnormal code m/8 * 2^-6 normalised: leading one of m at position p, value 1.r * 2^(p-9)
    wire [1:0] lp = cm[2] ? 2'd2 : (cm[1] ? 2'd1 : 2'd0);
    wire [2:0] sm = cm[2] ? {cm[1:0], 1'b0} : (cm[1] ? {cm[0], 2'b00} : 3'b000);
    //: biased binary32 exponent: normal e + s - 7, subnormal p + s - 9
    wire signed [10:0] eb = (ce != 4'd0) ? $signed({3'd0, s}) + $signed({7'd0, ce}) - 11'sd7
                                         : $signed({3'd0, s}) + $signed({9'd0, lp}) - 11'sd9;
    wire [2:0]  mt = (ce != 4'd0) ? cm : sm;
    wire        cz = (c[6:0] == 7'd0);
    wire        cn = (c[6:0] == 7'h7F);
    wire        rng = (eb < 11'sd1) || (eb > 11'sd254);
    wire [31:0] w8 = cz ? 32'd0 : {c[7], eb[7:0], mt, 20'd0};
    wire        f8bad = !cz && (cn || rng);

    // -- D, fmt 2: E2M1 x E4M3 scale -> binary32 (POOL) ---------------------------------------------
    wire [31:0] w4;
    wire        f4bad;
    generate
        if (POOL != 0) begin : g_fp4
            wire [3:0] q  = p0_w[3:0];
            wire [1:0] qe = q[2:1];
            wire [1:0] q2 = {(qe != 2'd0), q[0]};                 // 2-bit significand
            wire [1:0] qf = (qe == 2'd0) ? 2'd1 : qe;             // value q2 * 2^(qf - 2)
            wire [3:0] se = s[6:3];
            wire [3:0] s4 = {(se != 4'd0), s[2:0]};               // value s4 * 2^(sf - 10)
            wire [3:0] sf = (se == 4'd0) ? 4'd1 : se;
            wire [5:0] pp = q2 * s4;                              // exact, <= 6 bits
            reg  [2:0] lz;
            reg  [5:0] pn;
            always @(*) begin
                casez (pp)
                    6'b1?????: begin lz = 3'd0; pn = pp; end
                    6'b01????: begin lz = 3'd1; pn = pp << 1; end
                    6'b001???: begin lz = 3'd2; pn = pp << 2; end
                    6'b0001??: begin lz = 3'd3; pn = pp << 3; end
                    6'b00001?: begin lz = 3'd4; pn = pp << 4; end
                    default:   begin lz = 3'd5; pn = pp << 5; end
                endcase
            end
            //: leading one at bit 5 - lz: value 1.f * 2^(5 - lz + qf - 2 + sf - 10); biased + 127
            wire [8:0] e4 = 9'd120 + {7'd0, qf} + {5'd0, sf} - {6'd0, lz};
            assign w4 = (pp == 6'd0) ? 32'd0 : {q[3] ^ s[7], e4[7:0], pn[4:0], 18'd0};
            assign f4bad = (s[6:0] == 7'h7F);
        end else begin : g_nofp4
            assign w4 = 32'd0;
            assign f4bad = 1'b1;                                  // the format is not built: fail closed
        end
    endgenerate

    reg            d_v;
    reg [31:0]     d_w;
    reg            d_f;
    reg [M*16-1:0] d_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) d_v <= 1'b0;
        else d_v <= p0_v;
    end
    always @(posedge clk) begin
        d_w <= p0_z ? 32'd0 : (fmt == 2'd1 ? w8 : (fmt == 2'd2 ? w4 : p0_w[31:0]));
        d_f <= !p0_z && ((fmt == 2'd1 && f8bad) || (fmt == 2'd2 && f4bad) || fmt == 2'd3);
        d_x <= p0_x;
    end

    wire [M-1:0] mf;
    wire         df;
    genvar p;
    generate
        for (p = 0; p < M; p = p + 1) begin : g_p
            ot_hdc_qmul u_mul (.clk(clk), .rst_n(rst_n), .v(d_v), .a(d_w), .b({d_x[16*p +: 16], 16'h0000}),
                               .y(y[32*p +: 32]), .fault(mf[p]));
        end
    endgenerate
    ot_hdc_delay #(.W(1), .D(3), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(d_v), .q(ov));
    ot_hdc_delay #(.W(1), .D(3)) u_f (.clk(clk), .rst_n(rst_n), .d(d_f), .q(df));
    assign f = mf | {M{df & ov}};
endmodule

// Eight MAC lanes and their chain: one chunk of 8 contiguous K terms.  Lane c's operands
// are presented at t + SK(c) (SK = 0,0,3,..,18); the chunk sum leaves at t + 26.
module ot_hdc_v41x_wgt_mchunk #(
    parameter integer M = 1,
    parameter integer POOL = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        v,
    input  wire [7:0]        z,
    input  wire [8*34-1:0]   w,
    input  wire [8*M*16-1:0] x,
    output wire              ov,
    output wire [M*32-1:0]   s,
    output wire [M-1:0]      sf
);
    wire [7:0]        pv;
    wire [8*M*32-1:0] py;
    wire [8*M-1:0]    pf;
    wire [M*32-1:0]   unused_s1;
    wire [M-1:0]      unused_f1;
    genvar c;
    generate
        for (c = 0; c < 8; c = c + 1) begin : g_l
            ot_hdc_v41x_wgt_mlane #(.M(M), .POOL(POOL)) u_l (.clk(clk), .rst_n(rst_n), .v(v[c]), .z(z[c]),
                                                .w(w[34*c +: 34]), .x(x[c*M*16 +: M*16]), .ov(pv[c]),
                                                .y(py[c*M*32 +: M*32]), .f(pf[c*M +: M]));
        end
    endgenerate
    ot_hdc_v41x_wgt_chain #(.M(M), .SPLIT(0)) u_ch (.clk(clk), .rst_n(rst_n), .v(pv), .sp4(1'b0), .t(py), .tf(pf),
                                                     .ov(ov), .s(s), .sf(sf), .s1st(unused_s1), .s1stf(unused_f1));
endmodule

// Eight block-dot lanes and their chain: one chunk of 8 contiguous 32-blocks (256 K terms), or in
// SPLIT (POOL) two rows of 4 blocks (the lightning indexer's 128-element FP4 dots).
// Lane c's operands at t + SK(c); the chunk sum leaves at t + 30 (and the split first row with it).
module ot_hdc_v41x_wgt_qchunk #(
    parameter integer M = 1,
    parameter integer POOL = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [7:0]         v,
    input  wire [7:0]         z,
    input  wire [7:0]         fp4,
    input  wire               split4,     // with lane 4's operands
    input  wire [8*264-1:0]   w,
    input  wire [8*M*264-1:0] x,
    output wire               ov,
    output wire [M*32-1:0]    s,
    output wire [M-1:0]       sf,
    output wire [M*32-1:0]    s1st,
    output wire [M-1:0]       s1stf
);
    wire [7:0]        pv;
    wire [8*M*32-1:0] py;
    wire [8*M-1:0]    pf;
    wire              sp4;
    genvar c;
    generate
        for (c = 0; c < 8; c = c + 1) begin : g_l
            ot_hdc_v41x_wgt_bdot #(.M(M)) u_l (.clk(clk), .rst_n(rst_n), .v(v[c]), .z(z[c]), .fp4(fp4[c]),
                                               .w(w[264*c +: 264]), .x(x[c*M*264 +: M*264]), .ov(pv[c]),
                                               .y(py[c*M*32 +: M*32]), .f(pf[c*M +: M]));
        end
        if (POOL != 0) begin : g_sp
            ot_hdc_delay #(.W(1), .D(9)) u_sp (.clk(clk), .rst_n(rst_n), .d(split4), .q(sp4));
        end else begin : g_nosp
            assign sp4 = 1'b0;
        end
    endgenerate
    ot_hdc_v41x_wgt_chain #(.M(M), .SPLIT(POOL)) u_ch (.clk(clk), .rst_n(rst_n), .v(pv), .sp4(sp4), .t(py), .tf(pf),
                                                        .ov(ov), .s(s), .sf(sf), .s1st(s1st), .s1stf(s1stf));
endmodule
