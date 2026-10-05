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
//   A  signed products from a 7-input table, offset-binary operands (no sign
//      extension); CSA 32 -> 7
//   B  CSA 7 -> 2, carry-propagate add: S; |S|; the exponent decisions that
//      do not need the leading-zero count
//   C  leading-zero count, normal pack or subnormal right shift + RNE
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
    // term i: the signed product (+-2a_i * 2b_i, |.| <= 144) straight from a
    // 7-input table (sign, two 3-bit magnitudes) as 9-bit two's complement, offset
    // by 2^8 (MSB flipped): the sum of the 32 operands is S + 2^13 (mod 2^14).
    // A carry-save tree takes them to 7 rows here; stage B finishes it.
    function automatic [8:0] sprod(input [6:0] x);     // {sign, ma, mb}
        reg [7:0] pm;
        begin
            pm = dmag(x[5:3]) * dmag(x[2:0]);
            sprod = x[6] ? (9'd0 - {1'b0, pm}) : {1'b0, pm};
        end
    endfunction
    function automatic [128*9-1:0] mktab(input integer dummy);
        integer j;
        begin
            for (j = 0; j < 128; j = j + 1) mktab[9*j +: 9] = sprod(j[6:0]) ^ 9'h100;
        end
    endfunction
    localparam [128*9-1:0] TAB = mktab(0);
    reg  [32*14-1:0] opa;
    reg  [8:0]       t;
    integer i;
    always @* begin
        for (i = 0; i < 32; i = i + 1) begin
            t = TAB[9 * {a[4*i + 3] ^ b[4*i + 3], a[4*i +: 3], b[4*i +: 3]} +: 9];
            opa[14*i +: 14] = {5'd0, t};
        end
    end
    wire [7*14-1:0]  qa;
    ot_hdc_v41x_csa #(.N(32), .M(7), .W(14)) u_ca (.d(opa), .q(qa));
    wire signed [9:0] ea = $signed({2'b00, ua}) + $signed({2'b00, ub}) - 10'sd256;
    wire refa = (ua >= 8'd253) || (ub >= 8'd253);
    reg [7*14-1:0] ra;
    reg signed [9:0] rea;
    reg rrefa;
    always @(posedge clk) begin
        ra <= qa;
        rea <= ea;
        rrefa <= refa;
    end

    // -- stage B: CSA 7 -> 2, the add, |S|, the exponent decisions that do not
    //    depend on the leading-zero count ----------------------------------------
    wire [2*14-1:0] qb;
    ot_hdc_v41x_csa #(.N(7), .M(2), .W(14)) u_cb (.d(ra), .q(qb));
    wire [13:0] sb = (qb[13:0] + qb[27:14]) ^ 14'h2000;     // remove the 2^13 offset
    wire [12:0] mb = sb[13] ? (~sb[12:0] + 13'd1) : sb[12:0];   // |S| <= 4608 < 2^13
    wire signed [11:0] kb = $signed({{2{rea[9]}}, rea}) + 12'sd149;      // subnormal: F = |S| * 2^kb
    wire [11:0] nkb = -kb;
    reg         rsg, rkneg;
    reg  [12:0] rm;
    reg  [4:0]  rkl;                 // kb >= 0: left shift (<= 22 where it applies)
    reg  [3:0]  rkr;                 // kb < 0: right shift, clipped at 14 (|S| < 2^13: all below 1/2)
    reg signed [11:0] rnl, rov;      // normal iff lz <= E + 138; overflow iff lz <= E - 116
    reg signed [9:0] reb;
    reg rrefb;
    always @(posedge clk) begin
        rsg <= sb[13];
        rm <= mb;
        rkneg <= kb[11];
        rkl <= kb[4:0];
        rkr <= (nkb > 12'd14) ? 4'd14 : nkb[3:0];
        rnl <= $signed({{2{rea[9]}}, rea}) + 12'sd138;
        rov <= $signed({{2{rea[9]}}, rea}) - 12'sd116;
        reb <= rea;
        rrefb <= rrefa;
    end

    // -- stage C: leading-zero count, normal pack or subnormal shift + RNE --------
    reg  [3:0]  lz;
    integer kq;
    always @* begin
        lz = 4'd13;
        for (kq = 0; kq < 13; kq = kq + 1) if (rm[kq]) lz = 4'd12 - kq[3:0];
    end
    wire [12:0]       mn = rm << lz;                         // leading one at bit 12
    wire [7:0]        bef = reb[7:0] + 8'd139 - {4'd0, lz};  // biased exponent (mod 256) where normal
    wire              nrm = $signed({8'd0, lz}) <= rnl;
    wire              ovc = (rm != 13'd0) && ($signed({8'd0, lz}) <= rov);
    wire [26:0]       xr = {rm, 14'd0} >> rkr;
    wire [12:0]       qt = xr[26:14];
    wire              g = xr[13], st = |xr[12:0];
    wire [23:0]       fr = {11'd0, qt} + ((g && (st || qt[0])) ? 24'd1 : 24'd0);
    wire [23:0]       fl = {11'd0, rm} << rkl;
    wire [23:0]       f = rkneg ? fr : fl;
    reg  [31:0] yc;
    reg         oc;
    always @* begin
        oc = rrefb || ovc;
        if (rm == 13'd0 || oc) yc = 32'd0;
        else if (nrm) yc = {rsg, bef, mn[11:0], 11'd0};
        else if (f == 24'd0) yc = 32'd0;
        else yc = {rsg, 7'd0, f};
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
// product is exact in binary32's significand.  LATENCY 3.  `ovf`: a product
// past the binary32 range, or one to_bf16 rounds to infinity.
//   1  ReLU, significands, the exact 16-bit product, exponent sums
//   2  leading-zero count and normalise (normal result); the subnormal
//      alignment shift with guard and sticky
//   3  BF16 RNE of the normal significand, or binary32-subnormal RNE then BF16
//      RNE of the subnormal one; pack, refuse
// ---------------------------------------------------------------------------
module ot_hdc_v41x_bmul (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] w,
    output reg  [15:0] y,
    output reg         ovf
);
    // -- stage 1 --------------------------------------------------------------------
    wire        az = a[15] || (a[14:0] == 15'd0);
    wire        wz = (w[14:0] == 15'd0);
    wire [7:0]  ma = {a[14:7] != 8'd0, a[6:0]};
    wire [7:0]  mw = {w[14:7] != 8'd0, w[6:0]};
    wire [8:0]  ea = (a[14:7] == 8'd0) ? 9'd1 : {1'b0, a[14:7]};
    wire [8:0]  ew = (w[14:7] == 8'd0) ? 9'd1 : {1'b0, w[14:7]};
    wire signed [11:0] e1 = $signed({3'b000, ea}) + $signed({3'b000, ew}) - 12'sd268;   // value = P * 2^e1
    wire signed [11:0] k1 = e1 + 12'sd149;                  // binary32 subnormal: F = P * 2^k1
    wire [11:0] nk1 = -k1;
    reg  [15:0] rp;
    reg  signed [11:0] re;
    reg         rs, rz, rkneg;
    reg  [4:0]  rkl, rkr;
    always @(posedge clk) begin
        rp <= ma * mw;
        re <= e1;
        rs <= w[15];
        rz <= az || wz;
        rkneg <= k1[11];
        rkl <= k1[4:0];
        rkr <= (nk1 > 12'd17) ? 5'd17 : nk1[4:0];
    end

    // -- stage 2 --------------------------------------------------------------------
    reg  [4:0]  lz;
    integer kq;
    always @* begin
        lz = 5'd16;
        for (kq = 0; kq < 16; kq = kq + 1) if (rp[kq]) lz = 5'd15 - kq[4:0];
    end
    wire [15:0]        pn = rp << lz;
    wire signed [11:0] be = re + 12'sd142 - $signed({7'd0, lz});   // 15 - lz + e1 + 127
    wire [32:0]        xr = {rp, 17'd0} >> rkr;
    wire [23:0]        fl = {8'd0, rp} << rkl;
    reg  [15:0] s_pn;
    reg  [7:0]  s_be;
    reg         s_nrm, s_o32, s_zero, s_sign, s_kneg;
    reg  [16:0] s_q;               // subnormal (right shift): integer part
    reg         s_g, s_st;
    reg  [23:0] s_fl;              // subnormal (left shift): exact
    always @(posedge clk) begin
        s_pn <= pn;
        s_be <= be[7:0];
        s_nrm <= (be >= 12'sd1);
        s_o32 <= !rz && (rp != 16'd0) && (be >= 12'sd255);
        s_zero <= rz || (rp == 16'd0);
        s_sign <= rs;
        s_kneg <= rkneg;
        s_q <= xr[32:17] ;
        s_g <= xr[16];
        s_st <= |xr[15:0];
        s_fl <= fl;
    end

    // -- stage 3 --------------------------------------------------------------------
    // normal: BF16 RNE of the 16-bit significand (binary32 holds it exactly)
    wire [8:0]  nr = {1'b0, s_pn[15:8]} + ((s_pn[7] && ((|s_pn[6:0]) || s_pn[8])) ? 9'd1 : 9'd0);
    wire [8:0]  nbe = {1'b0, s_be} + {8'd0, nr[8]};           // a carry renormalises: 1.0 x 2^(e+1)
    wire [15:0] ynorm = {s_sign, nbe[7:0], nr[8] ? 7'd0 : nr[6:0]};
    wire        onorm = (nbe >= 9'd255);
    // subnormal: binary32 RNE at 2^-149, then to_bf16's RNE at 2^-133
    wire [23:0] fr = {7'd0, s_q} + ((s_g && (s_st || s_q[0])) ? 24'd1 : 24'd0);
    wire [23:0] f = s_kneg ? fr : s_fl;
    wire [32:0] fb = {9'd0, f} + 33'h7FFF + {32'd0, f[16]};
    wire [15:0] ysub = (f == 24'd0) ? 16'd0 : {s_sign, fb[30:16]};
    always @(posedge clk) begin
        ovf <= s_o32 || (!s_zero && s_nrm && onorm);
        y <= (s_zero || s_o32 || (s_nrm && onorm)) ? 16'd0 : (s_nrm ? ynorm : ysub);
    end
endmodule
