// Scoped source: rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv
// Generic opt-in correction of released E4M3 scale saturation; original DS core retained.
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
// el1011-hbm-fq track B (2026-10-12): PIPE=1 splits the two 2-level max stages (S0->S1 and S1->S2a) into one 31-bit
// compare-and-select per stage (+2 edges, LATENCY 10); XEXT=1 takes the S4-aligned element copy from x4_ext (driven by
// an external staging tile: x delayed PIPE ? 7 : 5 edges after s0_x) instead of the internal line.  Defaults keep the
// original module bit for bit and cycle for cycle.
module ot_hgi_fp4qdq__d4g_qdq #(parameter integer PACKED=0, parameter integer PIPE=0, parameter integer XEXT=0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [511:0]  y,
    output reg           fault,
    output wire [264:0]  packed_word,
    input  wire [1023:0] x4_ext
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
    // PIPE: t8 / nf0 / v registered (S1p) before the second level
    reg [30:0] t8q [0:15];
    reg        s1p_v, s1p_nf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1p_v <= 1'b0;
        else s1p_v <= s0_v;
    end
    always @(posedge clk) begin
        s1p_nf <= nf0;
        for (i = 0; i < 16; i = i + 1) t8q[i] <= t8[i];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= (PIPE != 0) ? s1p_v : s0_v;
    end
    always @(posedge clk) begin
        s1_nf <= (PIPE != 0) ? s1p_nf : nf0;
        for (i = 0; i < 8; i = i + 1)
            s1_m[i] <= (PIPE != 0) ? mx(t8q[2*i], t8q[2*i+1]) : mx(t8[2*i], t8[2*i+1]);
    end

    // -- S2: 4 -> 1 per block --------------------------------------------------------------
    reg        s2a_v, s2a_nf;
    reg [30:0] s2a_m [0:1];
    // PIPE: the first of the two levels registered (S2p)
    reg [30:0] s2p_m [0:3];
    reg        s2p_v, s2p_nf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2p_v <= 1'b0;
        else s2p_v <= s1_v;
    end
    always @(posedge clk) begin
        s2p_nf <= s1_nf;
        for (b = 0; b < 4; b = b + 1) s2p_m[b] <= mx(s1_m[2*b], s1_m[2*b+1]);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2a_v <= 1'b0;
        else s2a_v <= (PIPE != 0) ? s2p_v : s1_v;
    end
    always @(posedge clk) begin
        s2a_nf <= (PIPE != 0) ? s2p_nf : s1_nf;
        for (b = 0; b < 2; b = b + 1)
            s2a_m[b] <= (PIPE != 0) ? mx(s2p_m[2*b], s2p_m[2*b+1])
                                    : mx(mx(s1_m[4*b], s1_m[4*b+1]), mx(s1_m[4*b+2], s1_m[4*b+3]));
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
            if (s2_amax[b] >= 31'h45280000) begin
                // Released SATFINITE E4M3 scale: min(scale,448), 448=14*2^5.
                s3_n[b] <= 5'd14; s3_qs[b] <= 10'sd5;
            end else if (s2_amax[b] < SUBN) begin
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
    wire [1023:0] x4, x4_i;
    ot_hdc_delay__d4g_qdq #(.W(1024), .D((XEXT != 0) ? 0 : (PIPE != 0) ? 7 : 5)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(x4_i));
    assign x4 = (XEXT != 0) ? x4_ext : x4_i;

    // -- S5: E2M1 codes ------------------------------------------------------------------------
    reg              s5_v, s5_nf;
    reg [2:0]        s5_c [0:31];
    reg [31:0]       s5_sgn;
    reg [4:0]        s5_n [0:1];
    reg signed [9:0] s5_qs [0:1];
    reg [30:0]       xm;
    reg [2:0]        cc;
    reg [6:0]        qp;
    //: balanced count of seven predicates: (p0+p1)+(p2+p3) and (p4+p5)+p6
    function automatic [2:0] cnt7(input [6:0] p);
        reg [1:0] a, b2, c;
        begin
            a  = {1'b0, p[0]} + {1'b0, p[1]};
            b2 = {1'b0, p[2]} + {1'b0, p[3]};
            c  = {1'b0, p[4]} + {1'b0, p[5]};
            cnt7 = ({1'b0, a} + {1'b0, b2}) + ({1'b0, c} + {2'b0, p[6]});
        end
    endfunction
    // hgi-1010/c (route f589c9afa: s4_t -> s5_c 28 levels = seven 31-bit compares + the count in one edge): S5A registers
    // the predicates, S5B counts them (+1 edge; ot_hgi_quant_decode's alignment pipe is one shorter)
    reg              s5a_v, s5a_nf;
    reg [6:0]        s5a_p [0:31];
    reg [31:0]       s5a_sgn;
    reg [4:0]        s5a_n [0:1];
    reg signed [9:0] s5a_qs [0:1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s5a_v <= 1'b0; s5_v <= 1'b0; end
        else begin s5a_v <= s4_v; s5_v <= s5a_v; end
    end
    always @(posedge clk) begin
        s5a_nf <= s4_nf;
        for (b = 0; b < 2; b = b + 1) begin s5a_n[b] <= s4_n[b]; s5a_qs[b] <= s4_qs[b]; end
        for (i = 0; i < 32; i = i + 1) begin
            xm = x4[32*i +: 31];
            b = i / 16;
            //: the thresholds increase, so the code is the number passed; on a
            //: threshold the even code wins (midpoint j sits below code j+1)
            for (j = 0; j < 7; j = j + 1)
                qp = {(!s4_big[7*b + j] && (xm > s4_t[7*b + j] || (xm == s4_t[7*b + j] && (j % 2) == 1))), qp[6:1]};
            s5a_p[i] <= qp;
            s5a_sgn[i] <= x4[32*i + 31] && (xm != 31'd0);
        end
    end
    always @(posedge clk) begin
        s5_nf <= s5a_nf; s5_sgn <= s5a_sgn;
        for (b = 0; b < 2; b = b + 1) begin s5_n[b] <= s5a_n[b]; s5_qs[b] <= s5a_qs[b]; end
        for (i = 0; i < 32; i = i + 1) begin
            //: balanced count of the seven predicates (same count as the former serial cc = cc + 1 chain)
            cc = cnt7(s5a_p[i]);
            s5_c[i] <= cc;
        end
    end

    // Preserve original quantizer provenance, aligned with S6 y/vo. No re-quantization.
    function automatic [7:0] packed_scale(input [4:0] n, input signed [9:0] qs);
        begin
            if (qs == -10'sd9 && n < 5'd8) packed_scale = {5'd0,n[2:0]};
            else if (n == 5'd16) packed_scale = {1'b0,4'(qs+10'sd11),3'd0};
            else packed_scale = {1'b0,4'(qs+10'sd10),n[2:0]};
        end
    endfunction
    generate if(PACKED) begin : g_packed
        reg [143:0] meta; integer k;
        always @(posedge clk) begin
            meta[135:128] <= packed_scale(s5_n[0],s5_qs[0]);
            meta[143:136] <= packed_scale(s5_n[1],s5_qs[1]);
            for(k=0;k<32;k=k+1) meta[4*k +:4] <= {s5_sgn[k],s5_c[k]};
        end
        assign packed_word = {1'b1,120'd0,meta};
    end else begin : g_no_packed
        assign packed_word = 265'd0;
    end endgenerate

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

// Scoped source: rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv
`timescale 1ns/1ps
`default_nettype none
// ot_hgi_quant_wide_h decode, track B (el1011-hbm-fq 2026-10-12): ot_hgi_qw_dec split into three hardened tiles, each
// <= 15k clock sinks on its own root, registered on every seam, cycle for cycle and bit for bit the same as ot_hgi_qw_dec
// (same ports, same latency: tb_hgi_qw_dec3_equiv).  The one-tile decoder carried 35,679 flops on one root; 26k of them
// are the two element delay lines (actquant 13 x 1088, fp4qdq 5 x 1024 shared) and the fp4qdq result alignment
// (14 x 512).  Split:
//   X  ot_hgi_qw_dxl__d4g_qdq : the shared element line (14 x 1024 flops, no logic): x -> r1 .. r14; taps r1 (both s0
//                      registers), r8 (fp4qdq S4 copy) and r14 (actquant E copy).
//   B  ot_hgi_qw_dbq__d4g_qdq : the E4M3/FP4 path (ot_hgi_fp4qdq__d4g_qdq PIPE=1: one 31-bit max per stage, +2 edges) + 11 of the 12
//                      result-alignment registers.
//   A  ot_hgi_qw_daq__d4g_qdq : the actquant path (ot_hfd_actquant_m XEXT=1), the last alignment register (B's capture), the
//                      result select and the output registers; decode_fault.
// Edges (E1 = the one-tile decoder's input registers): X r_k at E_k; A/B s0_x = capture of r1 at E2 (as before);
// B captures r8 at E9 = s0 + 7 (PIPE=1 S4 alignment); A captures r14 at E15 = s0 + 13 (7 + MLAT); fp4qdq results go
// through 11 B registers + 1 A capture = the 12 alignment edges left after PIPE's +2 (was 14).
module ot_hgi_qw_dxl__d4g_qdq (
    input  wire          clk,
    input  wire [1023:0] x,
    output wire [1023:0] xs,     // r1 -> A and B s0_x
    output wire [1023:0] xb,     // r8 -> B x4 capture
    output wire [1023:0] xa      // r14 -> A xe capture
);
    reg [1023:0] r [1:14];
    integer k;
    always @(posedge clk) begin
        r[1] <= x;
        for (k = 2; k <= 14; k = k + 1) r[k] <= r[k-1];
    end
    assign xs = r[1]; assign xb = r[8]; assign xa = r[14];
endmodule

// header fields used by the decode: {header[127:118] (unit, op), header[71:64] (block)}
module ot_hgi_qw_dbq__d4g_qdq (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [17:0]   hd,
    input  wire [1023:0] xs,
    input  wire [1023:0] xb,
    output wire          bvo,
    output wire          bfo,
    output wire [511:0]  byo
);
    wire [0:0] rr_n;
    ot_rst_relay__d4g_qdq #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg i_v; reg [17:0] i_h; reg [1023:0] xc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) i_v <= 0; else i_v <= v;
    always @(posedge clk) begin i_h <= hd; xc <= xb; end
    wire [3:0] unit_code = i_h[17:14];
    wire [5:0] op = i_h[13:8];
    wire legal = (unit_code == 4) && (op == 4 || op == 5 || (op == 6 && i_h[7:0] == 16));
    wire take = i_v && legal;
    wire bv, bf; wire [511:0] by;
    ot_hgi_fp4qdq__d4g_qdq #(.PIPE(1), .XEXT(1)) bq (.clk(clk), .rst_n(rr_n[0]), .v(take && op == 6), .x(xs), .vo(bv), .y(by),
        .fault(bf), .packed_word(), .x4_ext(xc));
    // NB-cycle latency match (byo = by delayed NB edges).  Data is a ring of ND = NB-1 enabled 512-bit entries plus
    // one output register, NOT an NB-deep shift register: the shift register was 5,120 back-to-back flop->flop pairs
    // with no logic between them, so CTS/GRT hold repair flooded (b2: ~27k hold buffers, DPL-0033 at 4_1_cts).
    // Every ring path is flop -> enable mux / one-hot read AO-tree -> flop.  Read-before-overwrite at the write slot:
    // o(edge t) = mem[wp] = by(edge t-ND), so byo(edge t) = by(edge t-NB), identical to the shift register.
    // The one-hot pointer is replicated per 64-bit lane group (8 x ND flops) so no select net fans out to 512 bits.
    localparam integer NB = 11;
    localparam integer ND = NB - 1;
    localparam integer NG = 8, GW = 512 / NG;
    reg [NB-1:0] vp, fp;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin vp <= 0; fp <= 0; end
        else begin vp <= {vp[NB-2:0], bv}; fp <= {fp[NB-2:0], bf}; end
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_ring
        reg [ND-1:0] wp;
        reg [GW-1:0] mem [0:ND-1];
        reg [GW-1:0] rd, o;
        integer k;
        always @(posedge clk or negedge rr_n[0])
            if (!rr_n[0]) wp <= {{(ND-1){1'b0}}, 1'b1};
            else wp <= {wp[ND-2:0], wp[ND-1]};
        always @(*) begin
            rd = {GW{1'b0}};
            for (k = 0; k < ND; k = k + 1) rd = rd | ({GW{wp[k]}} & mem[k]);
        end
        always @(posedge clk) begin
            for (k = 0; k < ND; k = k + 1) if (wp[k]) mem[k] <= by[g*GW +: GW];
            o <= rd;
        end
        assign byo[g*GW +: GW] = o;
    end endgenerate
    assign bvo = vp[NB-1]; assign bfo = fp[NB-1];
endmodule

module ot_hgi_qw_daq__d4g_qdq #(parameter integer MUTANT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [17:0]   hd,
    input  wire [1023:0] xs,
    input  wire [1023:0] xa,
    input  wire          bvo,
    input  wire          bfo,
    input  wire [511:0]  byo,
    output reg           vo,
    output reg  [511:0]  y,
    output reg           fault,
    output reg           decode_fault
);
    wire [1:0] rr_n;
    ot_rst_relay__d4g_qdq #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg i_v; reg [17:0] i_h; reg [1023:0] xc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) i_v <= 0; else i_v <= v;
    always @(posedge clk) begin i_h <= hd; xc <= xa; end
    wire [3:0] unit_code = i_h[17:14];
    wire [5:0] op = i_h[13:8];
    wire e4 = op == 6;
    wire legal = (unit_code == 4) && (op == 4 || op == 5 || (op == 6 && i_h[7:0] == 16));
    wire take = i_v && legal;
    wire fp4 = (op == 5) ^ (MUTANT == 1);
    reg df;
    always @(posedge clk or negedge rr_n[1]) if (!rr_n[1]) df <= 0; else df <= i_v && !legal;
    wire av, af; wire [511:0] ay; wire [255:0] q; wire signed [9:0] exponent;
    ot_hfd_actquant_m #(.MR(1), .MLAT(6), .XEXT(1)) aq (.clk(clk), .rst_n(rr_n[1]), .v(take && !e4), .fp4(fp4), .x(xs),
        .vo(av), .q(q), .e(exponent), .y(ay), .fault(af), .xe_ext(xc));
    // B's result capture = the last alignment register
    reg cv, cf; reg [511:0] cy;
    always @(posedge clk or negedge rr_n[1]) if (!rr_n[1]) begin cv <= 0; cf <= 0; end else begin cv <= bvo; cf <= bfo; end
    always @(posedge clk) cy <= byo;
    wire d_vo = av | cv;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin vo <= 0; fault <= 0; decode_fault <= 0; end
        else begin vo <= d_vo; fault <= d_vo && (cv ? cf : af); decode_fault <= df; end
    always @(posedge clk) y <= cv ? cy : ay;
endmodule

// same ports and timing as ot_hgi_qw_dec; pure wiring around the three tiles
module ot_hgi_qw_dec3__d4g_qdq #(parameter integer MUTANT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [127:0]  header,
    input  wire [1023:0] x,
    output wire          vo,
    output wire [511:0]  y,
    output wire          fault,
    output wire          decode_fault
);
    wire [17:0] hd = {header[127:118], header[71:64]};
    wire [1023:0] xs, xb, xa; wire bvo, bfo; wire [511:0] byo;
    ot_hgi_qw_dxl__d4g_qdq u_dxl (.clk(clk), .x(x), .xs(xs), .xb(xb), .xa(xa));
    ot_hgi_qw_dbq__d4g_qdq u_dbq (.clk(clk), .rst_n(rst_n), .v(v), .hd(hd), .xs(xs), .xb(xb), .bvo(bvo), .bfo(bfo), .byo(byo));
`ifdef OT_HARD_CHILDREN
    ot_hgi_qw_daq__d4g_qdq u_daq (
`else
    ot_hgi_qw_daq__d4g_qdq #(.MUTANT(MUTANT)) u_daq (
`endif
        .clk(clk), .rst_n(rst_n), .v(v), .hd(hd), .xs(xs), .xa(xa), .bvo(bvo), .bfo(bfo),
        .byo(byo), .vo(vo), .y(y), .fault(fault), .decode_fault(decode_fault));
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split.sv
`timescale 1ns/1ps
`default_nettype none
// HBM d4g hb_quant_NW: soft parent composition of the CLOSED split leaves (OWNERS-HBM/QDQ 2026-10-18).
// Port-identical drop-in for ot_hgi_qdq_host_static__d4g_qdq (same port list and widths, same RL/WC/MUT/COMPACT parameters):
// the die binds hb_quant_NW to this master instead of the BLOCKED monolith (one CTS root cannot carry its SRAM and
// the 11.5 mm bank span).  Physical children, each with its own clock pin, named as the d4g grant slots:
//
//   program_leaf          ot_hgi_qdq_native_program_leaf__d4g_qdq #(COMPACT)   target48 collar + record calendar + programme SRAM
//                                                                     (no closed NW view: needs its own kit; SW twin
//                                                                     ot_hgi_qdq_sw_program_leaf is closed as sw125_r6)
//   quant_NW_xp           ot_hgi_qdq_static_transport_split__d4g_qdq #(IO_REGS1,RL+2,DL25,WC+1,NS4)  wires-only cluster:
//                           .ctl                 ot_hgi_qdq_transport_ctl__d4g_qdq #(RL+2,25,WC+1)   slot quant_NW_xp_ctl
//                           .slice[s].rslice     ot_hgi_qdq_transport_rslice__d4g_qdq #(NW2)          slot quant_NW_xp_rslice<s>
//                           .slice[s].wslice     ot_hgi_qdq_transport_wslice__d4g_qdq #(NW2)          slot quant_NW_xp_wslice<s>
//   u_dxl/u_dbq/u_daq     ot_hgi_qw_dxl__d4g_qdq / ot_hgi_qw_dbq__d4g_qdq / ot_hgi_qw_daq__d4g_qdq  the released decoder (closed qw_*_ref views)
//   quant_NW<k> k=0..3    ot_hgi_qdq_quant_bank_pair__d4g_qdq (wires-only cluster) -> .lg ot_hgi_qdq_lg_port_group__d4g_qdq #(BANKS2)
//                                                                     slot quant_NW<k>_lg, banks 2k and 2k+1
//
// RL / WC keep their monolith meaning: the fixed VM bank latency measured AT THESE PINS.  The LG groups add the priced
// fixed edges (rq +1, rr +1, wq +1) and the transport is always the registered boundary (+1 rr, +1 result), so the
// engine runs RL+2 / WC+1 internally (exactly ot_hgi_qdq_program_static LG=1).  Against the IO_REGS=0 monolith every
// port is the same stream, shifted by a fixed number of edges:
//   rq                            +1 edge   (VM read-slot reservation +1)
//   wq, beat_done, record_done    +5 edges  (VM write-slot reservation +5: IO_REGS +2, LG +3)
//   program_active/done, configured, fault-free behaviour   unchanged
// IO_REGS is accepted for drop-in compatibility only: the split IS the registered boundary.
// PIN_BOUNDARY=1 (reset collars + sticky fault flop) would be soft logic in this wires-only parent: not supported.
// The only parent gate is the two-input fault OR, exactly as in the monolith parent.
// LGMUT (bench only): 1 binds quant_NW0 / quant_NW1 to each other's write ports.
module ot_hgi_qdq_quant_bank_pair__d4g_qdq #(parameter integer BANKS=2)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output wire [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output wire [BANKS*257-1:0] rr_o,
    input wire [BANKS*281-1:0] wq_i, output wire [BANKS*281-1:0] wq_o
);
    ot_hgi_qdq_lg_port_group__d4g_qdq #(.BANKS(BANKS)) lg(.clk(clk),.rst_n(rst_n),
        .rq_i(rq_i),.rq_o(rq_o),.rr_i(rr_i),.rr_o(rr_o),.wq_i(wq_i),.wq_o(wq_o));
endmodule

module ot_hgi_qdq_host_split #(
    parameter integer RL=7,WC=4,MUT=0,COMPACT=0,PIN_BOUNDARY=0,IO_REGS=0,LGMUT=0
)(
    input wire clk_program,clk_transport,clk_dxl,clk_dbq,clk_daq,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire program_active,program_done,configured,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done,record_done,fault
);
    initial if(PIN_BOUNDARY!=0) $fatal(1,"ot_hgi_qdq_host_split: PIN_BOUNDARY=1 needs parent soft logic; not supported");
    wire [47:0] command;
    wire command_v,pfault,efault;
    wire [31:0] ordinal;
    ot_hgi_qdq_native_program_leaf__d4g_qdq #(.COMPACT(COMPACT)) program_leaf(
        .clk(clk_program),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .command(command),.command_v(command_v),.ordinal(ordinal),.active(program_active),.done(program_done),
        .configured(configured),.fault(pfault),.installed_cfg_we(),.installed_cfg_addr());
    // engine side of the LG groups
    wire [8*17-1:0] rq_e; wire [8*257-1:0] rr_e; wire [8*281-1:0] wq_e;
    wire v,vo,qfault,decode_fault;
    wire [127:0] header; wire [1023:0] x; wire [511:0] y;
    wire [17:0] hd={header[127:118],header[71:64]};
    wire [1023:0] xs,xb,xa; wire bvo,bfo; wire [511:0] byo;
    ot_hgi_qdq_static_transport_split__d4g_qdq #(.IO_REGS(1),.RL(RL+2),.DL(25),.WC(WC+1),.MUT(MUT),.NS(4)) quant_NW_xp(
        .clk(clk_transport),.rst_n(rst_n),.cmd_v(command_v&&command[0]),.cmd_op(command[6:1]),.cmd_block(command[14:7]),
        .cmd_src(command[30:15]),.cmd_dst(command[46:31]),.cmd_last(command[47]),.rq(rq_e),.rr(rr_e),.wq(wq_e),
        .beat_done(beat_done),.record_done(record_done),.fault(efault),
        .dec_v(v),.dec_header(header),.dec_x(x),.vo(vo),.qfault(qfault),.decode_fault(decode_fault),.y(y));
    ot_hgi_qw_dxl__d4g_qdq u_dxl(.clk(clk_dxl),.x(x),.xs(xs),.xb(xb),.xa(xa));
    ot_hgi_qw_dbq__d4g_qdq u_dbq(.clk(clk_dbq),.rst_n(rst_n),.v(v),.hd(hd),.xs(xs),.xb(xb),.bvo(bvo),.bfo(bfo),.byo(byo));
    ot_hgi_qw_daq__d4g_qdq u_daq(.clk(clk_daq),.rst_n(rst_n),.v(v),.hd(hd),.xs(xs),.xa(xa),
        .bvo(bvo),.bfo(bfo),.byo(byo),.vo(vo),.y(y),.fault(qfault),.decode_fault(decode_fault));
    // four bank-pair groups: quant_NW<k> serves banks 2k, 2k+1 (rq/rr/wq slices [(2k)*W, (2k+2)*W))
    wire [2*281-1:0] wq_g [0:3];
    for(genvar k=0;k<4;k=k+1) begin: bank_pair
        localparam integer KW=(LGMUT==1&&k<2)?(k^1):k;
        assign wq[KW*2*281+:2*281]=wq_g[k];
    end
    ot_hgi_qdq_quant_bank_pair__d4g_qdq #(.BANKS(2)) quant_NW0(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[0*34+:34]),.rq_o(rq[0*34+:34]),.rr_i(rr[0*514+:514]),.rr_o(rr_e[0*514+:514]),
        .wq_i(wq_e[0*562+:562]),.wq_o(wq_g[0]));
    ot_hgi_qdq_quant_bank_pair__d4g_qdq #(.BANKS(2)) quant_NW1(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[1*34+:34]),.rq_o(rq[1*34+:34]),.rr_i(rr[1*514+:514]),.rr_o(rr_e[1*514+:514]),
        .wq_i(wq_e[1*562+:562]),.wq_o(wq_g[1]));
    ot_hgi_qdq_quant_bank_pair__d4g_qdq #(.BANKS(2)) quant_NW2(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[2*34+:34]),.rq_o(rq[2*34+:34]),.rr_i(rr[2*514+:514]),.rr_o(rr_e[2*514+:514]),
        .wq_i(wq_e[2*562+:562]),.wq_o(wq_g[2]));
    ot_hgi_qdq_quant_bank_pair__d4g_qdq #(.BANKS(2)) quant_NW3(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[3*34+:34]),.rq_o(rq[3*34+:34]),.rr_i(rr[3*514+:514]),.rr_o(rr_e[3*514+:514]),
        .wq_i(wq_e[3*562+:562]),.wq_o(wq_g[3]));
    assign fault=pfault|efault;
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv
`timescale 1ns/1ps
`default_nettype none
// Physical leaf: actual target48 configuration collar, calendar core and mapped
// SRAM. Configuration/launch comes from the real host overlay/loader CP producer.
// PCW10 validates the PC12 host frame: out-of-range words/ranges fault, no alias.
module ot_hgi_qdq_native_program_leaf__d4g_qdq #(parameter integer COMPACT=0)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire [47:0] command,
    output wire command_v,
    output wire [31:0] ordinal,
    output wire active,done,configured,fault,
    output wire installed_cfg_we,output wire[9:0] installed_cfg_addr
);
    wire cfg_we,start_v;
    assign installed_cfg_we=cfg_we;assign installed_cfg_addr=address;
    wire [9:0] address,base;
    wire [10:0] limit;
    wire [15:0] loops;
    wire [255:0] data_word;
    wire target_fault,calendar_fault;
    ot_static_program_target__d4g_qdq #(.TARGET(8'd48),.PCW(10)) target(
        .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),
        .launch_v(launch_v),.program_active(active),.program_cfg_we(cfg_we),.program_cfg_addr(address),
        .program_cfg_data(data_word),.program_start_v(start_v),.program_start_base(base),
        .program_start_limit(limit),.program_start_loops(loops),.configured(configured),.fault(target_fault));
    generate if(COMPACT==0)begin: beat_programme
    ot_vms_calendar_static__d4g_qdq #(.W(48)) calendar(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(address),.cfg_data(data_word),
        .start_v(start_v),.start_base(base),.start_limit(limit),.start_loops(loops),
        .calendar(command),.calendar_v(command_v),.ordinal(ordinal),.active(active),.done(done),.fault(calendar_fault));
    end else begin: record_programme
        wire [31:0] local_cycle;
        wire record_fault;reg unsupported_loop;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)unsupported_loop<=0;
            else if(start_v && loops!=1)unsupported_loop<=1;
        assign calendar_fault=record_fault|unsupported_loop;
        reg [31:0] issued;
        ot_hgi_qdq_record_calendar__d4g_qdq calendar(
            .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(address),.cfg_data(data_word),
            .start_v(start_v),.start_base(base),.start_limit(limit),
            .command(command),.command_v(command_v),.cycle(local_cycle),.active(active),.done(done),.fault(record_fault));
        always @(posedge clk or negedge rst_n)
            if(!rst_n)issued<=0;
            else if(start_v)issued<=0;
            else if(command_v)issued<=issued+1;
        assign ordinal=issued;
    end endgenerate
    assign fault=target_fault|calendar_fault;
endmodule

// Wires-only native Quant parent; every physical child retains its own clock pin.
// Programme done reports issue completion; record_done includes fixed bank commit.
// Physical pin boundary (HBMA-QDQ 10-17, opt-in, defaults keep the bound die instance unchanged):
//  IO_REGS=1      registered bank-return rr / decoder y boundary in the transport (+1 bank-return edge, +1 result edge:
//                 VM write reservation t+35 -> t+37, read reservation unchanged; priced 3e0c10191 transport_boundary_r2).
//  PIN_BOUNDARY=1 rst_n reaches only two ot_rst_relay__d4g_qdq collars (programme root, transport root; release 3 edges, before
//                 any host configuration completes) and the fault pin leaves one sticky flop (+1 diagnostic edge).
//  Every other pin is already flop-first: cfg/desc/launch enter the target's capture flops, programme status, rq, wq,
//  beat_done and record_done leave registers.
module ot_hgi_qdq_host_static__d4g_qdq #(
    parameter integer RL=7,WC=4,MUT=0,COMPACT=0,PIN_BOUNDARY=0,IO_REGS=0
)(
    input wire clk_program,clk_transport,clk_dxl,clk_dbq,clk_daq,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire program_active,program_done,configured,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done,record_done,fault
);
    wire [47:0] command;
    wire command_v,pfault,efault;
    wire [31:0] ordinal;
    wire program_rst_n,engine_rst_n,fault_rst_n;
    generate if(PIN_BOUNDARY)begin: physical_boundary
        wire [1:0] prst_n;wire [0:0] erst_n;
        ot_rst_relay__d4g_qdq #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) program_reset(
            .clk(clk_program),.rst_n_in(rst_n),.rst_n(prst_n));
        ot_rst_relay__d4g_qdq #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) engine_reset(
            .clk(clk_transport),.rst_n_in(rst_n),.rst_n(erst_n));
        assign program_rst_n=prst_n[0];assign fault_rst_n=prst_n[1];assign engine_rst_n=erst_n[0];
        reg fault_q;
        always @(posedge clk_program or negedge fault_rst_n)
            if(!fault_rst_n)fault_q<=1'b0;
            else fault_q<=fault_q|pfault|efault;
        assign fault=fault_q;
    end else begin: original_boundary
        assign program_rst_n=rst_n;assign engine_rst_n=rst_n;assign fault_rst_n=rst_n;
        assign fault=pfault|efault;
    end endgenerate
    ot_hgi_qdq_native_program_leaf__d4g_qdq #(.COMPACT(COMPACT)) program_leaf(
        .clk(clk_program),.rst_n(program_rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .command(command),.command_v(command_v),.ordinal(ordinal),.active(program_active),.done(program_done),
        .configured(configured),.fault(pfault));
    ot_hgi_qdq_static #(.RL(RL),.WC(WC),.MUT(MUT),.IO_REGS(IO_REGS)) engine(
        .clk_transport(clk_transport),.clk_dxl(clk_dxl),.clk_dbq(clk_dbq),.clk_daq(clk_daq),.rst_n(engine_rst_n),
        .cmd_v(command_v&&command[0]),.cmd_op(command[6:1]),.cmd_block(command[14:7]),
        .cmd_src(command[30:15]),.cmd_dst(command[46:31]),.cmd_last(command[47]),
        .rq(rq),.rr(rr),.wq(wq),.beat_done(beat_done),.record_done(record_done),.fault(efault));
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv
`timescale 1ns/1ps
`default_nettype none
// GEO-H LG port group (v15 engine_lg_port_group_rule): one registered VM port cluster per bank pair.
// Bit slices follow the contract: rq [(2k)*17,(2k+2)*17), rr [(2k)*257,(2k+2)*257), wq [(2k)*281,(2k+2)*281).
// Pure fixed one-edge registers in each direction; the compiler/engine prices them (+1 rq, +1 rr, +1 wq).
// No ready, credit or arbitration. Only validity bits are reset; payload is bounded latency state.
// Own clock entry so each group is a separate physical leaf placed facing its bank pair (link < 500 um).
module ot_hgi_qdq_lg_port_group__d4g_qdq #(parameter integer BANKS=2)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output reg [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output reg [BANKS*257-1:0] rr_o,
    input wire [BANKS*281-1:0] wq_i, output reg [BANKS*281-1:0] wq_o
);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) for(integer b=0;b<BANKS;b=b+1) begin rq_o[b*17+16]<=0;rr_o[b*257+256]<=0;wq_o[b*281+280]<=0;end
        else for(integer b=0;b<BANKS;b=b+1) begin rq_o[b*17+16]<=rq_i[b*17+16];rr_o[b*257+256]<=rr_i[b*257+256];wq_o[b*281+280]<=wq_i[b*281+280];end
    always @(posedge clk)
        for(integer b=0;b<BANKS;b=b+1) begin rq_o[b*17+:16]<=rq_i[b*17+:16];rr_o[b*257+:256]<=rr_i[b*257+:256];wq_o[b*281+:280]<=wq_i[b*281+:280];end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
`timescale 1ns/1ps
`default_nettype none
// Timestamped native QDQ record programme. One word per operation rather than
// one word per beat or idle clock. Absolute timestamps determine production
// issue. No result status, ready, credit or dynamic dependency wait is read.
// Payload: start31:0, beats47:32, src63:48, dst79:64, op85:80, block93:86.
// Magic255:240=c7a1, PC233:224; all other bits zero. Real mapped SRAM only.
// One record prefetched at first beat; supported records have >=4 beats.
module ot_hgi_qdq_record_calendar__d4g_qdq #(
    parameter integer MUT=0 //1 wrong source;2 delayed timestamp
)(
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    output reg command_v,
    output reg [47:0] command,
    output reg [31:0] cycle,
    output reg active,done,fault
);
    reg cfg_q,start_q;
    reg [9:0] ca,base_q;
    reg [10:0] limit_q;
    reg [255:0] cd;
    always @(posedge clk)begin ca<=cfg_addr;cd<=cfg_data;base_q<=start_base;limit_q<=start_limit;end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cfg_q<=0;start_q<=0;end
        else begin cfg_q<=cfg_we;start_q<=start_v;end
    reg running,have,waiting;
    // The full1024-row capacity needs an11-bit exhausted sentinel;
    // a10-bit counter wraps to0 and silently replays the programme.
    reg [10:0] next_pc;
    reg [10:0] limit;
    reg [93:0] current,pending;
    reg pending_v;
    reg [15:0] beat;
    wire due=running && have && cycle>=current[31:0] && beat<current[47:32];
    wire first=due && beat==0;
    wire last=due && beat+16'd1==current[47:32];
    wire more=next_pc<limit;
    wire legal_launch=!running && !cfg_q && limit_q>{1'b0,base_q} && limit_q<=1024;
    wire read_start=start_q && legal_launch;
    wire read_next=first && more;
    wire read_v=read_start|read_next;
    wire [9:0] read_addr=read_start?base_q:next_pc[9:0];
    wire [255:0] macro_word;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_addr),.rd_out(macro_word),
        .w_ce_in(cfg_q&&!running&&!start_q),.w_addr_in(ca),.wd_in(cd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    reg rv0,rv1;
    reg [9:0] pc0,pc1;
    reg [255:0] captured;
    always @(posedge clk)begin captured<=macro_word;pc0<=read_addr;pc1<=pc0;end
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:224]==pc1 &&
        captured[239:234]==0 && captured[223:94]==0 && captured[47:32]>=4 &&
        (captured[85:80]==4 || captured[85:80]==5 || (captured[85:80]==6 && captured[93:86]==16));
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            running<=0;have<=0;waiting<=0;pending_v<=0;beat<=0;next_pc<=0;limit<=0;
            rv0<=0;rv1<=0;command_v<=0;cycle<=0;active<=0;done<=0;fault<=0;
        end else begin
            rv0<=read_v;rv1<=rv0;command_v<=0;done<=0;active<=running;
            if(cfg_q&&running)fault<=1;
            if(start_q)begin
                if(!legal_launch)fault<=1;
                else begin running<=1;cycle<=0;have<=0;pending_v<=0;waiting<=1;
                    next_pc<={1'b0,base_q}+11'd1;limit<=limit_q;beat<=0;end
            end else if(running)cycle<=cycle+1;
            if(read_next)next_pc<=next_pc+1'b1;
            if(rv1)begin
                if(!word_ok)fault<=1;
                if(waiting)begin current<=captured[93:0];have<=1;waiting<=0;beat<=0;end
                else begin pending<=captured[93:0];pending_v<=1;end
            end
            if(due)begin
                command_v<=1;
                command<={(beat+16'd1==current[47:32]),current[79:64]+16'(beat*4),
                    current[63:48]+16'(beat*4)+(MUT==1?16'd1:16'd0),current[93:86],current[85:80],1'b1};
                if(cycle!=current[31:0]+32'(beat)+(MUT==2?32'd1:32'd0))fault<=1;
                beat<=beat+1'b1;
                if(last)begin
                    if(pending_v)begin current<=pending;pending_v<=0;beat<=0;
                        if(pending[31:0]<=cycle)fault<=1;
                    end else if(!more)begin have<=0;running<=0;done<=1;end
                    else begin have<=0;fault<=1;end
                end
            end
            if(running && have && cycle>current[31:0]+32'(beat))fault<=1;
        end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_split.sv
`timescale 1ns/1ps
`default_nettype none
// QUANT transport split (H-ATTQ 2026-10-15). Structural successor of the registered (IO_REGS=1) monolith
// ot_hgi_qdq_static_transport, whose single CTS root spanned the 453.6 x 345.6 um face-pinned slot at 2 % util
// (r3 gate: 5,895 sinks, TT insertion 555.6 ps, spread 62.7 ps). The datapath is bit-sliced by 32-bit word:
// read word t of every lane only ever reads word t of some bank, write word t of every bank only ever takes word t
// of some lane. So NS independent word slices (read gather + write scatter) and one control leaf replace the
// monolith; each leaf is a small, dense, separately rooted tile. The bank selects are registered one edge earlier
// in the control leaf (sp[NP-3] / dst[ND-3]) and re-registered in each slice, so every operation edge is identical to
// the monolith: zero added cycles, same fixed calendar, no ready/credit. Only validity bits are reset (control leaf).
//
//   ot_hgi_qdq_transport_ctl__d4g_qdq         command pipelines, rq, wq header (valid/address/mask), dec_v/header, fault
//   ot_hgi_qdq_transport_rslice__d4g_qdq      rr word capture + 8:1 constant-bank gather for its words (no reset)
//   ot_hgi_qdq_transport_wslice__d4g_qdq      y word capture + 4->8 constant-bank scatter for its words (no reset)
//   ot_hgi_qdq_static_transport_split__d4g_qdq  wires-only parent, same ports/parameters as the monolith (IO_REGS=1 only)

module ot_hgi_qdq_transport_ctl__d4g_qdq #(
    parameter integer RL=7, DL=25, WC=4, MUT=0
)(
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output reg [8*17-1:0] rq,
    input wire [7:0] rr_v,            // rr[b*257+256] of the 8 banks
    output reg [7:0] wq_v,            // wq[b*281+280]
    output reg [8*16-1:0] wq_addr,    // wq[b*281+264 +: 16]
    output reg [8*8-1:0] wq_mask,     // wq[b*281 +: 8]
    output reg [2:0] rsel, wsel,      // bank selects, one edge ahead of the slices' local copies
    output reg beat_done, record_done,
    output reg fault,
    output reg dec_v,
    output reg [127:0] dec_header,
    input wire vo, qfault, decode_fault
);
    localparam integer NP=RL+2;   // RL+1+IO_REGS
    localparam integer ND=DL+1;
    reg vo_q,qfault_q,decode_fault_q;
    reg [7:0] rr_v_q;
    reg [2:0] write_bank_local;
    always @(posedge clk) rr_v_q<=rr_v;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin vo_q<=0;qfault_q<=0;decode_fault_q<=0;end
        else begin vo_q<=vo;qfault_q<=qfault;decode_fault_q<=decode_fault;end
    reg [NP-1:0] vp, lp;
    reg [15:0] sp [0:NP-1], dp [0:NP-1];
    reg [13:0] hp [0:NP-1];
    reg gl;
    reg [15:0] gd;
    reg [ND-1:0] dv, dl;
    reg [WC-1:0] donep,lastp;
    reg [15:0] dst [0:ND-1];
    reg [7:0] expected;
    reg bad;
    always @* begin
        expected='0;
        for(integer t=0;t<4;t=t+1) if(vp[NP-1]) expected[(sp[NP-1][2:0]+t)&7]=1'b1;
        bad=1'b0;
        for(integer t=0;t<8;t=t+1) if(rr_v_q[t]!=expected[t]) bad=1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            vp<='0; lp<='0; dec_v<=0; gl<=0;
            dv<='0; dl<='0; donep<='0; lastp<='0; beat_done<=0; record_done<=0; fault<=0;
        end else begin
            vp<={vp[NP-2:0],cmd_v}; lp<={lp[NP-2:0],cmd_last};
            dv<={dv[ND-2:0],dec_v}; dl<={dl[ND-2:0],gl};
            dec_v<=vp[NP-1]; gl<=lp[NP-1];
            if(bad || decode_fault_q || (vo_q && qfault_q) || vo_q!=dv[ND-1]) fault<=1;
            if(cmd_v && (!(cmd_op==4 || cmd_op==5 || (cmd_op==6 && cmd_block==16)) ||
                cmd_src[15:3] != ((cmd_src+16'd3)>>3) ||
                cmd_dst[15:3] != ((cmd_dst+16'd3)>>3))) fault<=1;
            donep<={donep[WC-2:0],dv[ND-1]};
            lastp<={lastp[WC-2:0],dv[ND-1]&&dl[ND-1]};
            beat_done<=donep[WC-1]; record_done<=lastp[WC-1];
        end
    end
    // Constant-index request and write-header packing (as the monolith's constant_port_pack).
    reg [8*17-1:0] rq_next;
    reg [7:0] wv_next;
    reg [8*16-1:0] wa_next;
    reg [8*8-1:0] wm_next;
    always @* begin
        rq_next='0; wv_next='0; wa_next='0; wm_next='0;
        for(integer b=0;b<8;b=b+1)
            for(integer k=0;k<4;k=k+1)begin
                if(((int'(cmd_src[2:0])+k)&7)==b) rq_next[b*17+:17]={cmd_v,cmd_src+16'(k)};
                if((((int'(write_bank_local)+k)&7)^(MUT==2?1:0))==b)begin
                    wv_next[b]=dv[ND-1]; wa_next[b*16+:16]=dst[ND-1]+16'(k); wm_next[b*8+:8]=8'hff;
                end
            end
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin for(integer k=0;k<8;k=k+1) rq[k*17+16]<=0; wq_v<='0; end
        else begin for(integer k=0;k<8;k=k+1) rq[k*17+16]<=rq_next[k*17+16]; wq_v<=wv_next; end
    always @(posedge clk) begin
        for(integer k=0;k<8;k=k+1) rq[k*17+:16]<=rq_next[k*17+:16];
        wq_addr<=wa_next; wq_mask<=wm_next;
        sp[0]<=cmd_src; dp[0]<=cmd_dst; hp[0]<={cmd_op,cmd_block};
        for(integer k=1;k<NP;k=k+1) begin sp[k]<=sp[k-1]; dp[k]<=dp[k-1]; hp[k]<=hp[k-1]; end
        gd<=dp[NP-1]; dec_header<='0; dec_header[127:124]<=4'd4;
        dec_header[123:118]<=hp[NP-1][13:8]; dec_header[71:64]<=hp[NP-1][7:0];
        dst[0]<=gd;
        for(integer k=1;k<ND;k=k+1) dst[k]<=dst[k-1];
        rsel<=sp[NP-3][2:0];             // == sp[NP-2] one edge later (slice read_bank_local)
        wsel<=dst[ND-3][2:0];            // == dst[ND-2] one edge later (slice write_bank_local)
        write_bank_local<=dst[ND-2][2:0];
    end
    initial if(RL<1 || DL<2 || WC<2) $fatal(1,"invalid measured QDQ pipeline");
endmodule

// Read gather for words [W0, W0+NW): gx[k][t] <= word t of bank ((sel+k)&7)^mut, from the registered rr face.
module ot_hgi_qdq_transport_rslice__d4g_qdq #(
    parameter integer NW=2, MUT=0
)(
    input wire clk,
    input wire [8*NW*32-1:0] rr_w,     // bank b word j at [(b*NW+j)*32 +: 32]
    input wire [2:0] rsel,
    output reg [4*NW*32-1:0] gx_w      // lane k word j at [(k*NW+j)*32 +: 32]
);
    reg [8*NW*32-1:0] rr_q;
    (* keep="true", dont_touch="true" *) reg [2:0] read_bank_local[0:3][0:NW-1];
    always @(posedge clk) begin
        rr_q<=rr_w;
        for(integer k=0;k<4;k=k+1) for(integer j=0;j<NW;j=j+1) read_bank_local[k][j]<=rsel;
    end
    for(genvar k=0;k<4;k=k+1)begin: lane
        for(genvar j=0;j<NW;j=j+1)begin: word_
            reg [31:0] selected;
            always @* begin
                selected='0;
                for(integer b=0;b<8;b=b+1)
                    if((((int'(read_bank_local[k][j])+k)&7)^(MUT==1?1:0))==b)
                        selected=selected|rr_q[(b*NW+j)*32+:32];
            end
            always @(posedge clk) gx_w[(k*NW+j)*32+:32]<=selected;
        end
    end
endmodule

// Write scatter for words [W0, W0+NW): bank b word j <= {y lane k word j, 16'd0} for the k that maps to b, else 0.
module ot_hgi_qdq_transport_wslice__d4g_qdq #(
    parameter integer NW=2, MUT=0
)(
    input wire clk,
    input wire [4*NW*16-1:0] y_w,      // lane k word j at [(k*NW+j)*16 +: 16]
    input wire [2:0] wsel,
    output reg [8*NW*16-1:0] wq_w      // bank b word j BF16 at [(b*NW+j)*16 +: 16] (low 16 bits of the word are 0)
);
    reg [4*NW*16-1:0] y_q;
    (* keep="true", dont_touch="true" *) reg [2:0] write_bank_local[0:7];
    always @(posedge clk) begin
        y_q<=y_w;
        for(integer b=0;b<8;b=b+1) write_bank_local[b]<=wsel;
    end
    for(genvar b=0;b<8;b=b+1)begin: bank
        reg [NW*16-1:0] nxt;
        always @* begin
            nxt='0;
            for(integer k=0;k<4;k=k+1)
                if((((int'(write_bank_local[b])+k)&7)^(MUT==2?1:0))==b)
                    for(integer j=0;j<NW;j=j+1) nxt[j*16+:16]=y_q[(k*NW+j)*16+:16];
        end
        always @(posedge clk) wq_w[b*NW*16+:NW*16]<=nxt;
    end
endmodule

module ot_hgi_qdq_static_transport_split__d4g_qdq #(
    parameter integer IO_REGS=1,
    parameter integer RL=7,
    parameter integer DL=25,
    parameter integer WC=4,
    parameter integer MUT=0,
    parameter integer NS=4             // word slices (8 words / NS each)
) (
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done, record_done,
    output wire fault,
    output wire dec_v,
    output wire [127:0] dec_header,
    output wire [1023:0] dec_x,
    input wire vo,qfault,decode_fault,
    input wire [511:0] y
);
    localparam integer NW=8/NS;
    initial if(IO_REGS!=1 || NS*NW!=8) $fatal(1,"split transport is the registered (IO_REGS=1) successor; NS must divide 8");
    wire [7:0] rr_v, wq_v; wire [8*16-1:0] wq_addr; wire [8*8-1:0] wq_mask; wire [2:0] rsel, wsel;
    for(genvar b=0;b<8;b=b+1)begin: bank_bits
        assign rr_v[b]=rr[b*257+256];
        assign wq[b*281+280]=wq_v[b];
        assign wq[b*281+264+:16]=wq_addr[b*16+:16];
        assign wq[b*281+:8]=wq_mask[b*8+:8];
    end
    ot_hgi_qdq_transport_ctl__d4g_qdq #(.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) ctl(
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),.cmd_src(cmd_src),
        .cmd_dst(cmd_dst),.cmd_last(cmd_last),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),.wq_mask(wq_mask),
        .rsel(rsel),.wsel(wsel),.beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(dec_v),.dec_header(dec_header),.vo(vo),.qfault(qfault),.decode_fault(decode_fault));
    for(genvar s=0;s<NS;s=s+1)begin: slice
        wire [8*NW*32-1:0] rr_w; wire [4*NW*32-1:0] gx_w;
        wire [4*NW*16-1:0] y_w; wire [8*NW*16-1:0] wq_w;
        for(genvar j=0;j<NW;j=j+1)begin: word_
            for(genvar b=0;b<8;b=b+1)begin: bank
                assign rr_w[(b*NW+j)*32+:32]=rr[b*257+(s*NW+j)*32+:32];
                assign wq[b*281+8+(s*NW+j)*32+:32]={wq_w[(b*NW+j)*16+:16],16'd0};
            end
            for(genvar k=0;k<4;k=k+1)begin: lane
                assign dec_x[k*256+(s*NW+j)*32+:32]=gx_w[(k*NW+j)*32+:32];
                assign y_w[(k*NW+j)*16+:16]=y[(k*8+s*NW+j)*16+:16];
            end
        end
        ot_hgi_qdq_transport_rslice__d4g_qdq #(.NW(NW),.MUT(MUT)) rslice(.clk(clk),.rr_w(rr_w),.rsel(rsel),.gx_w(gx_w));
        ot_hgi_qdq_transport_wslice__d4g_qdq #(.NW(NW),.MUT(MUT)) wslice(.clk(clk),.y_w(y_w),.wsel(wsel),.wq_w(wq_w));
    end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
`timescale 1ns/1ps
`default_nettype none
// F20 programme target. Two registered transport rungs; execution never waits.
// A descriptor arms exactly one launch. Actual programme-pin writes maintain a
// finite installed-row bitmap, not a shadow payload. The first write after a
// descriptor starts a fresh image generation; unwritten old SRAM rows are invalid.
// A descriptor-only rearm may reuse an installed image. Descriptor verification
// scans the exact [base,limit) range before configured can rise; descriptor-only
// reuse of the same resident range reuses its proof. All scanning and
// write-commit latency is initialization; an early launch faults without replay.
// TGT_PIN=1 (H-NETLIST 0600): the target id comes from the identity strap pin tgt (die constant), so one hardened master
// serves every target id; TGT_PIN=0 keeps the TARGET parameter (tgt unused).
// CAP_CLK=1 (H-NETLIST 0600): the F20 input-capture rung (cv/dv/lv, target/address/data/base/limit/loops, tgt) runs on
// clk_cap, a related same-frequency phase-0 root kept short at the face; the body (bitmap, scan, outputs) stays on clk.
module ot_static_program_target__d4g_qdq #(parameter [7:0] TARGET=8'd48,parameter integer PCW=10,parameter integer TGT_PIN=0,
                                  parameter integer CAP_CLK=0)(
    input wire clk,rst_n,
    input wire clk_cap,   // used only when CAP_CLK=1
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire program_active,
    output reg program_cfg_we,
    output reg [PCW-1:0] program_cfg_addr,
    output reg [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault
);
    localparam integer ROWS=1<<PCW;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    // External reset reaches two synchronizer pins, not the entire valid bitmap.
    (* async_reg = "true" *) reg reset_meta,reset_live;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_live<=0;end
        else begin reset_meta<=1;reset_live<=reset_meta;end
    reg cv,dv,lv;
    reg [7:0] target;
    wire clk_in=(CAP_CLK!=0)?clk_cap:clk;
    reg [7:0] tgt_q; always @(posedge clk_in) tgt_q<=tgt;
    wire [7:0] tid=(TGT_PIN!=0)?tgt_q:TARGET;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg [ROWS-1:0] installed;
    reg install_open,armed,scanning,validated,missing;
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk_in)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk_in or negedge reset_live)
        if(!reset_live)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            installed<=0;install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;
            scan_row<=0;scan_limit<=0;commit<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            // Observe the real registered programme-write pins. The neighbour's
            // capture and SRAM write consume two further edges; commit masks both.
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin
                if(!install_open)installed<=({{(ROWS-1){1'b0}},1'b1}<<program_cfg_addr);
                else installed[program_cfg_addr]<=1'b1;
                install_open<=1;
            end
            if(cv && target==tid)begin
                armed<=0;validated<=0;configured<=0;
                if(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address})fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end
            end
            if(dv && target==tid)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        // Same range in the unchanged resident generation: reuse
                        // the completed row proof, not a stale descriptor arm.
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!installed[scan_row])missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !installed[scan_row])fault<=1;
                    else validated<=1;
                end else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base;
                    program_start_limit<=stored_limit;program_start_loops<=stored_loops;
                end
            end
        end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
`timescale 1ns/1ps
`default_nettype none
// Programme SRAM is written before launch. A launch executes the fixed range
// [base,limit), repeated loops times. Nothing observes datapath arrival/ready.
// Each programme word: magic[255:240]=c7a1, PC identity[233:224], calendar[W-1:0];
// all reserved bits zero. The independent capture rung is the macro's only load.
module ot_vms_calendar_static__d4g_qdq #(
    parameter integer W=146,
    parameter integer MUT=0 // 1 wrong wrap PC, 2 extra cycle at loop boundary
)(
    input wire clk,rst_n,
    input wire cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output reg [W-1:0] calendar,
    output reg calendar_v,
    output reg [31:0] ordinal,
    output reg active,done,fault
);
    initial if(W<1 || W>223)$fatal(1,"VM calendar width must fit protected programme payload");
    reg cfg_we_q,start_v_q;
    reg [9:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [10:0] start_limit_q;
    reg [15:0] start_loops_q;
    always @(posedge clk)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cfg_we_q<=0;start_v_q<=0;end
        else begin cfg_we_q<=cfg_we;start_v_q<=start_v;end
    reg running;
    reg [9:0] pc,base;
    reg [10:0] limit;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,last0,last1;
    reg [9:0] pc0,pc1;
    reg [31:0] ord0,ord1;
    reg [255:0] captured;
    wire [255:0] macro_data;
    wire busy=running|valid0|valid1;
    wire legal_start=start_limit_q>{1'b0,start_base_q} && start_limit_q<=11'd1024 && start_loops_q!=0;
    wire final_issue=({1'b0,pc}+11'd1==limit) && loops_left==1;
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:224]==pc1 &&
                 captured[239:234]==0 && captured[223:W]==0;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(running),.r_addr_in(pc),.rd_out(macro_data),
        .w_ce_in(cfg_we_q && !busy && !start_v_q),.w_addr_in(cfg_addr_q),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    // Payload, ordinal and address identity have dedicated, nonreset rungs.
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
        calendar<=valid1 && word_ok?captured[W-1:0]:{W{1'b0}};
        ordinal<=ord1;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            running<=0;pc<=0;base<=0;limit<=0;loops_left<=0;issued<=0;
            valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q)begin
                if(busy || cfg_we_q || !legal_start)fault<=1;
                else begin
                    running<=1;pc<=start_base_q;base<=start_base_q;limit<=start_limit_q;
                    loops_left<=start_loops_q;issued<=0;
                end
            end
            if(running)begin
                issued<=issued+1;
                if({1'b0,pc}+11'd1==limit)begin
                    if(loops_left==1)running<=0;
                    else begin
                        pc<=base + ((MUT==1)?10'd1:10'd0);
                        loops_left<=loops_left-1;
                        if(MUT==2)running<=0;
                    end
                end else pc<=pc+1;
            end
        end
endmodule
`default_nettype wire

// Scoped source: rtl/hdc/ot_hdc_delay.sv
`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay__d4g_qdq #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_fastfp.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Low-latency binary32 add and multiply (ot_hdc_qadd__d4g_qdq / ot_hdc_qmul__d4g_qdq) for the
// decode core's stream unit and special-function pipelines.
//
// Same arithmetic, bit for bit, as the qualified five-stage pipes they stand in
// for -- rtl/proto/ot_fp32_add_rne_pipe.sv and rtl/hdc/ot_hdc_fp32_mul_pipe.sv:
// IEEE RNE with gradual underflow, every zero result canonical +0, a zero
// multiplier operand giving +0, (+-0)+(+-0) = +0, and a nonfinite operand or an
// overflowing result failing closed through `err` with y = 0.  Equivalence is
// checked cycle by cycle against those pipes (rtl/test/tb_hdc_fastfp_equiv.sv).
//
// What is different is depth.  The five-stage pipes are cut around carry
// chains that the synthesis flow maps to ripple logic (a 31-bit magnitude
// compare, 28-bit adds, a 48-bit product sum, the rounding increment); here
// every carry chain is an explicit Kogge-Stone prefix network, the product is a
// carry-save tree, and the leading-zero count is a tree whose exponent-floor
// clamp is a sentinel bit, so each operation is three register stages.
// ---------------------------------------------------------------------------

// W-bit adder with carry-in, Kogge-Stone prefix carries.
module ot_hdc_ksa__d4g_qdq #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    reg [W:0] g, p, gn, pn;
    integer l, i;
    always @* begin
        g = {a & b, cin};
        p = {a ^ b, 1'b0};
        for (l = 1; l <= W; l = l * 2) begin
            gn = g;
            pn = p;
            for (i = l; i <= W; i = i + 1) begin
                gn[i] = g[i] | (p[i] & g[i - l]);
                pn[i] = p[i] & p[i - l];
            end
            g = gn;
            p = pn;
        end
    end
    assign s = (a ^ b) ^ g[W-1:0];
    assign cout = g[W];
endmodule

// Leading-zero count of a 32-bit word as a tree (n = 32 for zero).
module ot_hdc_lzc32__d4g_qdq (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule

// 24 x 24 unsigned product in two halves, so a pipeline register can sit in
// the middle of the tree: 24 AND rows, Wallace reduction by vector 3:2
// compressors 24 -> 16 -> 11 -> 8 (ot_hdc_mul24_rows__d4g_qdq), then 8 -> 6 -> 4 -> 3
// -> 2 and a Kogge-Stone final add (ot_hdc_mul24_sum__d4g_qdq).  Rows are flat vectors,
// row k in bits [48k +: 48]; a compressor writes its sum to row 2i and its
// carry to row 2i+1.
module ot_hdc_mul24_rows__d4g_qdq (
    input  wire [23:0]     a,
    input  wire [23:0]     b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;        // {carry, sum} of three rows
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a & {24{b[i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

module ot_hdc_mul24_sum__d4g_qdq (
    input  wire [48*8-1:0] rows,
    output wire [47:0]     p
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(rows[144*i +: 48], rows[144*i + 48 +: 48], rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire unused_cout;
    ot_hdc_ksa__d4g_qdq #(.W(48)) u_cpa (.a(l7[47:0]), .b(l7[95:48]), .cin(1'b0), .s(p), .cout(unused_cout));
endmodule

// ---------------------------------------------------------------------------
// Binary32 add, LATENCY 3, II 1.  Stage for stage:
//   1  decode; |b| > |a| as one 31-bit prefix compare of the encodings; both
//      exponent differences; the smaller significand aligned with a jam
//   2  the add and the subtract (both prefix adders); the add's one-bit
//      renormalize; the cancellation normalize, its shift the leading-zero
//      count of the difference OR a sentinel at the exponent floor
//   3  round to nearest even (prefix increment), encode, the refusals
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_fast__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    //: Magnitude order is the integer order of the encodings (a subnormal's
    //: exponent 1 and a normal's hidden bit agree with it), so the swap is one
    //: compare: b[30:0] > a[30:0] exactly when a - b borrows.
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksa__d4g_qdq #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire swap = !cmp_c;
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksa__d4g_qdq #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksa__d4g_qdq #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    //: Three guard bits, everything shifted past them OR-ed into the lowest.
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    //: Both alignments, then the pick: when b is the larger b's exponent is
    //: not below a's, so dba is the distance; otherwise dab.
    wire [27:0] small_a = jam28(a_man, dba);
    wire [27:0] small_b = jam28(b_man, dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= bypass;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= bypass_code;
        s1_sub <= a[31] ^ b[31];
        s1_sign <= swap ? b[31] : a[31];
        s1_exp <= swap ? b_exp : a_exp;
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? small_a : small_b;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum, dif;
    wire sum_c, dif_c;
    ot_hdc_ksa__d4g_qdq #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum), .cout(sum_c));
    ot_hdc_ksa__d4g_qdq #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif), .cout(dif_c));
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    //: The authority normalizes one bit at a time while bit 26 is clear and the
    //: exponent is above 1: the shift is min(lzc, exp - 1).  A one at bit
    //: 26 - (exp - 1) makes the count stop there.
    wire [7:0]  room = s1_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz;
    ot_hdc_lzc32__d4g_qdq u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz));
    wire [26:0] sub_val = dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksa__d4g_qdq #(.W(8)) u_esub (.a(s1_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksa__d4g_qdq #(.W(8)) u_eadd (.a(s1_exp), .b(8'd0), .cin(carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_code <= s1_code; s2_sign <= s1_sign;
        s2_zero <= s1_sub && (dif == 28'd0);
        s2_exp <= s1_sub ? exp_sub : exp_add;
        s2_val <= s1_sub ? sub_val : add_val;
    end

    // -- stage 3 ------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_qdq #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd), .cout(rnd_c));
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, s2_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {s2_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (s2_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= s2_code; err <= s2_err; end
            else if (s2_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Binary32 multiply, LATENCY 3, II 1.
//   1  decode; subnormal operands normalized (tree LZC); the exponent sum;
//      the partial products and three carry-save levels (24 -> 8 rows)
//   2  the rest of the tree and the prefix final add; both exponent
//      decisions (leading bit 47 or 46) and the subnormal-result alignment
//      masks, all from the exponent sum alone
//   3  the product's top bit picks the decision; align, round, encode, refuse
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_fast__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_qdq u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_qdq u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    //: The authority's powers: field - 150 for a normal, -149 - shift for a
    //: subnormal (a normal has no leading zero, so the shift is 0 there).
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksa__d4g_qdq #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));

    //: The first three compressor levels ride in stage 1, after the normalize.
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows__d4g_qdq u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= nonfinite || zero;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_sign <= a[31] ^ b[31];
        s1_rows <= rows;
        s1_power <= power;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [47:0] prod;
    ot_hdc_mul24_sum__d4g_qdq u_sum (.rows(s1_rows), .p(prod));
    //: floor = power + msb; a subnormal result when floor < -126, and then the
    //: alignment is -(power + 149) whatever the msb, so only the normal path's
    //: fixed alignment (23 or 24) depends on the product.
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    //: sh_sub >= 24 whenever it is used; clamp at 63 (everything below).
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_sign <= s1_sign;
        s2_prod <= prod;
        s2_sub47 <= fl47 < -12'sd126;
        s2_sub46 <= fl46 < -12'sd126;
        s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_sh <= shc; s2_mr <= m_round; s2_ms <= m_sticky;
    end

    // -- stage 3 ------------------------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_qdq #(.W(24)) u_rnd (.a(main), .b(24'd0), .cin(rb && (st || main[0])), .s(rnd), .cout(rnd_c));
    wire carry = !is_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = fl + {11'd0, carry};
    wire over = !is_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = is_sub && rnd[23];
    wire [31:0] code = is_sub ? (sub_carry ? {s2_sign, 8'h01, 23'd0} : {s2_sign, 8'h00, rnd[22:0]})
                              : {s2_sign, field, man[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= 32'd0; err <= s2_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// Fault-reporting wrappers, as ot_hdc_fadd / ot_hdc_fmul but LATENCY 3.
module ot_hdc_qadd__d4g_qdq #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_add_fast__d4g_qdq (unchanged); L > 3 is ot_hdc_fp32_add_lat__d4g_qdq #(L), bit for bit
    // the same values, with the extra cuts (rtl/hdc/ot_hdc_fp32_add_lat__d4g_qdq.sv) so no stage carries two prefix adders.
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_add_fast__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul__d4g_qdq #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_mul_fast__d4g_qdq (unchanged); L > 3 is ot_hdc_fp32_mul_lat__d4g_qdq #(L), bit for bit
    // the same values; L >= 5 cuts the four carry-save levels from the 48-bit prefix add (fast stage 2, the lane
    // tile's -180 ps TT path s1_rows -> s2_prod).
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_mul_fast__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fastfp_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 serial-domain wrappers over the fast binary32 units (rtl/hdc/ot_hdc_fastfp.sv), kept out of that file so
// the records that pin it stay current.  Needs rtl/hdc/ot_hdc_fastfp.sv (or its DPI stand-ins); the non-default
// branches also need rtl/hdc/ot_hdc_fp32_mul_lat__d4g_qdq.sv, rtl/hdc/ot_hdc_fp32_add_lat__d4g_qdq.sv and rtl/hdc/ot_hdc_prefix.sv.
//   ot_hdc_qmul_lat__d4g_qdq #(LAT)       ot_hdc_qmul__d4g_qdq at LAT 3 (default), ot_hdc_fp32_mul_lat4__d4g_qdq / _lat5i / _lat #(LAT)
//   ot_hdc_qadd_lat__d4g_qdq #(KEEP, LAT) ot_hdc_qadd__d4g_qdq (default), ot_hdc_fp32_add_lat3__d4g_qdq / _lat4i (keep-prefix adders)
//   ot_hdc_kadd__d4g_qdq / _kge / _kinc   integer add / compare / increment: behavioural (K = 0) or keep-prefix (K = 1)
// ---------------------------------------------------------------------------
// ot_hdc_qmul_lat__d4g_qdq #(LAT): ot_hdc_qmul__d4g_qdq with the multiplier's latency as a parameter.  LAT = 3 is ot_hdc_qmul__d4g_qdq
// itself (ot_hdc_fp32_mul_fast__d4g_qdq); LAT = 4..7 is ot_hdc_fp32_mul_lat__d4g_qdq #(LAT) (rtl/hdc/ot_hdc_fp32_mul_lat__d4g_qdq.sv, which
// needs rtl/hdc/ot_hdc_fp32_add_lat__d4g_qdq.sv), bit-identical to it (21d9aab2: 5,000,000 biased pairs).  W11 serial
// domain: the 3-stage multiply misses 1.111 ns at SS; LAT 4 reaches 987 MHz.
module ot_hdc_qmul_lat__d4g_qdq #(
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (LAT == 3) begin : g_l3
        ot_hdc_fp32_mul_fast__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_l4
        // the fixed LAT-4 top: a plain module name, so synthesis can keep it as its own hierarchy
        // (ORFS SYNTH_KEEP_MODULES) and ABC maps it as the standalone unit
        ot_hdc_fp32_mul_lat4__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 5) begin : g_l5
        // LAT 5 is the input-cut variant (C1 + C3; rtl/hdc/ot_hdc_fp32_mul_lat__d4g_qdq.sv): the operand multiplexer ahead of
        // the unit shares a stage with the decode / normalise, not with the partial products (W11 serial domain)
        ot_hdc_fp32_mul_lat5i__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_ln
        ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// ot_hdc_qadd_lat__d4g_qdq #(KEEP, LAT): ot_hdc_qadd__d4g_qdq, or (KEEP = 1) the plain ot_hdc_fp32_add_lat3__d4g_qdq top of
// rtl/hdc/ot_hdc_fp32_add_lat__d4g_qdq.sv (needs rtl/hdc/ot_hdc_prefix.sv): the same binary32 add, bit for bit, with
// (* keep *) Kogge-Stone prefix adders that ABC cannot re-ripple inside a parent block; LAT = 4 (KEEP = 1) is
// the input-cut ot_hdc_fp32_add_lat4i__d4g_qdq (W11 serial domain, 0.9 GHz at SS).
module ot_hdc_qadd_lat__d4g_qdq #(
    parameter integer KEEP = 0,
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (KEEP == 0) begin : g_fast
        ot_hdc_fp32_add_fast__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_keep4
        ot_hdc_fp32_add_lat4i__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_keep
        ot_hdc_fp32_add_lat3__d4g_qdq u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Keep-prefix integer arithmetic for the W11 serial-domain build (K = 1: rtl/hdc/ot_hdc_prefix.sv, whose
// (* keep *) Kogge-Stone levels ABC cannot re-ripple; K = 0: the behavioural operator, the unit as it was).
module ot_hdc_kadd__d4g_qdq #(parameter integer W = 24, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire cin, output wire [W-1:0] s, output wire cout
);
    generate if (K == 0) begin : g_b
        assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
    end else begin : g_k
        ot_hdc_ksadd_k__d4g_qdq #(.W(W)) u (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
    end endgenerate
endmodule

// ge = (a >= b), unsigned
module ot_hdc_kge__d4g_qdq #(parameter integer W = 32, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, output wire ge
);
    generate if (K == 0) begin : g_b
        assign ge = (a >= b);
    end else begin : g_k
        wire [W-1:0] unused_s;
        ot_hdc_ksadd_k__d4g_qdq #(.W(W)) u (.a(a), .b(~b), .cin(1'b1), .s(unused_s), .cout(ge));
    end endgenerate
endmodule

// y = a + inc (mod 2^W)
module ot_hdc_kinc__d4g_qdq #(parameter integer W = 16, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire inc, output wire [W-1:0] y
);
    generate if (K == 0) begin : g_b
        assign y = a + {{(W-1){1'b0}}, inc};
    end else begin : g_k
        wire unused_co;
        ot_hdc_inc_k__d4g_qdq #(.W(W)) u (.a(a), .inc(inc), .y(y), .co(unused_co));
    end endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_add_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_add_lat__d4g_qdq #(LAT): the binary32 adder of ot_hdc_fp32_add_fast__d4g_qdq (rtl/hdc/ot_hdc_fastfp.sv), bit for bit,
// with LAT = 3..6 register stages.  A MEASUREMENT vehicle for the 1.2 GHz @ SS decision (W11, 2026-09-30): the
// same logic is cut at up to three extra boundaries, so the SS fmax against LAT shows the flop overhead.
//   A1  decode, magnitude compare, exponent differences        | cut C_A  (LAT >= 5)
//   A2  both jammed alignments, the swap pick
//   B1  28-bit sum and difference (prefix adders)               | cut C_B  (LAT >= 4)
//   B2  normalise: sentinel LZC, shift, exponent adjust
//   C1  round increment (prefix adder)                          | cut C_C  (LAT >= 6)
//   C2  encode, subnormal, overflow, canonical zero -> y
//   (B2 is cut after the sentinel LZC when LAT >= 7)
// Every prefix adder is ot_hdc_ksadd_k__d4g_qdq (rtl/hdc/ot_hdc_prefix.sv): (* keep *) Kogge-Stone levels, so ABC cannot
// re-ripple the carries inside a parent block (W13: the plain form closed standalone and failed in context).
// LAT 3 has the cuts of ot_hdc_fp32_add_fast__d4g_qdq (after A, after B, after C).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_lat__d4g_qdq #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bits {D, C, B, A} (LAT must be 3 + their count); -1: by LAT.
    // W11 serial domain: CUTS = 4'b0001 (C_A, LAT 4) cuts the INPUT side, so an operand multiplexer in front of
    // the unit shares stage 1 with the decode / compare instead of the alignment
    parameter integer CUTS = -1,
    // DRST 0 (fe-push-hphys-1010, opt-in via OT_FP_DATA_NORST): only the valid bits are reset (cuts VB, valid_out);
    // y / err / data cuts are plain flops (consumers qualify them with valid_out).  1: legacy, every stage bit reset.
    parameter integer DRST = `ifdef OT_FP_DATA_NORST 0 `else 1 `endif
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
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;     // inside B2: after the sentinel LZC
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k__d4g_qdq #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 boundary bundle
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    ot_hdc_w11_cut__d4g_qdq #(.W(WA + 1), .CUT(CUT_A), .VB(DRST ? -1 : WA - 1)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    // ---- A2 ----------------------------------------------------------------------------------------
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k__d4g_qdq #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    ot_hdc_w11_cut__d4g_qdq #(.W(WB), .CUT(CUT_B), .VB(DRST ? -1 : WB - 1)) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    // ---- B2 ----------------------------------------------------------------------------------------
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32__d4g_qdq u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // B2a -> B2b boundary (LAT >= 7)
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    ot_hdc_w11_cut__d4g_qdq #(.W(WD), .CUT(CUT_D), .VB(DRST ? -1 : WD - 1)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_qdq #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [WC-1:0] c2_in;
    ot_hdc_w11_cut__d4g_qdq #(.W(WC), .CUT(CUT_C), .VB(DRST ? -1 : WC - 1)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    // ---- C2 ----------------------------------------------------------------------------------------
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate if (DRST != 0) begin : g_yr
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
            else begin
                valid_out <= u_v;
                if (u_byp) begin y <= u_code; err <= u_err; end
                else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
                else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
                else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
            end
        end
    end else begin : g_yn
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= u_v;
        end
        always @(posedge clk) begin
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end endgenerate
endmodule

// a W-bit bundle, registered when CUT = 1 (bit 0... the bundle's MSB is the valid, reset to 0), else passed through
// VB >= 0 (fe-push-hphys-1010, opt-in): only bit VB (the bundle's valid) is reset; the data bits are plain flops (a wide
// datapath costs no reset fan-out; validity travels on the reset bit).  VB < 0 (default): every bit reset, as before.
module ot_hdc_w11_cut__d4g_qdq #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

// fixed tops for the hardening sweep
// the W11 serial-domain LAT-4 adder: the LAT-3 cuts plus C_A (after the decode / compare), bit-identical
module ot_hdc_fp32_add_lat4i__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(4), .CUTS(1)) u (.*);
endmodule
module ot_hdc_fp32_add_lat3__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(3)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat5__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat6__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_add_lat7__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_qdq #(.LAT(7)) u (.*);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_f12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// 1.2 GHz (0.833 ns at ASAP7 SS, 60 ps setup uncertainty) binary32 add and multiply for the DS HBM accelerator's
// serial unit (ot_hdc_v41x_vec, hbm-fmax-su 2026-10-04).  Bit for bit and cycle for cycle (at their LAT) the
// adder of ot_hdc_fp32_add_fast__d4g_qdq / ot_hdc_fp32_add_lat__d4g_qdq and the multiplier of ot_hdc_fp32_mul_fast__d4g_qdq /
// ot_hdc_fp32_mul_lat__d4g_qdq (rtl/test/tb_su_fp32_f12.sv); only the register boundaries move.
//
// Every cut point is optional (CUTS bit k, LAT = 1 + popcount(CUTS)); the output register is always there.
//   adder      bit 0  after the decode / magnitude compare / exponent differences        (= add_lat C_A)
//              bit 1  after the alignments and the swap pick                             (= add_lat s1)
//              bit 2  after the 28-bit sum and difference                                 (= add_lat C_B)
//              bit 3  after the sentinel leading-zero count                               (= add_lat C_D)
//              bit 4  after the cancellation shift and the exponent adjust                (= add_lat s2)
//              bit 5  after the rounding increment                                        (= add_lat C_C)
//              bit 6  after the decode and the exponent differences, BEFORE the magnitude compare (new; the lane's
//                     LAT-5 adder 7'b1101010: lane operand mux + decode + differences | compare, alignments, swap |
//                     add, LZC | shift, round | encode)
//     add_lat LAT 3 is CUTS 6'b010010; the f12 LAT-4 adder is 6'b101010: decode..swap | add, LZC | shift,
//     round | encode -- the rounding increment moves in front of s2 so the encode stage carries only the
//     exponent carry and the refusals.
//   multiplier bit 0  after the decode and the fraction leading-zero counts (new)
//              bit 1  after the normalise shift and the powers                           (= mul_lat C1)
//              bit 2  after the AND rows and three carry-save levels (24 -> 8)            (= mul_lat s1)
//              bit 3  after two more carry-save levels (8 -> 4) (new)
//              bit 4  after four carry-save levels (8 -> 2) and the masks                 (= mul_lat C2)
//              bit 5  after the 48-bit prefix add                                         (= mul_lat s2)
//              bit 6  after the select / subnormal shift / round and sticky bits          (= mul_lat C3)
//              bit 7  after the rounding increment                                        (= mul_lat C4)
//     mul_lat LAT 3 is CUTS 8'b00100100; the f12 LAT-5 multiplier is 8'b01101010.
// Timing changes that keep the function: the subnormal input normalisation counts the FRACTION's leading zeros
// (a_lz = 1 + clz23(frac) below an exponent field of 0: the same count, the field decode off the count's path);
// the multiplier's encode takes the two exponent fields and overflow flags (with and without the rounding
// carry) precomputed in the stage before; every increment is ot_hdc_inc_k__d4g_qdq (rtl/hdc/ot_hdc_prefix.sv); only
// the valid bits are reset (the data registers of add_lat / mul_lat cut bundles reset too: their contents
// never reach y without a valid, and y / err / valid_out reset as before).
// Needs rtl/hdc/ot_hdc_fastfp.sv (ot_hdc_lzc32__d4g_qdq, ot_hdc_mul24_rows__d4g_qdq) and rtl/hdc/ot_hdc_prefix.sv.
// ---------------------------------------------------------------------------

// a W-bit bundle with its valid bit (bit W-1), registered when CUT = 1 (the valid reset to 0), else a wire
module ot_hdc_f12_cut__d4g_qdq #(parameter integer W = 2, parameter integer CUT = 0) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT) begin : g_r
        reg         v;
        reg [W-2:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) v <= 1'b0;
            else v <= d[W-1];
        end
        always @(posedge clk) r <= d[W-2:0];
        assign q = {v, r};
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

module ot_hdc_fp32_add_f12__d4g_qdq #(
    parameter integer CUTS = 6'b101010
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
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    localparam integer K0 = CUTS % 2, K1 = (CUTS / 2) % 2, K2 = (CUTS / 4) % 2, K3 = (CUTS / 8) % 2,
                       K4 = (CUTS / 16) % 2, K5 = (CUTS / 32) % 2, K6 = (CUTS / 64) % 2;

    // ---- decode, exponent differences (bit 6: cut here, the magnitude compare after it); magnitude compare ----------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    wire [5:0] g6, g0;                         // {valid, f_eq, f_lt, -, dab >= 28, dba >= 28}
    ot_hdc_f12_cut__d4g_qdq #(.W(6), .CUT(K6)) u_g6 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a_field == b_field, a_field < b_field, 1'b0, dab >= 8'd28, dba >= 8'd28}), .q(g6));
    localparam integer WA6 = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8 + 31 + 31;
    wire [WA6-1:0] q6;
    ot_hdc_f12_cut__d4g_qdq #(.W(WA6), .CUT(K6)) u_k6 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
            a_exp, b_exp, a_man, b_man, dab, dba, a[30:0], b[30:0]}), .q(q6));
    wire [30:0] c_a = q6[61:31], c_b = q6[30:0];
    // the magnitude order of the encodings (swap = |b| > |a|) split at the exponent field: the field order is decided
    // beside the exponent differences (f_lt, f_eq, carried in g6 / g0), the fraction order after the cut; the same
    // predicate as the 31-bit compare of add_lat (the lane's compare + swap stage was 2-13 ps over 0.833 ns)
    wire frac_c;
    wire [22:0] frac_s;
    ot_hdc_ksadd_k__d4g_qdq #(.W(23)) u_cmp (.a(c_a[22:0]), .b(~c_b[22:0]), .cin(1'b1), .s(frac_s), .cout(frac_c));
    wire cmp_c = g6[4] ? frac_c : !g6[3];          // a >= b
    localparam integer WA = 1 + 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] qa;
    ot_hdc_f12_cut__d4g_qdq #(.W(WA), .CUT(K0)) u_k0 (.clk(clk), .rst_n(rst_n),
        .d({q6[WA6-1], !cmp_c, q6[WA6-2:62]}), .q(qa));
    wire        x_v, x_swap, x_byp, x_sub, x_as, x_bs;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_v, x_swap, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = qa;
    // ---- both alignments, the swap pick -------------------------------------------------------------
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    // the shifted-out-entirely flags (d >= 28), decided beside the exponent differences and carried through the cuts
    // (the stage after cut 6 was 4 ps over 0.833 ns in the lane with the compares in it)

    function automatic [27:0] jam28f;
        input [23:0] man;
        input [4:0]  d;
        input        far;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (far) jam28f = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d);
                jam28f = (val >> d) | {27'd0, |lost};
            end
        end
    endfunction
    ot_hdc_f12_cut__d4g_qdq #(.W(6), .CUT(K0)) u_g0 (.clk(clk), .rst_n(rst_n), .d(g6), .q(g0));
    wire [27:0] small_a = jam28f(x_aman, x_dba[4:0], g0[0]);
    wire [27:0] small_b = jam28f(x_bman, x_dab[4:0], g0[1]);
    localparam integer W1 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 28;
    wire [W1-1:0] q1;
    ot_hdc_f12_cut__d4g_qdq #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n),
        .d({x_v, x_byp, x_sub, x_swap ? x_bs : x_as, x_err, x_code, x_swap ? x_bexp : x_aexp,
            x_swap ? x_bman : x_aman, x_swap ? small_a : small_b}), .q(q1));
    wire        s1_v, s1_byp, s1_sub, s1_sign;
    wire [1:0]  s1_err;
    wire [31:0] s1_code;
    wire [7:0]  s1_exp;
    wire [23:0] s1_big;
    wire [27:0] s1_small;
    assign {s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, s1_big, s1_small} = q1;
    // ---- the sum and the difference ------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k__d4g_qdq #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer W2 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [W2-1:0] q2;
    ot_hdc_f12_cut__d4g_qdq #(.W(W2), .CUT(K2)) u_k2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(q2));
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = q2;
    // ---- the add's renormalise; the sentinel leading-zero count ------------------------------------------
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32__d4g_qdq u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    localparam integer W3 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [W3-1:0] q3;
    ot_hdc_f12_cut__d4g_qdq #(.W(W3), .CUT(K3)) u_k3 (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(q3));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = q3;
    // ---- the cancellation shift, the exponent adjust ------------------------------------------------------
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_inc_k__d4g_qdq #(.W(8)) u_eadd (.a(w_exp), .inc(w_carry), .y(exp_add), .co(exp_add_c));
    localparam integer W4 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    wire [W4-1:0] q4;
    ot_hdc_f12_cut__d4g_qdq #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n),
        .d({w_v, w_byp, w_sign, w_sub && (w_dif == 28'd0), w_err, w_code, w_sub ? exp_sub : exp_add,
            w_sub ? sub_val : w_add}), .q(q4));
    wire        s2_v, s2_byp, s2_sign, s2_zero;
    wire [1:0]  s2_err;
    wire [31:0] s2_code;
    wire [7:0]  s2_exp;
    wire [26:0] s2_val;
    assign {s2_v, s2_byp, s2_sign, s2_zero, s2_err, s2_code, s2_exp, s2_val} = q4;
    // ---- round increment ----------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k__d4g_qdq #(.W(24)) u_rnd (.a(s2_val[26:3]), .inc(inc), .y(rnd_w), .co(rnd_cw));
    localparam integer W5 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [W5-1:0] q5;
    ot_hdc_f12_cut__d4g_qdq #(.W(W5), .CUT(K5)) u_k5 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(q5));
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = q5;
    // ---- encode, subnormal, overflow, canonical zero -------------------------------------------------------
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= u_v;
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

module ot_hdc_fp32_mul_f12__d4g_qdq #(
    parameter integer CUTS = 8'b01101010
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
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    localparam integer K0 = CUTS % 2, K1 = (CUTS / 2) % 2, K2 = (CUTS / 4) % 2, K3 = (CUTS / 8) % 2,
                       K4 = (CUTS / 16) % 2, K5 = (CUTS / 32) % 2, K6 = (CUTS / 64) % 2, K7 = (CUTS / 128) % 2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- decode; the fractions' leading zeros ---------------------------------------------------------
    wire [7:0] a_field = a[30:23];
    wire [7:0] b_field = b[30:23];
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_cz, b_cz;                      // clz23 of the fraction (23 for a zero fraction)
    ot_hdc_lzc32__d4g_qdq u_la (.x({a[22:0], 9'h1ff}), .n(a_cz));
    ot_hdc_lzc32__d4g_qdq u_lb (.x({b[22:0], 9'h1ff}), .n(b_cz));
    localparam integer W0 = 1 + 1 + 2 + 1 + 23 + 23 + 8 + 8 + 5 + 5;
    wire [W0-1:0] q0;
    ot_hdc_f12_cut__d4g_qdq #(.W(W0), .CUT(K0)) u_k0 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), a[31] ^ b[31], a[22:0], b[22:0],
            a_field, b_field, a_cz[4:0], b_cz[4:0]}), .q(q0));
    wire        o0_v, o0_byp, o0_sign;
    wire [1:0]  o0_err;
    wire [22:0] o0_af, o0_bf;
    wire [7:0]  o0_ae, o0_be;
    wire [4:0]  o0_acz, o0_bcz;
    assign {o0_v, o0_byp, o0_err, o0_sign, o0_af, o0_bf, o0_ae, o0_be, o0_acz, o0_bcz} = q0;
    // ---- normalise (a subnormal's significand {frac, 0} << clz23; mul_lat's a_raw << (1 + clz23)), powers ---
    wire a_s = (o0_ae == 8'd0), b_s = (o0_be == 8'd0);
    wire [23:0] a_n = a_s ? ({o0_af, 1'b0} << o0_acz) : {1'b1, o0_af};
    wire [23:0] b_n = b_s ? ({o0_bf, 1'b0} << o0_bcz) : {1'b1, o0_bf};
    wire signed [11:0] a_power = a_s ? (-12'sd150 - {7'd0, o0_acz}) : ($signed({4'd0, o0_ae}) - 12'sd150);
    wire signed [11:0] b_power = b_s ? (-12'sd150 - {7'd0, o0_bcz}) : ($signed({4'd0, o0_be}) - 12'sd150);
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] q1;
    ot_hdc_f12_cut__d4g_qdq #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n),
        .d({o0_v, o0_byp, o0_err, o0_sign, a_n, b_n, a_power, b_power}), .q(q1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = q1;
    // ---- rows (24 AND rows, three carry-save levels), the exponent sum -----------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows__d4g_qdq u_rows (.a(p_a), .b(p_b), .rows(rows));
    localparam integer W2 = 1 + 1 + 2 + 1 + 48 * 8 + 12;
    wire [W2-1:0] q2;
    ot_hdc_f12_cut__d4g_qdq #(.W(W2), .CUT(K2)) u_k2 (.clk(clk), .rst_n(rst_n),
        .d({p_v, p_byp, p_err, p_sign, rows, power}), .q(q2));
    wire        s1_v, s1_byp, s1_sign;
    wire [1:0]  s1_err;
    wire [48*8-1:0] s1_rows;
    wire signed [11:0] s1_power;
    assign {s1_v, s1_byp, s1_err, s1_sign, s1_rows, s1_power} = q2;
    // ---- two carry-save levels (8 -> 6 -> 4) ---------------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    localparam integer W3 = 1 + 1 + 2 + 1 + 48 * 4 + 12;
    wire [W3-1:0] q3;
    ot_hdc_f12_cut__d4g_qdq #(.W(W3), .CUT(K3)) u_k3 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l5, s1_power}), .q(q3));
    wire        r3_v, r3_byp, r3_sign;
    wire [1:0]  r3_err;
    wire [48*4-1:0] r3_l5;
    wire signed [11:0] r3_power;
    assign {r3_v, r3_byp, r3_err, r3_sign, r3_l5, r3_power} = q3;
    // ---- two more carry-save levels (4 -> 3 -> 2); the floors and the subnormal masks -------------------
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    assign l6[0 +: 96] = csa(r3_l5[0 +: 48], r3_l5[48 +: 48], r3_l5[96 +: 48]);
    assign l6[96 +: 48] = r3_l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = r3_power + 12'sd47;
    wire signed [11:0] fl46 = r3_power + 12'sd46;
    wire signed [11:0] sh_sub = -(r3_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W4 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W4-1:0] q4;
    ot_hdc_f12_cut__d4g_qdq #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n),
        .d({r3_v, r3_byp, r3_err, r3_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(q4));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = q4;
    // ---- the 48-bit prefix add ---------------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k__d4g_qdq #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));
    localparam integer W5 = 1 + 1 + 2 + 1 + 48 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W5-1:0] q5;
    ot_hdc_f12_cut__d4g_qdq #(.W(W5), .CUT(K5)) u_k5 (.clk(clk), .rst_n(rst_n),
        .d({q_v, q_byp, q_err, q_sign, prod, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms}), .q(q5));
    wire        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    wire [1:0]  s2_err;
    wire [47:0] s2_prod, s2_mr, s2_ms;
    wire [5:0]  s2_sh;
    wire signed [11:0] s2_fl47, s2_fl46;
    assign {s2_v, s2_byp, s2_err, s2_sign, s2_prod, s2_sub47, s2_sub46, s2_fl47, s2_fl46, s2_sh, s2_mr, s2_ms} = q5;
    // ---- select, subnormal shift, round / sticky bits; both encode exponents ------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    // mul_lat's encode: floor_ = fl + carry; over = !sub && floor_ > 127; field = floor_[7:0] + 127.  Both
    // carries here (from the select's fl, both top choices side by side), picked by the carry after the round
    wire signed [11:0] f47p1 = s2_fl47 + 12'sd1, f46p1 = s2_fl46 + 12'sd1;
    wire [7:0]  fa47 = s2_fl47[7:0] + 8'd127, fb47 = f47p1[7:0] + 8'd127;
    wire [7:0]  fa46 = s2_fl46[7:0] + 8'd127, fb46 = f46p1[7:0] + 8'd127;
    wire        oa47 = s2_fl47 > 12'sd127, ob47 = f47p1 > 12'sd127;
    wire        oa46 = s2_fl46 > 12'sd127, ob46 = f46p1 > 12'sd127;
    wire [7:0]  fa = top ? fa47 : fa46, fb = top ? fb47 : fb46;
    wire        oa = top ? oa47 : oa46, ob = top ? ob47 : ob46;
    localparam integer W6 = 1 + 1 + 2 + 1 + 1 + 24 + 1 + 8 + 8 + 1 + 1;
    wire [W6-1:0] q6;
    ot_hdc_f12_cut__d4g_qdq #(.W(W6), .CUT(K6)) u_k6 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, main, rb && (st || main[0]), fa, fb, oa, ob}), .q(q6));
    wire        r_v, r_byp, r_sign, r_sub, r_inc, r_oa, r_ob;
    wire [1:0]  r_err;
    wire [23:0] r_main;
    wire [7:0]  r_fa, r_fb;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_main, r_inc, r_fa, r_fb, r_oa, r_ob} = q6;
    // ---- round ----------------------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k__d4g_qdq #(.W(24)) u_rnd (.a(r_main), .inc(r_inc), .y(rnd_w), .co(rnd_cw));
    localparam integer W7 = 1 + 1 + 2 + 1 + 1 + 24 + 1 + 8 + 8 + 1 + 1;
    wire [W7-1:0] q7;
    ot_hdc_f12_cut__d4g_qdq #(.W(W7), .CUT(K7)) u_k7 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, rnd_w, rnd_cw, r_fa, r_fb, r_oa, r_ob}), .q(q7));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c, o_oa, o_ob;
    wire [1:0]  o_err;
    wire [23:0] rnd;
    wire [7:0]  o_fa, o_fb;
    assign {o_v, o_byp, o_err, o_sign, o_sub, rnd, rnd_c, o_fa, o_fb, o_oa, o_ob} = q7;
    // ---- encode ---------------------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire over = !o_sub && (carry ? o_ob : o_oa);
    wire [7:0] field = carry ? o_fb : o_fa;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= o_v;
            if (o_byp) begin y <= 32'd0; err <= o_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// fixed tops (plain module names: ORFS SYNTH_KEEP_MODULES, standalone routes)
module ot_hdc_fp32_add_f12_l4__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_f12__d4g_qdq #(.CUTS(6'b101010)) u (.*);
endmodule
module ot_hdc_fp32_add_f12_l5__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_f12__d4g_qdq #(.CUTS(6'b101011)) u (.*);
endmodule
module ot_hdc_fp32_mul_f12_l5__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_f12__d4g_qdq #(.CUTS(8'b01101010)) u (.*);
endmodule
module ot_hdc_fp32_mul_f12_l6__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_f12__d4g_qdq #(.CUTS(8'b01101011)) u (.*);
endmodule
module ot_hdc_fp32_add_f12_l5s__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_f12__d4g_qdq #(.CUTS(6'b101110)) u (.*);     // l4 + the sum | renormalise, LZC cut
endmodule
// CLAUDE HBM-ABSTRACTS hub margin (2026-10-06): + the rounding-increment cut (bit 7): the round / encode stage behind
// u_k6 was the routed HC lane's critical path at ML 6 (m8hc SS@833 +3.8 ps)
module ot_hdc_fp32_mul_f12_l7__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_f12__d4g_qdq #(.CUTS(8'b11101011)) u (.*);
endmodule
module ot_hdc_fp32_mul_f12_l6r__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_f12__d4g_qdq #(.CUTS(8'b11101010)) u (.*);
endmodule
module ot_hdc_fp32_add_f12_l5x__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_f12__d4g_qdq #(.CUTS(7'b1101010)) u (.*);
endmodule
// the lane builds (ot_hdc_v41x_vec MLAT 6 / ALAT 5): an INPUT register in front of the LAT-5 multiplier / LAT-4 adder,
// so the lane's operand multiplexers (control decode + 3- to 5-way select, ~250 ps routed) own a whole stage
// (measured: the LAT-4 adder behind the lane's AD multiplexer missed 0.833 ns by 364 ps at placement)
module ot_hdc_f12_inreg__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output reg v, output reg [31:0] qa, qb);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v <= 1'b0;
        else v <= valid_in;
    end
    always @(posedge clk) begin qa <= a; qb <= b; end
endmodule
module ot_hdc_fp32_add_f12_l5i__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    wire v; wire [31:0] qa, qb;
    ot_hdc_f12_inreg__d4g_qdq u_i (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .v(v), .qa(qa), .qb(qb));
    ot_hdc_fp32_add_f12__d4g_qdq #(.CUTS(6'b101010)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(qa), .b(qb), .y(y), .err(err),
                                               .valid_out(valid_out));
endmodule
module ot_hdc_fp32_mul_f12_l6i__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    wire v; wire [31:0] qa, qb;
    ot_hdc_f12_inreg__d4g_qdq u_i (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .v(v), .qa(qa), .qb(qb));
    ot_hdc_fp32_mul_f12__d4g_qdq #(.CUTS(8'b01101010)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(qa), .b(qb), .y(y), .err(err),
                                                 .valid_out(valid_out));
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_mul_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_mul_lat__d4g_qdq #(LAT): the binary32 multiplier of ot_hdc_fp32_mul_fast__d4g_qdq (rtl/hdc/ot_hdc_fastfp.sv), bit for
// bit, with LAT = 3..9 register stages (W11 measurement vehicle for 1.2 GHz @ SS; see ot_hdc_fp32_add_lat__d4g_qdq).
//   S1  decode, subnormal LZC                             | C5 (LAT >= 8; margin rule 2026-10-06)
//       normalise shift                                   | C1 (LAT >= 6)
//       partial products + three carry-save levels, the exponent sum
//   S2  four carry-save levels                            | C2 (LAT >= 5)
//       the 48-bit prefix add; the subnormal masks
//   S3  select, subnormal shift, sticky/round bits        | C3 (LAT >= 4)
//       round increment (prefix add)                      | C4 (LAT >= 7)
//       encode                                            | C6 (LAT >= 9; margin rule 2026-10-06)
//   C7 (LAT >= 10; margin m3 2026-10-06) sits in front of S1: field / zero / non-finite decode | LZC, power
//       refusals -> y
// Every prefix adder is ot_hdc_ksadd_k__d4g_qdq (rtl/hdc/ot_hdc_prefix.sv, (* keep *) levels).
// Uses ot_hdc_w11_cut__d4g_qdq (rtl/hdc/ot_hdc_fp32_add_lat__d4g_qdq.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_lat__d4g_qdq #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bit k-1 = C<k> (LAT must be 3 + their count); -1: by LAT as above.
    // W11 serial domain: CUTS = 4'b0101 (C1 + C3, LAT 5) cuts the INPUT side, so an operand multiplexer in front
    // of the unit shares stage 1 with the decode / normalise instead of the partial-product rows
    parameter integer CUTS = -1,
    // KCP > 1 (margin m3, 2026-10-06): the C1 operand register is KCP kept copies (ot_hdc_mul_kcp48__d4g_qdq), each driving
    // 24/KCP partial products, so the 24-load operand broadcast to the partial-product rows is a local net.  Values
    // identical (every copy captures the same a_n / b_n); no added cycle.  Needs CUT1.
    parameter integer KCP = 1,
    // Opt-in: reset only valid bits at extra cuts; payload is ignored until valid.
    parameter integer DRST = 1
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
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    localparam integer CUT7 = (CUTS >= 0) ? (CUTS / 64) % 2 : (LAT >= 10) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + CUT7 + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_mul_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- S1a: decode, normalise --------------------------------------------------------------------
    // C7: field / zero / non-finite decode | LZC, power
    wire [68:0] c7;
    ot_hdc_w11_cut__d4g_qdq #(.W(69), .CUT(CUT7), .VB(DRST ? -1 : 69-1)) u_c7 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a, b, (a[30:23] == 8'd0), (b[30:23] == 8'd0),
            (a[30:23] == 8'hff) || (b[30:23] == 8'hff), (a[30:0] == 31'd0) || (b[30:0] == 31'd0)}), .q(c7));
    wire        x_v, x_afz, x_bfz, nonfinite, zero;
    wire [31:0] x_a, x_b;
    assign {x_v, x_a, x_b, x_afz, x_bfz, nonfinite, zero} = c7;
    wire [7:0]  a_field = x_a[30:23];
    wire [7:0]  b_field = x_b[30:23];
    wire [23:0] a_raw = {!x_afz, x_a[22:0]};
    wire [23:0] b_raw = {!x_bfz, x_b[22:0]};
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_qdq u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_qdq u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = x_afz ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = x_bfz ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut__d4g_qdq #(.W(W5), .CUT(CUT5), .VB(DRST ? -1 : W5-1)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({x_v, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), x_a[31] ^ x_b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = n_ar << n_al;
    wire [23:0] b_n = n_br << n_bl;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut__d4g_qdq #(.W(W1), .CUT(CUT1), .VB(DRST ? -1 : W1-1)) u_c1 (.clk(clk), .rst_n(rst_n),
        .d({n_v, n_bz, n_err, n_sign, a_n, b_n, n_ap, n_bp}),
        .q(c1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = c1;
    // ---- S1b: rows, exponent sum ------------------------------------------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k__d4g_qdq #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    generate if (KCP > 1 && CUT1 != 0) begin : g_kcp
        wire [KCP*24-1:0] ka, kb;
        genvar k;
        for (k = 0; k < KCP; k = k + 1) begin : g_c
            ot_hdc_mul_kcp48__d4g_qdq u_k (.clk(clk), .rst_n(rst_n),
`ifdef NEGK
                .d({a_n ^ ((k == 1) ? 24'd1 : 24'd0), b_n}),   // bench negative control only
`else
                .d({a_n, b_n}),
`endif .q({ka[24*k +: 24], kb[24*k +: 24]}));
        end
        ot_hdc_mul24_rows_k__d4g_qdq #(.K(KCP)) u_rows (.a(ka), .b(kb), .rows(rows));
    end else begin : g_nokcp
        ot_hdc_mul24_rows__d4g_qdq u_rows (.a(p_a), .b(p_b), .rows(rows));
    end endgenerate

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= p_v;
    end
    always @(posedge clk) begin
        s1_byp <= p_byp; s1_err <= p_err; s1_sign <= p_sign; s1_rows <= rows; s1_power <= power;
    end

    // ---- S2a: compress to two rows; masks ----------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut__d4g_qdq #(.W(W2), .CUT(CUT2), .VB(DRST ? -1 : W2-1)) u_c2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = c2;
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k__d4g_qdq #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl47; s2_fl46 <= q_fl46;
        s2_sh <= q_sh; s2_mr <= q_mr; s2_ms <= q_ms;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut__d4g_qdq #(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-1)) u_c3 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_qdq #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut__d4g_qdq #(.W(W4), .CUT(CUT4), .VB(DRST ? -1 : W4-1)) u_c4 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, r_fl, rnd_w, rnd_cw}), .q(c4));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c;
    wire [1:0]  o_err;
    wire signed [11:0] o_fl;
    wire [23:0] rnd;
    assign {o_v, o_byp, o_err, o_sign, o_sub, o_fl, rnd, rnd_c} = c4;
    // ---- S3c: encode --------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = o_fl + {11'd0, carry};
    wire over = !o_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // C6: encode | refusals -> y
    localparam integer W6 = 1 + 1 + 2 + 1 + 32;
    wire [W6-1:0] c6;
    ot_hdc_w11_cut__d4g_qdq #(.W(W6), .CUT(CUT6), .VB(DRST ? -1 : W6-1)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    generate if (DRST != 0) begin : g_output_reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end
    end else begin : g_output_valid_reset
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= e_v;
        end
        always @(posedge clk) begin
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end endgenerate
endmodule

module ot_hdc_fp32_mul_lat4__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat6__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat7__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(7)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat9__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(9)) u (.*);
endmodule

// the W11 serial-domain LAT-5 multiplier: the LAT-4 cuts plus C1 (after the decode / normalise), bit-identical
module ot_hdc_fp32_mul_lat5i__d4g_qdq (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_qdq #(.LAT(5), .CUTS(5)) u (.*);
endmodule

// KCP copy of the C1 operand register: kept (SYNTH_KEEP_MODULES) so equal-D copies are never merged into one driver
module ot_hdc_mul_kcp48__d4g_qdq (input wire clk, input wire rst_n, input wire [47:0] d, output reg [47:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 48'd0; else q <= d;
endmodule

// ot_hdc_mul24_rows__d4g_qdq with the operands supplied as K copies: partial product i reads copy i*K/24 (identical values)
module ot_hdc_mul24_rows_k__d4g_qdq #(parameter integer K = 2) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a[24*(i*K/24) +: 24] & {24{b[24*(i*K/24) + i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_prefix.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Explicit log-depth adders (W10, 72f00b86; shared FP primitive copy owned by W11, rtl/hdc/ot_hdc_prefix.sv).
//
// Written as behavioural `a + b` or `a + inc`, yosys/ABC maps these adders as carry ripples (chains of MAJ or
// OR cells) even with ADDER_MAP_FILE cleared: measured at ORFS WC, 0.833 ns, a 28-bit add inside the element
// took 920 ps and a 24-bit rounding increment a chain of ten OR4/OR5 cells (W10 and W13, 2026-09-30).  Here each
// Kogge-Stone prefix level is a (* keep *) net, so synthesis must keep log2(W) levels.
//
// ot_v41_ksadd: s = a + b + cin (W bits), cout.
// ot_v41_inc:   y = a + inc (W bits), co (the carry out of the top bit).
// ---------------------------------------------------------------------------
module ot_hdc_ksadd_k__d4g_qdq #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule


module ot_hdc_inc_k__d4g_qdq #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    // t[i]: all of positions [0, i] are one, position 0 being the increment
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign t[l + 1][i] = t[l][i] & t[l][i - (1 << l)];
                end else begin : g_p
                    assign t[l + 1][i] = t[l][i];
                end
            end
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule

// Scoped source: rtl/hdc/ot_hdc_sfu.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Special-function pipelines of the hardwired decode core: exp, reciprocal and
// reciprocal square root.  Each is an unrolled chain of the qualified binary32
// multiply/add pipes (LATENCY 5, II 1) plus single-cycle integer steps, so each
// accepts one operand per cycle and returns it a fixed DEPTH later.  No divider,
// no iteration, no combinational IEEE operation.
//
// The algorithms and their operation order are the specification in
// tools/hdc_golden.py (exp, reciprocal, rsqrt); the RTL matches it bit for bit.
// ---------------------------------------------------------------------------

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_vline__d4g_qdq #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule

// exp(x): clamp to [-87, 88]; n = rint(x*log2e) by the 1.5*2^23 trick; two-
// constant Cody-Waite reduction; degree-6 Horner; 2^n added to the exponent.
module ot_hdc_exp__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 92;
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [31:0] K_MAGIC = 32'h4B400000;   //  1.5 * 2^23
    localparam [31:0] K_NMAGIC = 32'hCB400000;
    localparam [31:0] K_HI    = 32'h3F317200;   //  ln2 high part
    localparam [31:0] K_LO    = 32'h35BFBE8E;   //  ln2 low part
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_qdq #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t, u, n, a_hi, a_lo, r1, r, xc_d20, lo_d5;
    wire [6:0] f;
    ot_hdc_fmul m_t  (clk, rst_n, vd[1],  xc, K_LOG2E, t,   f[0]);   // 6
    ot_hdc_fadd a_u  (clk, rst_n, vd[6],  t,  K_MAGIC, u,   f[1]);   // 11
    ot_hdc_fadd a_n  (clk, rst_n, vd[11], u,  K_NMAGIC, n,  f[2]);   // 16
    ot_hdc_fmul m_hi (clk, rst_n, vd[16], n,  K_HI,    a_hi, f[3]);  // 21
    ot_hdc_fmul m_lo (clk, rst_n, vd[16], n,  K_LO,    a_lo, f[4]);  // 21
    ot_hdc_delay__d4g_qdq #(.W(32), .D(20)) d_x (clk, rst_n, xc, xc_d20);
    ot_hdc_fadd a_r1 (clk, rst_n, vd[21], xc_d20, {~a_hi[31], a_hi[30:0]}, r1, f[5]);  // 26
    ot_hdc_delay__d4g_qdq #(.W(32), .D(5)) d_lo (clk, rst_n, a_lo, lo_d5);
    ot_hdc_fadd a_r  (clk, rst_n, vd[26], r1, {~lo_d5[31], lo_d5[30:0]}, r, f[6]);     // 31

    // Horner: p = C0; six times p = p*r + C[k]; r travels in 10-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay__d4g_qdq #(.W(32), .D(10)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_fmul u_m (clk, rst_n, vd[31 + 10*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_fadd u_a (clk, rst_n, vd[36 + 10*(k-1)], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    // n as an integer: u = 1.5*2^23 + n exactly, so n sits in u's fraction.
    reg  [8:0] nint;
    wire [8:0] nint_d;
    always @(posedge clk) nint <= u[8:0];   // low 9 bits of 0x400000 + n are n
    ot_hdc_delay__d4g_qdq #(.W(9), .D(79)) d_n (clk, rst_n, nint, nint_d);   // 12 -> 91
    always @(posedge clk) y <= pa[6] + {{14{nint_d[8]}}, nint_d, 23'd0};   // 92

    assign fault = |{f, hf};
endmodule

// 1/d: seed 0x7ef311c7 - bits(d), three Newton-Raphson steps y*(2 - d*y).
module ot_hdc_recip__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 46;
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_qdq #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0, d1;
    always @(posedge clk) begin
        // The bit seed wraps above this finite positive denominator.
        // Saturate that unsupported range to +0 before Newton iteration.
        y0 <= (!x[31] && x[30:23] != 8'hff && x > 32'h7EF311C7)
            ? 32'h00000000 : 32'h7EF311C7 - x;
        d1 <= x;
    end
    wire [31:0] yi [0:3];
    wire [31:0] dd [0:2];
    wire [31:0] m [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [8:0] f;
    assign yi[0] = y0;
    assign dd[0] = d1;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_d
                ot_hdc_delay__d4g_qdq #(.W(32), .D(15)) d_d (clk, rst_n, dd[k], dd[k+1]);
            end
            ot_hdc_fmul m_m (clk, rst_n, vd[1 + 15*k], dd[k], yi[k], m[k], f[3*k]);
            ot_hdc_fadd a_s (clk, rst_n, vd[6 + 15*k], 32'h40000000, {~m[k][31], m[k][30:0]}, s[k], f[3*k+1]);
            ot_hdc_delay__d4g_qdq #(.W(32), .D(10)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y (clk, rst_n, vd[11 + 15*k], yd[k], s[k], yi[k+1], f[3*k+2]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_rsqrt__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 61;
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_qdq #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    always @(posedge clk) y0 <= 32'h5F3759DF - {1'b0, x[31:1]};
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_fmul m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // 5
    ot_hdc_delay__d4g_qdq #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 6
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay__d4g_qdq #(.W(32), .D(20)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_fmul m_yy (clk, rst_n, vd[1 + 20*k],  yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_fmul m_hm (clk, rst_n, vd[6 + 20*k],  hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_fadd a_s  (clk, rst_n, vd[11 + 20*k], 32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay__d4g_qdq #(.W(32), .D(15)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y  (clk, rst_n, vd[16 + 20*k], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// Scoped source: rtl/lib/ot_rst_relay.sv
`timescale 1ns/1ps
// Registered, replicated local reset relay (synchronous-release reset tree).
//
// Design standard (coordinator 2026-10-10, drive-1010): a block's rst_n INPUT PORT drives only this relay.  The port net
// fans out to SYNC_STAGES synchronizer flops plus the asynchronous clear of the REGIONS*TREE_STAGES relay flops (assert
// stays asynchronous and immediate); release is synchronous and takes SYNC_STAGES + TREE_STAGES rising clk edges.
// Each region k then resets its own flops from rst_n[k], a flop output that placement can put next to that region, so no
// net from the port (or from one relay flop) spans the block.  On ~7 blocks the port -> thousands of reset flops net was
// the worst setup / hold path (hgi su_unit / su_ctl, idx-topk, qwen tile_e, ds qelem x1b).
//
// The region copies are logically identical, so synthesis would merge them: they are (* keep *) registers, which the
// ORFS flow's SYNTH_CANONICALIZE_TCL hook (physical/common_flow/ot_keep_regs.tcl, 0d3958d56) turns into kept flop cells.
//
// Consumers: release is delayed by RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES cycles (exactness is transaction-level; any
// logic that counts cycles from reset release must count from rst_n[k], never from the port).
module ot_rst_relay__d4g_qdq #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

    // relay tree: stage t, region r.  Every stage is replicated per region so each copy drives only its own region.
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

    assign rst_n = relay_q[TREE_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay__d4g_qdq: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay__d4g_qdq: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay__d4g_qdq: REGIONS must be >= 1");
    end
`endif
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 SQUARE ROOT for the V4.1 decode core: II 1, fixed
// DEPTH 31.  A stage-rebalanced copy of the qualified
// rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv (FRAC_SHIFT 15), with the decode
// core's port convention (v/a -> y/vo/fault).
//
// WHAT CHANGED, AND WHY.  The qualified pipe routes at 766 MHz on ASAP7: its
// critical path is the single finishing stage, which finds the root's leading
// bit by a priority encoder over all 28 root bits, shifts by a variable amount,
// rounds and encodes in one cycle.  But the leading bit is not variable: the
// radicand is a 24- or 25-bit significand times 2^(2*FRAC_SHIFT), so the root
// lies in [2^(11.5+F), 2^(12.5+F)) and its top bit is bit F+12 or bit F+11.
// Here the finish is a 2-way select on root[F+12] (stage 1: truncated
// significand, guard, sticky, exponent) and a separate round-and-encode
// (stage 2).  The digit recurrence and the decode stage are transcribed
// unchanged.  rtl/test/tb_hdc_fsqrt_equiv.sv drives both modules from one
// stimulus and requires the same code and the same refusal for every operand,
// one cycle later.
//
// FUNCTION.  y = RN_even(sqrt(a)); sqrt(+-0) = +0; subnormal arguments are
// normalised; a negative or nonfinite argument FAILS CLOSED (fault, y = +0).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;   // the root's possible top bit

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_qdq #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (as qualified) ------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage (as qualified) --------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire take = (shifted >= trial);
            always @(posedge clk) begin
                rem_stage[g]  <= take ? (shifted - trial) : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1 -------------------------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    reg [23:0] f_trunc;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg signed [EXP_W-1:0] f_unb;       // unbiased exponent before the rounding carry
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        if (hi) begin
            f_trunc  <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
            f_unb    <= $signed(TOP) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end else begin
            f_trunc  <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
            f_unb    <= $signed(TOP - 1) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end
    end

    // ---- finish 2: round to nearest even, encode --------------------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc[0]);
    wire [24:0] rounded  = {1'b0, f_trunc} + {24'd0, round_up};
    wire        carried  = rounded[24];
    wire [23:0] sig_out  = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] biased = f_unb + (carried ? 12'sd1 : 12'sd0) + 12'sd127;
    wire out_of_range = (biased < 12'sd1) || (biased > 12'sd254);
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased[7:0], sig_out[22:0]}; fault <= 1'b0; end
    end
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt_c12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fsqrt_c12__d4g_qdq: the 1.2 GHz (0.833 ns ASAP7 SS) successor of rtl/hdc/v41/ot_hdc_fsqrt__d4g_qdq.sv for the HBM SU
// (hbm-su closure, 2026-10-05).  Same ports, same DEPTH 31, the same {vo, y, fault} on every cycle, bit for bit
// (rtl/test/tb_hdc_fsqrt_c12_equiv.sv drives both from one stimulus).  New file; the original is unchanged.
// Timing-only rewrites (closure kit: kept prefix adders, precomputed carries), no register moved:
//   * digit stage: `shifted >= trial` and `shifted - trial` are ONE kept Kogge-Stone subtractor
//     (ot_hdc_ksadd_k__d4g_qdq: shifted + ~trial + 1; its carry out is the take bit), instead of a behavioural compare and
//     subtract that ABC ripples (routed -114 ps in the SU side pipe);
//   * finish 1 also registers both candidate biased exponents (no rounding carry / carry) and their
//     out-of-range flags, from the stage's own half exponent and top-bit select;
//   * finish 2 is only the kept 24-bit rounding increment (ot_hdc_inc_k__d4g_qdq) and a carry select (was -167 ps).
//     When the increment carries out, the rounded significand is 2^24, so the 23 stored fraction bits are the
//     increment's low 23 bits either way.
// Needs rtl/hdc/ot_hdc_prefix.sv (ot_hdc_ksadd_k__d4g_qdq, ot_hdc_inc_k__d4g_qdq) and ot_hdc_vline__d4g_qdq (rtl/hdc/ot_hdc_sfu.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt_c12__d4g_qdq (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_qdq #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (unchanged) ----------------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage, one kept subtractor -------------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire [REM_W-1:0] diff;
            wire             take;      // carry out of shifted + ~trial + 1  ==  (shifted >= trial)
            ot_hdc_ksadd_k__d4g_qdq #(.W(REM_W)) u_sub (.a(shifted), .b(~trial), .cin(1'b1), .s(diff), .cout(take));
            always @(posedge clk) begin
                rem_stage[g]  <= take ? diff : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1; both candidate exponents ------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    // biased = f_unb + 127 (+1 on a rounding carry); f_unb = half + (TOP - FRAC_SHIFT) (hi) or one less
    wire signed [EXP_W-1:0] h = half_stage[STAGES];
    wire signed [EXP_W-1:0] b_lo_hi = h + $signed(TOP - FRAC_SHIFT + 127);      // hi, no carry
    wire signed [EXP_W-1:0] b_lo_lo = h + $signed(TOP - 1 - FRAC_SHIFT + 127);  // lo, no carry
    wire signed [EXP_W-1:0] b_hi_hi = h + $signed(TOP - FRAC_SHIFT + 128);      // hi, carry
    wire [EXP_W-1:0] b0 = hi ? b_lo_hi : b_lo_lo;
    wire [EXP_W-1:0] b1 = hi ? b_hi_hi : b_lo_hi;                                 // lo + carry == hi, no carry
    reg [22:0] f_trunc_l;   // the truncated significand, low 23 bits
    reg        f_trunc23;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg [7:0]  f_b0, f_b1;
    reg        f_oor0, f_oor1;
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        f_b0 <= b0[7:0];
        f_b1 <= b1[7:0];
        f_oor0 <= ($signed(b0) < 12'sd1) || ($signed(b0) > 12'sd254);
        f_oor1 <= ($signed(b1) < 12'sd1) || ($signed(b1) > 12'sd254);
        if (hi) begin
            {f_trunc23, f_trunc_l} <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
        end else begin
            {f_trunc23, f_trunc_l} <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
        end
    end

    // ---- finish 2: kept rounding increment, carry select, encode --------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc_l[0]);
    wire [23:0] rounded;
    wire        carried;
    ot_hdc_inc_k__d4g_qdq #(.W(24)) u_inc (.a({f_trunc23, f_trunc_l}), .inc(round_up), .y(rounded), .co(carried));
    wire [7:0] biased = carried ? f_b1 : f_b0;
    wire       out_of_range = carried ? f_oor1 : f_oor0;
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased, rounded[22:0]}; fault <= 1'b0; end
    end
endmodule

