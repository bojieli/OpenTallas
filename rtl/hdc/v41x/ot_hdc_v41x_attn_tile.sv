`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Attention-engine TILE of the re-specified DeepSeek-V4.1-Flash decode die
// (docs/ARCH_SPEC_V41.md section 6 item 4): H heads x TD products per cycle,
// every product BF16 x (dequantised FP8/FP4 KV element) -> binary32, summed
// by the R-ARITH contract of tools/hdc_golden_v41.py (chunk8):
//
//   out[h] = csum_k( mul(A[h][k], B[k]) ),  k = 0 .. TD-1
//
// csum = TD/8 contiguous chunks of 8, each summed sequentially from +0, the
// chunk sums added by a pairwise tree.  TD/8 is a power of two, so the tile's
// output is one aligned node of the golden's padded tree and tiles combine by
// the same tree (q.k: the slices of a row) or by the binary-counter merge
// (p.v: the row blocks) -- see ot_hdc_v41x_attn.sv.
//
// ONE datapath serves both products of attention:
//   q.k  A = q[h][64 dims of a slice] (stationary for the layer),
//        B = one KV row's 64 elements            -> a partial score s[h, row]
//   p.v  A = to_bf16(p)[h][64 rows of a block] (stationary for DPT beats),
//        B = one dim of the block's 64 KV rows    -> a partial pv[h, dim]
//
// STATIONARY OPERAND A: NBANK banks of H x TD BF16.  Load port: one word of TD
// BF16 per cycle into bank ld_bank, group ld_grp (0 .. H-1):
//   ld_mode 0 (q)  A[ld_grp][k]        = ld_w[k]                (one head)
//   ld_mode 1 (p)  A[h][R*ld_grp + j]   = ld_w[j*H + h], R = TD/H (R rows x H heads)
// PWORDS = 2 (p mode only): ld_w carries two words, the low TD*16 bits the
// group ld_grp, the high TD*16 bits the group ld_grp + 1 when ld_w2v is set.
// The two groups are disjoint stationary rows, so each position still has one
// write source per cycle (no double write of a cell); ld_w2v = 0 leaves the
// rows of group ld_grp + 1 untouched whatever the high bits hold.  q mode uses
// the low word only.  PWORDS = 1 is the original single-word port.
// The bank a beat reads travels with the beat (per chunk position, skewed as
// its operands are), so a bank may be reloaded while late positions of an
// earlier beat still read another bank; the engine's controller keeps the
// write-after-read distance (ot_hdc_v41x_attn.sv).
//
// ISSUE PORT: iv, ibank, ib[TD x 18]: per element {pad, fmt, code[7:0],
// scale[7:0]} in the KV row's STORED format, dequantised exactly here:
//   fmt 0  E4M3 code x 2^(scale - 127)   (window rows, UE8M0 per 32)
//   fmt 1  E2M1 code (low nibble) x E4M3 scale   (compressed rows, per 16)
// -- the golden's qdq_fp8 / qdq_fp4_e4m3 values, every one exact in BF16.
// `pad` marks an element past the row count: its product is +0, never a
// fault, whatever the stale A holds.
//
// CHUNK CHAIN: the 8 products of a chunk enter one sequential chain of 7
// binary32 adders (ot_hdc_v41x_qaddl, FPL cycles each: 3 = ot_hdc_qadd as
// built, 7 = ot_hdc_fp32_add_lat for the 1.2 GHz streaming domain); product i
// of the chunk is issued FPL*(i-1) cycles after product 0, by skewing the B
// element (shared by all H heads) and the bank select, not the per-head
// product.  The chunk's first term needs no adder: add(+0, p) = p for every
// canonical p.  The chain is a recurrence only along one beat's chunk; beats
// are independent, so II stays 1 at every FPL.
//
// Timing, a beat sampled at edge 0: R0 input register (1), dequant (2),
// multiply FML (3 as built), chain 7*FPL, tree FPL*log2(TD/8), output
// register: ov at LAT = 3 + FML + 7*FPL + FPL*log2(TD/8) (36 at TD = 64 and
// FML = FPL = 3).  Fully pipelined, II = 1, no stall: flow control is by issue
// credit in the engine.  A build with FPL > 3 adds
// rtl/hdc/ot_hdc_fp32_add_lat.sv to its sources.
//
// Faults fail closed: a nonfinite A, an out-of-domain KV element (a NaN
// code, a dequantised value outside the binary32 normal range), a product or
// sum overflow raises oflt[h] with its output, exactly where the golden's
// value would not be finite.
// ---------------------------------------------------------------------------

module ot_hdc_v41x_dly #(parameter integer W = 1, parameter integer D = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else begin : g_reg
            reg [W-1:0] r [0:D-1];
            integer i;
            always @(posedge clk) begin
                r[0] <= d;
                for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
            end
            assign q = r[D-1];
        end
    endgenerate
endmodule

// Valid delay line with reset.
module ot_hdc_v41x_vdly #(parameter integer D = 1) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
    reg [D:0] r;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r[D:1] <= {D{1'b0}};
        else for (i = 1; i <= D; i = i + 1) r[i] <= (i == 1) ? d : r[i-1];
    end
    assign q = r[D];
endmodule

// ---------------------------------------------------------------------------
// BF16 x BF16 -> binary32, IEEE RNE with gradual underflow, canonical +0,
// LATENCY ML (3 as built, up to 6) -- hdc_golden.mul on BF16 operands.  The
// 8 x 8 significand product is exact in binary32 whenever the result is
// normal; only a subnormal result rounds.  A nonfinite operand or an
// overflowing result raises flt with y = 0 (as ot_hdc_qmul).  `pad` forces
// y = +0, no fault.  Cuts (registers only; the value is the same at every ML):
//   ML >= 4  stage 3 after the subnormal alignment shifts
//   ML >= 5  stage 2 after the leading-zero count
//   ML >= 6  an operand register ahead of stage 1 (the bank-select mux and the
//            skewed element, both high fan-out, get a cycle of their own)
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_bmul #(
    parameter integer ML = 3
) (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        pad,
    output reg  [31:0] y,
    output reg         flt
);
    // -- operand register (ML >= 6)
    wire [15:0] oa, ob;
    wire        opad;
    ot_hdc_v41x_dly #(.W(33), .D((ML >= 6) ? 1 : 0)) u_cut0 (.clk(clk), .d({a, b, pad}), .q({oa, ob, opad}));
    // -- stage 1: decode, 8x8 product, exponent sum
    wire [7:0] ea = oa[14:7];
    wire [7:0] eb = ob[14:7];
    wire [7:0] ma = {(ea != 8'd0), oa[6:0]};
    wire [7:0] mb = {(eb != 8'd0), ob[6:0]};
    wire [8:0] esum_c = {1'b0, (ea == 8'd0) ? 8'd1 : ea} + {1'b0, (eb == 8'd0) ? 8'd1 : eb};
    wire nonfin_c = !opad && ((ea == 8'hff) || (eb == 8'hff));
    wire zero_c = opad || (ma == 8'd0) || (mb == 8'd0);
    reg [15:0] s1_p;
    reg [8:0]  s1_esum;
    reg        s1_sign, s1_zero, s1_nonfin;
    always @(posedge clk) begin
        s1_p <= ma * mb;
        s1_esum <= esum_c;
        s1_sign <= oa[15] ^ ob[15];
        s1_zero <= zero_c;
        s1_nonfin <= nonfin_c;
    end

    // -- stage 2: normalise; normal encoding; subnormal shift amounts
    //: value = P * 2^(esum - 268); msb at 15 - lz; biased exponent
    //: esum - 126 - lz; a subnormal result is P * 2^(esum - 119) in units of
    //: 2^-149, i.e. P << (esum - 119) or P >> (119 - esum) rounded.
    reg [3:0] lz0;
    integer i;
    always @* begin
        lz0 = 4'd15;
        for (i = 0; i < 16; i = i + 1)
            if (s1_p[i]) lz0 = 4'd15 - i[3:0];
    end
    wire [3:0]  lz;
    wire [15:0] c1_p;
    wire [8:0]  c1_esum;
    wire        c1_sign, c1_zero, c1_nonfin;
    ot_hdc_v41x_dly #(.W(4 + 16 + 9 + 3), .D((ML >= 5) ? 1 : 0)) u_cut2 (.clk(clk),
        .d({lz0, s1_p, s1_esum, s1_sign, s1_zero, s1_nonfin}), .q({lz, c1_p, c1_esum, c1_sign, c1_zero, c1_nonfin}));
    wire [15:0] pn = c1_p << lz;
    wire signed [10:0] biased = $signed({2'b00, c1_esum}) - 11'sd126 - $signed({7'd0, lz});
    wire normal_c = biased >= 11'sd1;
    wire over_c = biased >= 11'sd255;
    wire signed [10:0] lsh = $signed({2'b00, c1_esum}) - 11'sd119;   // left shift if >= 0
    reg [31:0] s2_code_n;
    reg [15:0] s2_p;
    reg [4:0]  s2_lsh;            // 0 .. 22 when used
    reg [4:0]  s2_rsh;            // 1 .. 17 (clamped) when used
    reg        s2_left, s2_normal, s2_over, s2_sign, s2_zero, s2_nonfin;
    always @(posedge clk) begin
        s2_code_n <= {c1_sign, biased[7:0], pn[14:0], 8'd0};
        s2_p <= c1_p;
        s2_left <= !lsh[10];
        s2_lsh <= (lsh > 11'sd22) ? 5'd22 : lsh[4:0];
        s2_rsh <= (lsh < -11'sd17) ? 5'd17 : (-lsh[4:0]);
        s2_normal <= normal_c;
        s2_over <= over_c;
        s2_sign <= c1_sign;
        s2_zero <= c1_zero;
        s2_nonfin <= c1_nonfin;
    end

    // -- stage 3: subnormal alignment [cut, ML >= 4] and rounding, select, encode
    wire [22:0] lft0 = {7'd0, s2_p} << s2_lsh;
    wire [15:0] rgt0 = s2_p >> s2_rsh;
    wire [31:0] below = {s2_p, 16'd0} >> s2_rsh;       // bits shifted out, MSB first at [15]
    wire [22:0] lft;
    wire [15:0] rgt;
    wire [31:0] c3_code_n;
    wire rb, st, c3_left, c3_normal, c3_over, c3_sign, c3_zero, c3_nonfin;
    ot_hdc_v41x_dly #(.W(23 + 16 + 32 + 8), .D((ML >= 4) ? 1 : 0)) u_cut3 (.clk(clk),
        .d({lft0, rgt0, s2_code_n, below[15], |below[14:0], s2_left, s2_normal, s2_over, s2_sign, s2_zero, s2_nonfin}),
        .q({lft, rgt, c3_code_n, rb, st, c3_left, c3_normal, c3_over, c3_sign, c3_zero, c3_nonfin}));
    wire [23:0] sub_f = c3_left ? {1'b0, lft} : ({8'd0, rgt} + {23'd0, rb && (st || rgt[0])});
    wire [31:0] code_s = {c3_sign, 7'd0, sub_f};
    always @(posedge clk) begin
        if (c3_nonfin) begin
            y <= 32'd0; flt <= 1'b1;
        end else if (c3_zero) begin
            y <= 32'd0; flt <= 1'b0;
        end else if (c3_normal) begin
            y <= c3_over ? 32'd0 : c3_code_n; flt <= c3_over;
        end else begin
            y <= (sub_f == 24'd0) ? 32'd0 : code_s; flt <= 1'b0;
        end
    end
endmodule

// ---------------------------------------------------------------------------
// KV element dequantiser (combinational): stored code + scale -> BF16, exact.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_deq (
    input  wire [17:0] e,          // {pad, fmt, code[7:0], scale[7:0]}
    output reg  [15:0] y,
    output reg         flt
);
    wire pad = e[17];
    wire fmt = e[16];
    wire [7:0] c = e[15:8];
    wire [7:0] s = e[7:0];
    reg signed [10:0] bx;
    reg [6:0] man;
    reg [5:0] prod;
    reg [2:0] msb;
    reg sgn, nan, zero;
    integer i;
    always @* begin
        bx = 11'sd0; man = 7'd0; prod = 6'd0; msb = 3'd0; sgn = 1'b0; nan = 1'b0; zero = 1'b0;
        if (!fmt) begin
            // E4M3 code x 2^(s - 127): value = sig * 2^(max(e4,1) - 10 + s - 127)
            sgn = c[7];
            nan = ((c[6:3] == 4'hf) && (c[2:0] == 3'd7)) || (s == 8'hff);
            prod = {2'b00, (c[6:3] != 4'd0), c[2:0]};
            bx = $signed({7'd0, (c[6:3] == 4'd0) ? 4'd1 : c[6:3]}) + $signed({3'd0, s}) - 11'sd137;
        end else begin
            // E2M1 code x E4M3 scale: sigA (2b) * sigS (4b) * 2^(expA + expS)
            sgn = c[3] ^ s[7];
            nan = (s[6:3] == 4'hf) && (s[2:0] == 3'd7);
            prod = {(c[2:1] != 2'd0), c[0]} * {(s[6:3] != 4'd0), s[2:0]};
            bx = $signed({9'd0, (c[2:1] == 2'd0) ? 2'd1 : c[2:1]}) - 11'sd2
               + $signed({7'd0, (s[6:3] == 4'd0) ? 4'd1 : s[6:3]}) - 11'sd10;
        end
        zero = (prod == 6'd0);
        for (i = 0; i < 6; i = i + 1)
            if (prod[i]) msb = i[2:0];
        // value = 1.f * 2^(msb + bx): biased = msb + bx + 127
        bx = bx + $signed({8'd0, msb}) + 11'sd127;
        man = ({1'b0, prod} << (3'd6 - msb));          // leading one lands at bit 6
        if (pad) begin
            y = 16'd0; flt = 1'b0;
        end else if (nan) begin
            y = 16'd0; flt = 1'b1;
        end else if (zero) begin
            y = {sgn, 15'd0}; flt = 1'b0;
        end else if ((bx < 11'sd1) || (bx > 11'sd254)) begin
            y = 16'd0; flt = 1'b1;                       // outside the quantiser's domain / overflow
        end else begin
            y = {sgn, bx[7:0], man[5:0], 1'b0}; flt = 1'b0;
        end
    end
endmodule

// ---------------------------------------------------------------------------
// One chunk: 8 products (position i issued FPL*(i-1) cycles after position 0)
// summed sequentially: acc = p0; acc = add(acc, p_i), i = 1..7.  LATENCY 7*FPL
// from the products of positions 0/1.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_chunk #(
    parameter integer FPL = 3
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [8*32-1:0] p,
    input  wire [7:0]    pf,
    output wire [31:0]   y,
    output wire          f
);
    wire [8*32-1:0] acc;
    wire [7:0]      af;
    assign acc[31:0] = p[31:0];
    assign af[0] = pf[0];
    genvar gi;
    generate
        for (gi = 1; gi < 8; gi = gi + 1) begin : g_a
            wire [31:0] s;
            wire sf;
            ot_hdc_v41x_qaddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(acc[(gi-1)*32 +: 32]),
                             .b(p[gi*32 +: 32]), .y(s), .fault(sf));
            wire fdq;
            ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(af[gi-1] | pf[gi]), .q(fdq));
            assign acc[gi*32 +: 32] = s;
            assign af[gi] = fdq | sf;
        end
    endgenerate
    assign y = acc[7*32 +: 32];
    assign f = af[7];
endmodule

// ---------------------------------------------------------------------------
// One head of a tile: TD stationary operands (NBANK banks), TD multipliers,
// TD/8 chunk chains, the pairwise tree.  LATENCY FML + 7*FPL + FPL*log2(TD/8)
// from the skewed operands to y (y is the last adder's register).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_hdp #(
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer FPL = 3,
    parameter integer FML = 3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [TD-1:0]     we,
    input  wire [BW-1:0]     wbank,
    input  wire [TD*16-1:0]  wd,
    input  wire [8*BW-1:0]   sk_bank,
    input  wire [TD*18-1:0]  sk_b,
    output wire [31:0]       y,
    output wire              f
);
    localparam integer NC = TD / 8;
    wire [TD*32-1:0] p;
    wire [TD-1:0]    pf;
    genvar gk, gn;
    generate
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_m
            reg [NBANK*16-1:0] ab;
            integer bb;
            always @(posedge clk)
                for (bb = 0; bb < NBANK; bb = bb + 1)
                    if (we[gk] && (wbank == bb)) ab[bb*16 +: 16] <= wd[gk*16 +: 16];
            wire [BW-1:0] bk = sk_bank[(gk % 8)*BW +: BW];
            wire [15:0] av = ab[bk*16 +: 16];
            wire [17:0] be = sk_b[gk*18 +: 18];
            wire mf;
            ot_hdc_v41x_attn_bmul #(.ML(FML)) u_m (.clk(clk), .a(av), .b(be[15:0]), .pad(be[17]), .y(p[gk*32 +: 32]), .flt(mf));
            // dequant fault rides with the product
            wire dfq;
            ot_hdc_v41x_dly #(.W(1), .D(FML)) u_df (.clk(clk), .d(be[16] & ~be[17]), .q(dfq));
            assign pf[gk] = mf | dfq;
        end
        wire [(2*NC-1)*32-1:0] tn;      // heap order: leaves (chunk sums) at NC-1 .. 2NC-2
        wire [2*NC-2:0]        tf;
        for (gn = 0; gn < NC; gn = gn + 1) begin : g_c
            ot_hdc_v41x_attn_chunk #(.FPL(FPL)) u_c (.clk(clk), .rst_n(rst_n), .p(p[gn*256 +: 256]), .pf(pf[gn*8 +: 8]),
                                        .y(tn[(NC-1+gn)*32 +: 32]), .f(tf[NC-1+gn]));
        end
        for (gn = 0; gn < NC - 1; gn = gn + 1) begin : g_node
            wire [31:0] s;
            wire sf;
            ot_hdc_v41x_qaddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(tn[(2*gn+1)*32 +: 32]),
                             .b(tn[(2*gn+2)*32 +: 32]), .y(s), .fault(sf));
            wire fdq;
            ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(tf[2*gn+1] | tf[2*gn+2]), .q(fdq));
            assign tn[gn*32 +: 32] = s;
            assign tf[gn] = fdq | sf;
        end
    endgenerate
    assign y = tn[31:0];
    assign f = tf[0];
endmodule

// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_tile #(
    parameter integer H = 16,          // heads
    parameter integer TD = 64,         // products per head per beat (multiple of 8, TD/8 a power of two)
    parameter integer NBANK = 3,       // stationary-operand banks
    parameter integer BW = 2,          // bank index width
    parameter integer PWORDS = 1,      // p-mode words per load (1 or 2)
    parameter integer FPL = 3,         // binary32 add latency (7: 1.2 GHz streaming domain)
    parameter integer FML = 3          // product latency (ot_hdc_v41x_attn_bmul)
) (
    input  wire              clk,
    input  wire              rst_n,
    // stationary operand load
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,   // second p word valid (PWORDS = 2)
    // issue
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    // result
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      oflt
);
    localparam integer NC = TD / 8;          // chunks
    localparam integer LV = $clog2(NC);      // tree levels
    localparam integer R = TD / H;           // rows per p-load word
    localparam integer LAT_CORE = FML + 7 * FPL + FPL * LV;   // multiply .. tree, from the dequant register

    // -- R0: boundary registers
    reg              r_ld_v, r_ld_mode;
    reg [BW-1:0]     r_ld_bank;
    reg [7:0]        r_ld_grp;
    reg [PWORDS*TD*16-1:0] r_ld_w;
    reg              r_ld_w2v;
    reg              r_iv;
    reg [BW-1:0]     r_ibank;
    reg [TD*18-1:0]  r_ib;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r_ld_v <= 1'b0; r_iv <= 1'b0; end
        else begin r_ld_v <= ld_v; r_iv <= iv; end
    end
    always @(posedge clk) begin
        r_ld_mode <= ld_mode; r_ld_bank <= ld_bank; r_ld_grp <= ld_grp; r_ld_w <= ld_w; r_ld_w2v <= ld_w2v;
        r_ibank <= ibank; r_ib <= ib;
    end

    genvar gh, gk;
    // -- D1: dequantise (shared by all heads)
    reg [TD*18-1:0] d1_b;              // {pad, flt, bf16} per element
    reg [BW-1:0]    d1_bank;
    reg             d1_v;
    generate
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_dq
            wire [15:0] y;
            wire f;
            ot_hdc_v41x_attn_deq u_dq (.e(r_ib[gk*18 +: 18]), .y(y), .flt(f));
            always @(posedge clk) d1_b[gk*18 +: 18] <= {r_ib[gk*18 + 17], f, y};
        end
    endgenerate
    always @(posedge clk) d1_bank <= r_ibank;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) d1_v <= 1'b0;
        else d1_v <= r_iv;
    end

    // -- skew: chunk position i issues FPL*(i-1) cycles after position 0 (0 for i = 0, 1)
    wire [TD*18-1:0] sk_b;
    wire [8*BW-1:0]  sk_bank;
    generate
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_skb
            localparam integer DS = (gk == 0) ? 0 : FPL * (gk - 1);
            ot_hdc_v41x_dly #(.W(BW), .D(DS)) u_d (.clk(clk), .d(d1_bank), .q(sk_bank[gk*BW +: BW]));
        end
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_ske
            localparam integer DS = ((gk % 8) == 0) ? 0 : FPL * ((gk % 8) - 1);
            ot_hdc_v41x_dly #(.W(18), .D(DS)) u_d (.clk(clk), .d(d1_b[gk*18 +: 18]), .q(sk_b[gk*18 +: 18]));
        end
    endgenerate

    // -- per head: multiply, chunk chains, tree (one datapath module per head)
    generate
        for (gh = 0; gh < H; gh = gh + 1) begin : g_h
            wire [TD-1:0]    we;
            wire [TD*16-1:0] wd;
            for (gk = 0; gk < TD; gk = gk + 1) begin : g_w
                if (PWORDS == 1) begin : g_w1
                    assign wd[gk*16 +: 16] = r_ld_mode ? r_ld_w[((gk % R) * H + gh) * 16 +: 16] : r_ld_w[gk * 16 +: 16];
                    assign we[gk] = r_ld_v && (r_ld_mode ? (r_ld_grp == (gk / R)) : (r_ld_grp == gh));
                end else begin : g_w2
                    // row gk is in group gk / R: the low word's group or (ld_w2v) the next one
                    wire lo = (r_ld_grp == (gk / R));
                    wire hi = r_ld_w2v && ((r_ld_grp + 8'd1) == (gk / R));
                    assign wd[gk*16 +: 16] = !r_ld_mode ? r_ld_w[gk * 16 +: 16] :
                                             hi ? r_ld_w[TD * 16 + ((gk % R) * H + gh) * 16 +: 16] :
                                                  r_ld_w[((gk % R) * H + gh) * 16 +: 16];
                    assign we[gk] = r_ld_v && (r_ld_mode ? (lo || hi) : (r_ld_grp == gh));
                end
            end
            wire [31:0] y;
            wire f;
            ot_hdc_v41x_attn_hdp #(.TD(TD), .NBANK(NBANK), .BW(BW), .FPL(FPL), .FML(FML)) u_hdp (
                .clk(clk), .rst_n(rst_n), .we(we), .wbank(r_ld_bank), .wd(wd), .sk_bank(sk_bank), .sk_b(sk_b),
                .y(y), .f(f));
            always @(posedge clk) begin
                oy[gh*32 +: 32] <= y;
                oflt[gh] <= f;
            end
        end
    endgenerate

    wire v_core;
    ot_hdc_v41x_vdly #(.D(LAT_CORE)) u_v (.clk(clk), .rst_n(rst_n), .d(d1_v), .q(v_core));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else ov <= v_core;
    end
endmodule

// ---------------------------------------------------------------------------
// Fault-reporting binary32 add of the attention datapath: ot_hdc_qadd (LAT 3,
// ot_hdc_fp32_add_fast) or, for LAT > 3, ot_hdc_fp32_add_lat -- bit for bit the
// same adder, cut deeper (rtl/hdc/ot_hdc_fp32_add_lat.sv, which a LAT > 3 build
// adds to its sources).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_qaddl #(
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
    generate
        if (LAT == 3) begin : g_fast
            ot_hdc_qadd u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y), .fault(fault));
        end else begin : g_lat
            wire [1:0] err;
            wire vo;
            // a LAT-3 build does not list ot_hdc_fp32_add_lat.sv: this branch is not elaborated then, and the
            // lint's timescale check must not trip on the unresolved name
            // verilator lint_off TIMESCALEMOD
            ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y),
                                                .err(err), .valid_out(vo));
            // verilator lint_on TIMESCALEMOD
            assign fault = vo && (err != 2'd0);
        end
    endgenerate
endmodule
