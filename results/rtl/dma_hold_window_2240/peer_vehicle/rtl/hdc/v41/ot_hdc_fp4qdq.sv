`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// E4M3-scaled FP4 quantise-dequantise of the DeepSeek-V4.1 decode core
// (compressed KV rows): tools/hdc_golden_v41.py qdq_fp4_e4m3, block 16.
//
// Two 16-element blocks per cycle (32 binary32 elements, II = 1, fixed
// latency LATENCY = 8, no stall).  Per block:
//
//   amax = max(max|x|, 6 * 2^-9);  s = E4M3-grid RNE of the exact quotient
//   amax / 6 (no saturation);  code = E2M1 index of |x| / s by comparing |x|
//   with the seven code midpoints times s (ties to the even code);
//   y = BF16(sign(x) * E2M1[code] * s).
//
// No divider anywhere.  The scale rounding compares amax against the eight
// (or three / five) E4M3 midpoints times 6, which are short constants once the
// binade of amax / 6 is known from amax's own exponent and whether its
// significand is >= 1.5; below 6 * 2^-6 the scale is on the E4M3 subnormal
// grid n * 2^-9 and the midpoints times 6 are eight binary32 constants.  s is
// kept as n * 2^qs with n in 1..16; every midpoint-times-s product K * n
// (K = 4 * midpoint in {1,3,5,7,10,14,20}) and every output value
// 2 * E2M1 * n has at most nine bits, so every compare and every output is
// exact, as the golden's float64 products are.
//
// -0 quantises to +0 (np.sign(-0.0) = +0); a negative element that rounds to
// zero keeps its sign.  A product past the binary32 range is +-inf, as the
// golden's float64 -> float32 cast gives.  A nonfinite element raises `fault`.
//
// Stages: S0 input register; S1 |x| and 16 -> 4 per block; S2 4 -> 1; S2b the
// floor; S3 scale; S4 thresholds; S5 codes; S6 outputs (registers).
// ---------------------------------------------------------------------------
module ot_hdc_fp4qdq (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [511:0]  y,
    output reg           fault
);
    localparam [30:0] FLOOR = 31'h3c400000;   // float32(6 * 2^-9)
    localparam [30:0] SUBN  = 31'h3dc00000;   // float32(6 * 2^-6): below it s is subnormal E4M3

    function automatic [30:0] mx(input [30:0] a, input [30:0] b);
        mx = (a >= b) ? a : b;
    endfunction
    // 3 * (2j + 1) * 2^-9 as binary32: six times the subnormal-grid midpoints
    function automatic [30:0] tsub(input integer j);
        case (j)
            1: tsub = 31'h3c900000; 2: tsub = 31'h3cf00000; 3: tsub = 31'h3d280000;
            4: tsub = 31'h3d580000; 5: tsub = 31'h3d840000; 6: tsub = 31'h3d9c0000;
            default: tsub = 31'h3db40000;
        endcase
    endfunction
    function automatic [4:0] kmid(input integer k);          // 4 * E2M1 midpoint
        case (k)
            0: kmid = 5'd1; 1: kmid = 5'd3; 2: kmid = 5'd5; 3: kmid = 5'd7;
            4: kmid = 5'd10; 5: kmid = 5'd14; default: kmid = 5'd20;
        endcase
    endfunction
    function automatic [3:0] twov(input [2:0] c);             // 2 * E2M1 value
        case (c)
            3'd0: twov = 4'd0; 3'd1: twov = 4'd1; 3'd2: twov = 4'd2; 3'd3: twov = 4'd3;
            3'd4: twov = 4'd4; 3'd5: twov = 4'd6; 3'd6: twov = 4'd8; default: twov = 4'd12;
        endcase
    endfunction

    integer i, j, b;

    // -- S0 ------------------------------------------------------------------------
    reg          s0_v;
    reg [1023:0] s0_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s0_v <= 1'b0;
        else s0_v <= v;
    end
    always @(posedge clk) s0_x <= x;

    // -- S1: 16 -> 4 per block (two 31-bit compare-and-select levels per stage; one is
    //    ~350 ps routed on ASAP7) -----------------------------------------------------------
    reg        s1_v, s1_nf;
    reg [30:0] s1_m [0:7];
    reg [30:0] t8 [0:15];
    reg        nf0;
    always @(*) begin
        nf0 = 1'b0;
        for (i = 0; i < 32; i = i + 1) nf0 = nf0 | (s0_x[32*i + 23 +: 8] == 8'hFF);
        for (i = 0; i < 16; i = i + 1) t8[i] = mx(s0_x[64*i +: 31], s0_x[64*i + 32 +: 31]);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= s0_v;
    end
    always @(posedge clk) begin
        s1_nf <= nf0;
        for (i = 0; i < 8; i = i + 1) s1_m[i] <= mx(t8[2*i], t8[2*i+1]);
    end

    // -- S2: 4 -> 1 per block --------------------------------------------------------------
    reg        s2a_v, s2a_nf;
    reg [30:0] s2a_m [0:1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2a_v <= 1'b0;
        else s2a_v <= s1_v;
    end
    always @(posedge clk) begin
        s2a_nf <= s1_nf;
        for (b = 0; b < 2; b = b + 1)
            s2a_m[b] <= mx(mx(s1_m[4*b], s1_m[4*b+1]), mx(s1_m[4*b+2], s1_m[4*b+3]));
    end

    // -- S2b: the floor --------------------------------------------------------------------
    reg        s2_v, s2_nf;
    reg [30:0] s2_amax [0:1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s2a_v;
    end
    always @(posedge clk) begin
        s2_nf <= s2a_nf;
        for (b = 0; b < 2; b = b + 1) s2_amax[b] <= mx(s2a_m[b], FLOOR);
    end

    // -- S3: s = n * 2^qs ---------------------------------------------------------------------
    reg              s3_v, s3_nf;
    reg [4:0]        s3_n [0:1];
    reg signed [9:0] s3_qs [0:1];
    reg [23:0]       ma;
    reg [4:0]        cnt;
    reg signed [9:0] ea;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_nf <= s2_nf;
        for (b = 0; b < 2; b = b + 1) begin
            ma = {1'b1, s2_amax[b][22:0]};
            ea = $signed({2'b00, s2_amax[b][30:23]}) - 10'sd127;
            if (s2_amax[b] < SUBN) begin
                //: n = 1 + #{j in 1..7 : amax past 6 (j + 1/2) 2^-9}, ties to even n
                cnt = 5'd1;
                for (j = 1; j < 8; j = j + 1)
                    if (s2_amax[b] > tsub(j) || (s2_amax[b] == tsub(j) && (j % 2) == 1)) cnt = cnt + 5'd1;
                s3_n[b] <= cnt;
                s3_qs[b] <= -10'sd9;
            end else if (s2_amax[b][22]) begin
                //: significand >= 1.5: amax / 6 = (2/3) sig * 2^(ea-2) in [1, 4/3) * 2^(ea-2);
                //: midpoint j (between 8+j and 9+j eighths) at sig = 3(17+2j)/32
                cnt = 5'd8;
                for (j = 0; j < 3; j = j + 1)
                    if (ma > (3 * (17 + 2 * j)) * (1 << 18) ||
                        (ma == (3 * (17 + 2 * j)) * (1 << 18) && (j % 2) == 1)) cnt = cnt + 5'd1;
                s3_n[b] <= cnt;
                s3_qs[b] <= ea - 10'sd5;
            end else begin
                //: significand < 1.5: amax / 6 = (4/3) sig * 2^(ea-3) in [4/3, 2) * 2^(ea-3);
                //: midpoints j = 0..2 are always passed
                cnt = 5'd11;
                for (j = 3; j < 8; j = j + 1)
                    if (ma > (3 * (17 + 2 * j)) * (1 << 17) ||
                        (ma == (3 * (17 + 2 * j)) * (1 << 17) && (j % 2) == 1)) cnt = cnt + 5'd1;
                s3_n[b] <= cnt;
                s3_qs[b] <= ea - 10'sd6;
            end
        end
    end

    // -- S4: the seven midpoint thresholds K * n * 2^(qs - 2) per block ---------------------
    reg              s4_v, s4_nf;
    reg [30:0]       s4_t [0:13];           // binary32 magnitude keys
    reg [13:0]       s4_big;                // threshold past the binary32 range
    reg [4:0]        s4_n [0:1];
    reg signed [9:0] s4_qs [0:1];
    reg [8:0]        pk;
    reg [3:0]        pp;
    reg signed [10:0] bt;
    reg [22:0]       mt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= s3_v;
    end
    always @(posedge clk) begin
        s4_nf <= s3_nf;
        for (b = 0; b < 2; b = b + 1) begin
            s4_n[b] <= s3_n[b]; s4_qs[b] <= s3_qs[b];
            for (j = 0; j < 7; j = j + 1) begin
                pk = kmid(j) * s3_n[b];
                pp = 4'd0;
                for (i = 0; i < 9; i = i + 1) if (pk[i]) pp = i[3:0];
                bt = $signed({7'd0, pp}) + s3_qs[b] - 11'sd2 + 11'sd127;
                mt = ({14'd0, pk} << (5'd23 - {1'b0, pp}));
                s4_big[7*b + j] <= (bt >= 11'sd255);
                s4_t[7*b + j] <= {bt[7:0], mt};
            end
        end
    end
    wire [1023:0] x4;
    ot_hdc_delay #(.W(1024), .D(5)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(x4));

    // -- S5: E2M1 codes ------------------------------------------------------------------------
    reg              s5_v, s5_nf;
    reg [2:0]        s5_c [0:31];
    reg [31:0]       s5_sgn;
    reg [4:0]        s5_n [0:1];
    reg signed [9:0] s5_qs [0:1];
    reg [30:0]       xm;
    reg [2:0]        cc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s5_v <= 1'b0;
        else s5_v <= s4_v;
    end
    always @(posedge clk) begin
        s5_nf <= s4_nf;
        for (b = 0; b < 2; b = b + 1) begin s5_n[b] <= s4_n[b]; s5_qs[b] <= s4_qs[b]; end
        for (i = 0; i < 32; i = i + 1) begin
            xm = x4[32*i +: 31];
            b = i / 16;
            //: the thresholds increase, so the code is the number passed; on a
            //: threshold the even code wins (midpoint j sits below code j+1)
            cc = 3'd0;
            for (j = 0; j < 7; j = j + 1)
                if (!s4_big[7*b + j] && (xm > s4_t[7*b + j] || (xm == s4_t[7*b + j] && (j % 2) == 1)))
                    cc = cc + 3'd1;
            s5_c[i] <= cc;
            s5_sgn[i] <= x4[32*i + 31] && (xm != 31'd0);
        end
    end

    // -- S6: BF16 of sign * E2M1[code] * n * 2^qs --------------------------------------------
    reg [7:0]         r;
    reg [2:0]         pr;
    reg signed [10:0] be;
    reg [7:0]         rn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= s5_v; fault <= s5_v && s5_nf; end
    end
    always @(posedge clk) begin
        for (i = 0; i < 32; i = i + 1) begin
            b = i / 16;
            r = twov(s5_c[i]) * s5_n[b];               // <= 12 * 16
            pr = 3'd0;
            for (j = 0; j < 8; j = j + 1) if (r[j]) pr = j[2:0];
            be = $signed({8'd0, pr}) + s5_qs[b] - 11'sd1 + 11'sd127;
            rn = r << (3'd7 - pr);
            if (r == 8'd0)           y[16*i +: 16] <= {s5_sgn[i], 15'd0};
            else if (be >= 11'sd255) y[16*i +: 16] <= {s5_sgn[i], 8'hFF, 7'd0};
            else                     y[16*i +: 16] <= {s5_sgn[i], be[7:0], rn[6:0]};
        end
    end
endmodule
