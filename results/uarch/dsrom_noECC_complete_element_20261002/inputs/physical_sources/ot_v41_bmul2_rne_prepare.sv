`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bmul2: ot_hdc_bmul (rtl/hdc/ot_hdc_fpu.sv) with the 8x8 significand product split across stages 2 and 3,
// for the 1.2 GHz BF16 column lanes (ot_v41_bf16_lanes2).  Stage 2 forms the two 8x4 partial products, stage 3 adds
// them (ot_v41_ksadd, keep-prefix) before its normalise select.  The single-stage product was the column pair's SS
// endpoint (c1, ideal clock: u_m.s2_p[15] at -154.7 ps, 848 ps of product logic).  Same split as W13b's ot_hdc_bmul
// SPLIT = 1 (claude/w13-blockdot12 a2f92966); a separate module so the 40 records pinning ot_hdc_fpu.sv stay current.
// Default0 preserves ot_hdc_bmul y/fault. Opt-in1 enables finite gradual-underflow RNE.
// Five cycles and existing registers/engine ports retained. Stage4 SS/FF closure OPEN.
// ---------------------------------------------------------------------------
module ot_v41_bmul2_rne_prepare #(
    parameter integer GRADUAL_RNE = 0 // mandatory finite-domain repair; default preserves baseline
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
        s1_z <= (a[30:16] == 15'd0) || (b[30:16] == 15'd0);
        s1_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
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
    wire [15:0] pq = {hi_sum, s2_lo[3:0]};
    // stage 3: normalise (leading bit 15 or 14) and bias
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf;
        if (pq[15]) begin s3_f <= {pq[14:0], 8'd0}; s3_be <= s2_e + 11'sd128; end
        else          begin s3_f <= {pq[13:0], 9'd0}; s3_be <= s2_e + 11'sd127; end
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= s3_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (s3_z && !s3_nf) s4_y <= 32'd0;
        else if (s3_nf || s3_be > 11'sd254 || (GRADUAL_RNE == 0 && s3_be < -11'sd6)) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (s3_be >= 11'sd1) s4_y <= {s3_s, s3_be[7:0], s3_f};
        else if (GRADUAL_RNE != 0) s4_y <= gradual_y;
        else s4_y <= {s3_s, 8'd0, sub_v[22:0]};
    end
    // stage 5: output register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
endmodule

