`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bmul3_rne (s81-bf deep full-rate BF, 2026-10-07, OPTIONAL lever): ot_v41_bmul2_rne_prepare (XS 0 / 1
// unchanged) plus XS = 2: XS = 1 and the gradual-underflow encode split in two stages (latency 9).
// ---------------------------------------------------------------------------
// ot_v41_bmul2: ot_hdc_bmul (rtl/hdc/ot_hdc_fpu.sv) with the 8x8 significand product split across stages 2 and 3,
// for the 1.2 GHz BF16 column lanes (ot_v41_bf16_lanes2).  Stage 2 forms the two 8x4 partial products, stage 3 adds
// them (ot_v41_ksadd, keep-prefix) before its normalise select.  The single-stage product was the column pair's SS
// endpoint (c1, ideal clock: u_m.s2_p[15] at -154.7 ps, 848 ps of product logic).  Same split as W13b's ot_hdc_bmul
// SPLIT = 1 (claude/w13-blockdot12 a2f92966); a separate module so the 40 records pinning ot_hdc_fpu.sv stay current.
// Default0 preserves ot_hdc_bmul y/fault. Opt-in1 enables finite gradual-underflow RNE.
// Five cycles and existing registers/engine ports retained. Stage4 SS/FF closure OPEN.
// ---------------------------------------------------------------------------
module ot_v41_bmul3_rne #(
    parameter integer GRADUAL_RNE = 0, // mandatory finite-domain repair; default preserves baseline
    // XS (BF rowfix re-cut A, 2026-10-07; default 0 = unchanged): +3 pipeline registers, latency 5 -> 8, bit-identical:
    // after the operand decode (stage 1 = exponent add only), after the partial-product add (stage 3 = normalise
    // select only) and after the subnormal RNE encode (stage 4 = result select only).  Routed BF HITFIX GRT at SS:
    // s1_e -212, s3_f -121, s4_y -224 ps.
    parameter integer XS = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
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
    wire [17:0] da0 = dec(a[30:23], a[22:16]);
    wire [17:0] db0 = dec(b[30:23], b[22:16]);
    // XS: stage-1 inputs registered after the decode
    wire [17:0] da, db;
    wire        i_v, i_s, i_z, i_nf;
    if (XS != 0) begin : g_x1
        reg [17:0] r_da, r_db; reg r_v, r_s, r_z, r_nf;
        always @(posedge clk or negedge rst_n) if (!rst_n) r_v <= 1'b0; else r_v <= v;
        always @(posedge clk) begin
            r_da <= da0; r_db <= db0; r_s <= a[31] ^ b[31];
            r_z <= (a[30:16] == 15'd0) || (b[30:16] == 15'd0); r_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
        end
        assign da = r_da; assign db = r_db; assign i_v = r_v; assign i_s = r_s; assign i_z = r_z; assign i_nf = r_nf;
    end else begin : g_n1
        assign da = da0; assign db = db0; assign i_v = v; assign i_s = a[31] ^ b[31];
        assign i_z = (a[30:16] == 15'd0) || (b[30:16] == 15'd0); assign i_nf = (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
    end
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [10:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= i_v;
    end
    always @(posedge clk) begin
        s1_s <= i_s;
        s1_z <= i_z;
        s1_nf <= i_nf;
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_e <= $signed(da[9:0]) + $signed(db[9:0]);
    end
    // stage 2: the two 8x4 partial products of the significand product
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [11:0] s2_lo, s2_hi;                   // the two 8x4 partial products
    reg signed [10:0] s2_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf; s2_e <= s1_e;
        s2_lo <= s1_a * s1_b[3:0]; s2_hi <= s1_a * s1_b[7:4];
    end
    // stage 3 first adds the partial products: a*b = a*b[7:4]*16 + a*b[3:0]; the high 12 bits are a 12-bit
    // keep-prefix add (<= 255*15 + 239 = 4064, no carry out).
    wire [11:0] hi_sum;
    wire        hi_co;
    ot_v41_ksadd #(.W(12)) u_ph (.a(s2_hi), .b({4'd0, s2_lo[11:4]}), .cin(1'b0), .s(hi_sum), .cout(hi_co));
    wire [15:0] pq0 = {hi_sum, s2_lo[3:0]};
    // XS: the product registered before the normalise select
    wire [15:0] pq;
    wire        j_v, j_s, j_z, j_nf;
    wire signed [10:0] j_e;
    if (XS != 0) begin : g_x3
        reg [15:0] r_pq; reg r_v, r_s, r_z, r_nf; reg signed [10:0] r_e;
        always @(posedge clk or negedge rst_n) if (!rst_n) r_v <= 1'b0; else r_v <= s2_v;
        always @(posedge clk) begin r_pq <= pq0; r_s <= s2_s; r_z <= s2_z; r_nf <= s2_nf; r_e <= s2_e; end
        assign pq = r_pq; assign j_v = r_v; assign j_s = r_s; assign j_z = r_z; assign j_nf = r_nf; assign j_e = r_e;
    end else begin : g_n3
        assign pq = pq0; assign j_v = s2_v; assign j_s = s2_s; assign j_z = s2_z; assign j_nf = s2_nf; assign j_e = s2_e;
    end
    // stage 3: normalise (leading bit 15 or 14) and bias
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= j_v;
    end
    always @(posedge clk) begin
        s3_s <= j_s; s3_z <= j_z; s3_nf <= j_nf;
        if (pq[15]) begin s3_f <= {pq[14:0], 8'd0}; s3_be <= j_e + 11'sd128; end
        else          begin s3_f <= {pq[13:0], 9'd0}; s3_be <= j_e + 11'sd127; end
    end
    // stage 4: encode; a subnormal result shifts right by 1 - biased (<= 7)
    reg        s4_v, s4_bad;
    reg [31:0] s4_y;
    wire [23:0] sig24 = {1'b1, s3_f};
    wire [3:0]  sub_sh = 4'd1 - s3_be[3:0];
    wire [23:0] sub_v = sig24 >> sub_sh;
    wire [31:0] gradual_y;
    generate if (GRADUAL_RNE != 0) begin : g_gradual
        ot_v41_bmul_subnormal_rne_prepare u_encode (.sign_i(s3_s), .biased_i(s3_be), .sig_i(sig24), .y(gradual_y));
    end else begin : g_baseline
        assign gradual_y = 32'd0;
    end endgenerate
    // XS: the encodes registered before the result select (k_* = stage-3 fields one cycle later)
    wire        k_v, k_s, k_z, k_nf;
    wire signed [10:0] k_be;
    wire [22:0] k_f, k_sub;
    wire [31:0] k_gy;
    if (XS >= 2) begin : g_x4s
        // XS = 2 (s81-bf deep BF): the gradual-underflow encode split over two registered stages (routed RECUT / UNROLL
        // limiter s3_be -> g_x4.r_gy, -237 / -299 ps): 4a forms the shift, retained significand, guard and sticky
        // (ot_v41_bmul_subnormal_rne_prepare's first half), 4b rounds and encodes.  Bit-identical, +1 cycle.
        wire signed [10:0] sf = 11'sd1 - s3_be;
        wire        inr = sf >= 11'sd1 && sf <= 11'sd24;
        wire [4:0]  shq = inr ? sf[4:0] : 5'd1;
        wire [4:0]  gix = shq - 5'd1;
        wire [23:0] ret = inr ? (sig24 >> shq) : 24'd0;
        wire        gb = inr && sig24[gix];
        reg  [23:0] stt;
        integer q;
        always @* for (q = 0; q < 24; q = q + 1) stt[q] = inr && (q < gix) && sig24[q];
        reg a_v, a_s, a_z, a_nf, a_inr, a_g, a_st; reg signed [10:0] a_be; reg [22:0] a_f, a_sub; reg [23:0] a_ret;
        always @(posedge clk or negedge rst_n) if (!rst_n) a_v <= 1'b0; else a_v <= s3_v;
        always @(posedge clk) begin
            a_s <= s3_s; a_z <= s3_z; a_nf <= s3_nf; a_be <= s3_be; a_f <= s3_f; a_sub <= sub_v[22:0];
            a_inr <= inr; a_ret <= ret; a_g <= gb; a_st <= |stt;
        end
        wire inc = a_g && (a_st || a_ret[0]);
        wire [23:0] rnd; wire rco;
        ot_v41_inc #(.W(24)) u_round (.a(a_ret), .inc(inc), .y(rnd), .co(rco));
        wire [31:0] gy = (!a_inr || rnd == 24'd0) ? 32'd0 : {a_s, 7'd0, rnd};
        reg r_v, r_s, r_z, r_nf; reg signed [10:0] r_be; reg [22:0] r_f, r_sub; reg [31:0] r_gy;
        always @(posedge clk or negedge rst_n) if (!rst_n) r_v <= 1'b0; else r_v <= a_v;
        always @(posedge clk) begin
            r_s <= a_s; r_z <= a_z; r_nf <= a_nf; r_be <= a_be; r_sub <= a_sub; r_f <= a_f;
`ifdef BF_DEEP_MUTANT_MUL
            r_gy <= GRADUAL_RNE != 0 ? (gy ^ {31'd0, a_g}) : 32'd0;   // negative control: guard leaks into the LSB
`else
            r_gy <= GRADUAL_RNE != 0 ? gy : 32'd0;
`endif
        end
        assign k_v = r_v; assign k_s = r_s; assign k_z = r_z; assign k_nf = r_nf; assign k_be = r_be; assign k_f = r_f;
        assign k_sub = r_sub; assign k_gy = r_gy;
    end else if (XS != 0) begin : g_x4
        reg r_v, r_s, r_z, r_nf; reg signed [10:0] r_be; reg [22:0] r_f, r_sub; reg [31:0] r_gy;
        always @(posedge clk or negedge rst_n) if (!rst_n) r_v <= 1'b0; else r_v <= s3_v;
        always @(posedge clk) begin
            r_s <= s3_s; r_z <= s3_z; r_nf <= s3_nf; r_be <= s3_be; r_sub <= sub_v[22:0]; r_gy <= gradual_y;
`ifdef W10_MUTANT_RECUT
            r_f <= s3_f ^ 23'd1;    // negative control: product significand LSB flipped in the added stage
`else
            r_f <= s3_f;
`endif
        end
        assign k_v = r_v; assign k_s = r_s; assign k_z = r_z; assign k_nf = r_nf; assign k_be = r_be; assign k_f = r_f;
        assign k_sub = r_sub; assign k_gy = r_gy;
    end else begin : g_n4
        assign k_v = s3_v; assign k_s = s3_s; assign k_z = s3_z; assign k_nf = s3_nf; assign k_be = s3_be; assign k_f = s3_f;
        assign k_sub = sub_v[22:0]; assign k_gy = gradual_y;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= k_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (k_z && !k_nf) s4_y <= 32'd0;
        else if (k_nf || k_be > 11'sd254 || (GRADUAL_RNE == 0 && k_be < -11'sd6)) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (k_be >= 11'sd1) s4_y <= {k_s, k_be[7:0], k_f};
        else if (GRADUAL_RNE != 0) s4_y <= k_gy;
        else s4_y <= {k_s, 8'd0, k_sub};
    end
    // stage 5: output register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
endmodule

