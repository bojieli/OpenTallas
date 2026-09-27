`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Arithmetic of the V4.1 lightning-indexer engine (ot_hdc_v41x_idx_*), bit
// exact to tools/hdc_golden_v41.py Model.indexer under R-ARITH (chunk8):
//
//   score[h] = to_bf16(dots_q4(q, key))              (FP4 x FP4 32-blocks)
//   term[h]  = to_bf16(mul(max(score[h], 0), wts[h]))
//   s        = to_bf16(csum over the heads of term)
//
// Modules here:
//   ot_hdc_v41x_csa       carry-save reduction (copy of ot_hdc_v41_csa)
//   ot_hdc_v41x_q4dot     exact FP4 (E2M1) x FP4 32-element block dot rounded
//                         once to binary32 (RNE, gradual underflow, +0), with
//                         the two UE8M0 block scales; LATENCY 3
//   ot_hdc_v41x_bmul      to_bf16(mul(relu(a), w)) for BF16 a, w; LATENCY 2
//   ot_hdc_v41x_bf16      to_bf16 of binary32 bits (function, combinational)
//
// E2M1 code c[3:0]: c[3] sign, c[2:0] magnitude index into
// {0, 0.5, 1, 1.5, 2, 3, 4, 6}; doubled magnitudes {0,1,2,3,4,6,8,12}.
// UE8M0 scale byte u: 2^(u - 127).  A 32-block dot of codes a, b with scales
// ua, ub is S * 2^(ua + ub - 256), S = sum(2a_i * 2b_i) an integer with
// |S| <= 32 * 144 = 4,608 (14-bit two's complement), so it is formed exactly
// and rounded once -- only where the result is subnormal -- as the golden's
// `.astype(F)` of its exact float64 block dot.  A scale byte >= 253 (2^126 and
// above: every such block the golden's quantiser can produce holds a code
// whose value overflows binary32) and a block value past the binary32 range
// fail closed through `ovf` (the fastfp adders refuse nonfinite operands; the
// engine never encodes an infinity).
// ---------------------------------------------------------------------------

// Carry-save reduction of N W-bit operands (mod 2^W) to at most M, by levels of
// 3:2 compressors; operands that do not fill a triple pass to the next level.
module ot_hdc_v41x_csa #(
    parameter integer N = 32,
    parameter integer M = 2,
    parameter integer W = 14
) (
    input  wire [N*W-1:0] d,
    output wire [M*W-1:0] q
);
    function automatic integer nxt(input integer n);
        nxt = 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer nlev(input integer n, input integer m);
        integer c, k;
        begin
            nlev = 0; c = n;
            for (k = 0; k < 64; k = k + 1)
                if (c > m) begin c = nxt(c); nlev = nlev + 1; end
        end
    endfunction
    function automatic integer cnt(input integer n, input integer l);
        integer k;
        begin
            cnt = n;
            for (k = 0; k < l; k = k + 1) cnt = nxt(cnt);
        end
    endfunction
    function automatic integer off(input integer n, input integer l);
        integer k, c;
        begin
            off = 0; c = n;
            for (k = 0; k < l; k = k + 1) begin off = off + c; c = nxt(c); end
        end
    endfunction
    localparam integer L = nlev(N, M);
    localparam integer NF = cnt(N, L);
    localparam integer OL = off(N, L);
    localparam integer TOT = OL + NF;
    wire [W-1:0] op [0:TOT-1] /*verilator split_var*/;
    genvar i, l;
    generate
        for (i = 0; i < N; i = i + 1) begin : g_in
            assign op[i] = d[W*i +: W];
        end
        for (l = 0; l < L; l = l + 1) begin : g_lvl
            localparam integer NI = cnt(N, l);
            localparam integer OI = off(N, l);
            localparam integer OO = off(N, l + 1);
            localparam integer G3 = NI / 3;
            for (i = 0; i < G3; i = i + 1) begin : g_fa
                wire [W-1:0] a = op[OI + 3*i];
                wire [W-1:0] b = op[OI + 3*i + 1];
                wire [W-1:0] c = op[OI + 3*i + 2];
                wire [W-1:0] mj = (a & b) | (a & c) | (b & c);
                assign op[OO + 2*i] = a ^ b ^ c;
                assign op[OO + 2*i + 1] = {mj[W-2:0], 1'b0};
            end
            for (i = 0; i < NI % 3; i = i + 1) begin : g_pass
                assign op[OO + 2*G3 + i] = op[OI + 3*G3 + i];
            end
        end
        for (i = 0; i < M; i = i + 1) begin : g_out
            if (i < NF) begin : g_op
                assign q[W*i +: W] = op[OL + i];
            end else begin : g_zero
                assign q[W*i +: W] = {W{1'b0}};
            end
        end
    endgenerate
endmodule

// ---------------------------------------------------------------------------
// Exact FP4 x FP4 block dot, rounded once to binary32.  LATENCY 3, II 1, no
// reset on data (validity travels outside).
//   A  products (3x3-bit magnitude table), sign as ones' complement plus a
//      count, offset-binary operands (no sign extension); CSA 34 -> 4
//   B  CSA 4 -> 2, carry-propagate add: S (14-bit two's complement)
//   C  |S|, leading-zero count, normal pack or subnormal right shift + RNE
// ---------------------------------------------------------------------------
module ot_hdc_v41x_q4dot (
    input  wire         clk,
    input  wire [127:0] a,        // 32 E2M1 codes, element i at [4i+3:4i]
    input  wire [127:0] b,
    input  wire [7:0]   ua,       // UE8M0 scale bytes
    input  wire [7:0]   ub,
    output reg  [31:0]  y,        // binary32, canonical +0
    output reg          ovf       // refused: scale >= 2^126, or |value| >= 2^128
);
    function automatic [3:0] dmag(input [2:0] mi);   // doubled E2M1 magnitude
        case (mi)
            3'd0: dmag = 4'd0;  3'd1: dmag = 4'd1;  3'd2: dmag = 4'd2;  3'd3: dmag = 4'd3;
            3'd4: dmag = 4'd4;  3'd5: dmag = 4'd6;  3'd6: dmag = 4'd8;  default: dmag = 4'd12;
        endcase
    endfunction

    // -- stage A ----------------------------------------------------------------
    // term i: p = 2a_i * 2b_i (0..144, 8 bits); negative terms enter as ~p (9-bit
    // two's complement) plus one count; each 9-bit operand is offset by 2^8
    // (MSB flipped), so the sum is S + 32 * 256 + 0 = S + 2^13 (mod 2^14).
    reg  [34*14-1:0] opa;
    reg  [31:0]      neg;
    reg  [7:0]       p;
    reg  [8:0]       t;
    integer i;
    always @* begin
        for (i = 0; i < 32; i = i + 1) begin
            p = dmag(a[4*i +: 3]) * dmag(b[4*i +: 3]);
            neg[i] = (a[4*i + 3] ^ b[4*i + 3]) && (p != 8'd0);
            t = neg[i] ? ~{1'b0, p} : {1'b0, p};
            opa[14*i +: 14] = {5'd0, ~t[8], t[7:0]};
        end
        opa[14*32 +: 14] = 14'd0;
        opa[14*33 +: 14] = 14'd0;
    end
    // the ones'-complement corrections: popcount(neg) as a 6-bit count
    wire [2*6-1:0] pc2;
    wire [32*6-1:0] negw;
    genvar gi;
    generate
        for (gi = 0; gi < 32; gi = gi + 1) begin : g_n
            assign negw[6*gi +: 6] = {5'd0, neg[gi]};
        end
    endgenerate
    ot_hdc_v41x_csa #(.N(32), .M(2), .W(6)) u_pc (.d(negw), .q(pc2));
    wire [34*14-1:0] opall = {{8'd0, pc2[11:6]}, {8'd0, pc2[5:0]}, opa[32*14-1:0]};
    wire [4*14-1:0]  qa;
    ot_hdc_v41x_csa #(.N(34), .M(4), .W(14)) u_ca (.d(opall), .q(qa));
    wire signed [9:0] ea = $signed({2'b00, ua}) + $signed({2'b00, ub}) - 10'sd256;
    wire refa = (ua >= 8'd253) || (ub >= 8'd253);
    reg [4*14-1:0] ra;
    reg signed [9:0] rea;
    reg rrefa;
    always @(posedge clk) begin
        ra <= qa;
        rea <= ea;
        rrefa <= refa;
    end

    // -- stage B ----------------------------------------------------------------
    wire [2*14-1:0] qb;
    ot_hdc_v41x_csa #(.N(4), .M(2), .W(14)) u_cb (.d(ra), .q(qb));
    wire [13:0] sb = (qb[13:0] + qb[27:14]) ^ 14'h2000;     // remove the 2^13 offset
    reg signed [13:0] rs;
    reg signed [9:0]  reb;
    reg rrefb;
    always @(posedge clk) begin
        rs <= sb;
        reb <= rea;
        rrefb <= rrefa;
    end

    // -- stage C: S * 2^E to binary32 ------------------------------------------
    wire        sg = rs[13];
    wire [12:0] mg = sg ? (~rs[12:0] + 13'd1) : rs[12:0];   // |S| <= 4608 < 2^13
    reg  [3:0]  lz;
    integer kq;
    always @* begin
        lz = 4'd13;
        for (kq = 0; kq < 13; kq = kq + 1) if (mg[kq]) lz = 4'd12 - kq[3:0];
    end
    wire [12:0]       mn = mg << lz;                         // leading one at bit 12
    wire signed [11:0] be = $signed({{2{reb[9]}}, reb}) + 12'sd139 - $signed({8'd0, lz});  // 12 - lz + E + 127
    wire signed [11:0] kk = $signed({{2{reb[9]}}, reb}) + 12'sd149;   // subnormal: F = mg * 2^kk
    reg  [23:0] f;                                          // subnormal significand (2^23 = min normal)
    reg  [31:0] yc;
    reg         oc;
    wire [11:0] nk = -kk;
    reg  [3:0]  sh;
    reg  [15:0] qt, rem, half;
    always @* begin
        f = 24'd0;
        sh = 4'd0; qt = 16'd0; rem = 16'd0; half = 16'd0;
        if (kk >= 0) begin
            f = {11'd0, mg} << kk[4:0];                      // be <= 0 bounds kk <= 22 - msb
        end else begin
            sh = (nk > 12'd14) ? 4'd14 : nk[3:0];          // |S| < 2^13: a shift of 14 leaves < 1/2
            qt = {3'd0, mg} >> sh;
            rem = {3'd0, mg} & ((16'd1 << sh) - 16'd1);
            half = 16'd1 << (sh - 4'd1);
            f = {8'd0, qt} + ((rem > half || (rem == half && qt[0])) ? 24'd1 : 24'd0);
        end
        oc = rrefb || (mg != 0 && be >= 12'sd255);
        if (mg == 13'd0) yc = 32'd0;
        else if (be >= 12'sd1) yc = {sg, be[7:0], mn[11:0], 11'd0};
        else if (f == 24'd0) yc = 32'd0;
        else yc = {sg, 7'd0, f};
        if (oc) yc = 32'd0;
    end
    always @(posedge clk) begin
        y <= yc;
        ovf <= oc;
    end
endmodule

// ---------------------------------------------------------------------------
// to_bf16 (hdc_golden: RNE on the bits, low 16 bits dropped) and its overflow.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_bf16 (
    input  wire [31:0] x,
    output wire [15:0] y,
    output wire        ovf     // a finite x rounded to an infinity
);
    wire [32:0] r = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
    assign y = r[31:16];
    assign ovf = (y[14:7] == 8'hFF);
endmodule

// ---------------------------------------------------------------------------
// term = to_bf16(mul(max(a, 0), w)) for BF16 a (the head score) and w (the
// head weight); binary32 multiply semantics of hdc_golden.mul (RNE, gradual
// underflow, a zero result +0) followed by to_bf16 -- two roundings where the
// binary32 product is subnormal, one (to BF16) elsewhere, since an 8 x 8-bit
// product is exact in binary32's significand.  LATENCY 2.  `ovf`: a product
// past the binary32 range, or one to_bf16 rounds to infinity.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_bmul (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] w,
    output reg  [15:0] y,
    output reg         ovf
);
    // -- stage 1: ReLU, significands, exact product, exponent -------------------
    wire        az = a[15] || (a[14:0] == 15'd0);
    wire        wz = (w[14:0] == 15'd0);
    wire [7:0]  ma = {a[14:7] != 8'd0, a[6:0]};
    wire [7:0]  mw = {w[14:7] != 8'd0, w[6:0]};
    wire [8:0]  ea = (a[14:7] == 8'd0) ? 9'd1 : {1'b0, a[14:7]};
    wire [8:0]  ew = (w[14:7] == 8'd0) ? 9'd1 : {1'b0, w[14:7]};
    reg  [15:0] rp;
    reg  signed [10:0] re;           // value = P * 2^(ea + ew - 268)
    reg         rs, rz;
    always @(posedge clk) begin
        rp <= ma * mw;
        re <= $signed({2'b00, ea}) + $signed({2'b00, ew}) - 11'sd268;
        rs <= w[15];
        rz <= az || wz;
    end

    // -- stage 2: binary32 encode (subnormal RNE), to_bf16, overflow -------------
    reg  [4:0]  lz;
    integer kq;
    always @* begin
        lz = 5'd16;
        for (kq = 0; kq < 16; kq = kq + 1) if (rp[kq]) lz = 5'd15 - kq[4:0];
    end
    wire [15:0]        pn = rp << lz;
    wire signed [11:0] be = $signed({re[10], re}) + 12'sd142 - $signed({7'd0, lz});   // 15 - lz + E + 127
    wire signed [11:0] kk = $signed({re[10], re}) + 12'sd149;
    reg  [23:0] f;
    reg  [31:0] x;
    wire [11:0] nk = -kk;
    reg  [4:0]  sh;
    reg  [16:0] qt, rem, half;
    reg         o32;
    always @* begin
        f = 24'd0; sh = 5'd0; qt = 17'd0; rem = 17'd0; half = 17'd0;
        if (kk >= 0) begin
            f = {8'd0, rp} << kk[4:0];
        end else begin
            sh = (nk > 12'd17) ? 5'd17 : nk[4:0];          // |P| < 2^16: a shift of 17 leaves < 1/2
            qt = {1'b0, rp} >> sh;
            rem = {1'b0, rp} & ((17'd1 << sh) - 17'd1);
            half = 17'd1 << (sh - 5'd1);
            f = {7'd0, qt} + ((rem > half || (rem == half && qt[0])) ? 24'd1 : 24'd0);
        end
        o32 = !rz && (be >= 12'sd255);
        if (rz || rp == 16'd0) x = 32'd0;
        else if (be >= 12'sd1) x = {rs, be[7:0], pn[14:0], 8'd0};
        else if (f == 24'd0) x = 32'd0;
        else x = {rs, 7'd0, f};
    end
    wire [15:0] yb;
    wire        ob;
    ot_hdc_v41x_bf16 u_b (.x(x), .y(yb), .ovf(ob));
    always @(posedge clk) begin
        y <= (o32 || ob) ? 16'd0 : yb;
        ovf <= o32 || ob;
    end
endmodule
