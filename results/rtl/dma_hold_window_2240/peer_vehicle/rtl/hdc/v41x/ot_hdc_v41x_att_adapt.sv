`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x, ME
// slot engine 2, X_ATT): runs the ME's KV-sourced attention ops -- the scores
// q.k and the weighted sum p.v (tools/hdc_program_v41.py Builder.attention) --
// on the attention engine ot_hdc_v41x_attn, keeping the as-built matrix
// engine's contract toward the slot (ot_hdc_v41_matvec: go / ready / idle, the
// me_* fields, the G vector-memory x read ports, the KV read port and the G
// masked word writes).
//
// THE OPS (Machine.me_lane, me_wsrc = 1, class "att": csum of the products in K
// order; x BF16-rounded, me_round = 1).  A KV op reads KV word
//     wb + t*ts + k*ks            (js = 0: every slot reads the same KV word)
// whose lane l is output index o = t*16 + l of tile t (t < me_tiles * (G >> hg)),
// the op's heads are hh = h*IL + j (head group h < 2^hg, slot j < IL) with x at
//     xb + h*xcs + k*xks + j*xjs,
// and result o of head hh goes to lane l of word ob + t*ots + h*ogs + j*ojs
// (me_mmode = 1: o < me_nout).  Two shapes:
//   q.k  (ks = 1)  k = dim (K = D = 32), o = KV row (me_nout = T rows): s[hh][row]
//   p.v  (ks > 1)  k = KV row (K = T), o = dim (me_nout = D = 32):       pv[hh][dim]
// Both are exactly the engine's products: q.k is dots(q, kv) csum over the D dims,
// p.v is dots(bf16(p), kv^T) csum over the T rows in row order.
//
// SEQUENCE per op:
//   LDKV  in reduced mode, the op's KV words through the G read ports, into a
//         BF16 row buffer. Full shape bypasses this step and consumes the
//         die service's chronological stored-format rows directly;
//   LDX   its x (q heads, or p rows) through the G x ports, BF16-rounded (RNE, as
//         hdc_golden.to_bf16);
//   JOBS  one engine job per H heads: q (the op's q heads, or zeros for p.v),
//         the T stored-format rows (re-encoded only in reduced mode), then the
//         probabilities (the op's p, or zeros for q.k); the half of the job the op
//         does not need is computed on zeros and discarded.  Results land in a
//         local result buffer (credits returned at once);
//   WR    the result words through the G masked write ports.
//
// STORED FORMAT (exact reduced-mode re-encode). Every KV row the program writes is a
// quantise-dequantise: window rows FP8 E4M3 x 2^e (UE8M0 per 32,
// hdc_golden_v41.qdq_fp8), gathered compressed rows E2M1 x E4M3 scale per 16
// (qdq_fp4_e4m3).  The adapter finds, per row, a stored word whose dequantised
// value is the SAME BF16 value element for element (the tile dequantises
// exactly), so the engine computes the golden's products bit for bit:
//   FP8: M = max |v|, E its exponent; e = E - 8 if M's significand <= 1.75 else
//        E - 7 (the largest scale-down that keeps |v|/2^e <= 448: never below the
//        quantiser's own exponent, so every element stays on the E4M3 grid);
//   FP4 (when FP8 is not exact): per 16, s = M / q for q = 6, 4, 3, 2, 1.5, 1, 0.5
//        (the first that is an E4M3 value putting every element on the E2M1 grid;
//        the quantiser's own amax rule makes q = 6 the one that fits).
// A row that neither encodes exactly faults (fail closed).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_att_adapt #(
    parameter integer W     = 16,          // lanes per KV / result word
    parameter integer G     = 4,           // read / write ports (the as-built ME's groups)
    parameter integer IL    = 8,           // slots (heads per head group)
    parameter integer AW    = 24,
    parameter integer NW    = 16,
    parameter integer MP    = 1,
    // the engine
    parameter integer H     = 16,          // heads per job
    parameter integer D     = 32,          // head dim
    parameter integer TD    = 32,          // tile width
    parameter integer NL    = 4,           // rows per cycle
    parameter integer TROWS = 160,         // rows per job (>= the attention rows T_MAX)
    parameter integer NHMAX = 32,          // heads per op
    parameter bit PACKED_KV = 0            // full-shape die supplies stored rows
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [1:0]        i_hg,
    input  wire [AW-1:0]     i_ogs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire [2:0]        i_m,
    // KV SRAM
    output reg               kv_re,
    output reg  [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    // Ordered packed KV rows from the die. A beat is four chronological rows
    // in the engine's 265-bit/group stored format. Used only with PACKED_KV.
    input  wire              packed_kv_v,
    output wire              packed_kv_ready,
    input  wire [NL-1:0]     packed_kv_m,
    input  wire [NL*(D/32)*265-1:0] packed_kv_w,
    input  wire              packed_kv_fault,
    // vector memory x reads (element), result writes (masked words)
    output reg  [MP*G-1:0]   x_re,
    output reg  [MP*G*AW-1:0] x_addr,
    input  wire [MP*G*32-1:0] x_q,
    output reg  [MP*G-1:0]   o_we,
    output reg  [MP*G*AW-1:0] o_addr,
    output reg  [MP*G*W-1:0] o_mask,
    output reg  [MP*G*W*32-1:0] o_data,
    output reg               fault
);
    localparam integer GW   = 265;
    localparam integer NG   = D / 32;               // group words per row
    localparam integer ROWW = NG * GW;
    localparam integer R    = TD / H;               // rows per probability word
    localparam integer S    = D / TD;
    localparam integer NT   = NL * S;
    localparam integer DPT  = D / NT;
    localparam [2:0] A_IDLE = 0, A_LDKV = 1, A_LDX = 2, A_JOB = 3, A_RUN = 4, A_WR = 5;

    // ---------------------------------------------------------------- op registers
    reg  [2:0]    st;
    reg           pv;                               // p.v (else q.k)
    reg  [NW-1:0] nout, kk, ntile;
    reg  [AW-1:0] wb, ts, ks, xb, xks, xjs, xcs, ogs, ob, ots, ojs;
    reg  [NW-1:0] T;                                // KV rows
    reg  [7:0]    nhd;                              // heads of the op
    reg           bad;                              // an op the adapter cannot run
    assign ready = (st == A_IDLE);
    wire [NW-1:0] c_ntile = i_tiles * (G >> i_hg);
    wire [7:0]    c_nhd = IL << i_hg;

    // ---------------------------------------------------------------- buffers
    reg [15:0] xbuf   [0:NHMAX*TROWS-1];            // [head][k] BF16 (q dims or p rows)
    reg [31:0] obuf   [0:NHMAX*TROWS-1];            // [head][o] binary32 results

    // ---------------------------------------------------------------- loads (G a cycle, data 2 cycles later)
    reg  [31:0] lc;                                 // linear load counter
    reg  [31:0] lend;
    reg         l1_v, l2_v;
    reg  [31:0] l1_c, l2_c;
    integer p;
    // KV pair (t, k) = (c / K, c % K); x element (hh, k) = (c / KX, c % KX)
    wire [NW-1:0] kx = pv ? T : D;                  // x elements per head
    function automatic [AW-1:0] kvw(input [31:0] c);
        kvw = wb + (c / kk) * ts + (c % kk) * ks;
    endfunction
    function automatic [AW-1:0] xel(input [31:0] c);
        reg [31:0] hh, k;
        begin
            hh = c / kx; k = c % kx;
            xel = xb + (hh / IL) * xcs + k * xks + (hh % IL) * xjs;
        end
    endfunction
    function automatic [15:0] rne16(input [31:0] b);
        reg [32:0] s;
        begin
            s = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            rne16 = s[31:16];
        end
    endfunction

    // ---------------------------------------------------------------- engine
    reg          job_v, q_v, kv_v, p_v;
    wire         job_ready, q_ready, kv_ready, p_ready;
    reg  [D*16-1:0] q_w;
    reg  [NL-1:0]   kv_m;
    wire [NL*ROWW-1:0] kv_w;
    reg  [TD*16-1:0] p_w;
    wire         sc_v, pv_v;
    wire [15:0]  sc_row;
    wire [NL-1:0] sc_m;
    wire [NL*H*32-1:0] sc_y;
    wire [NL*H-1:0] sc_f;
    wire [7:0]   pv_c;
    wire [NT*H*32-1:0] pv_y;
    wire [NT*H-1:0] pv_f;
    reg          sc_cr, pv_cr;
    wire kv_stream_v = PACKED_KV ? (kv_v && packed_kv_v) : kv_v;
    assign packed_kv_ready = PACKED_KV && st == A_RUN && kv_v && kv_ready;
    ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(TROWS)) u_attn (
        .clk(clk), .rst_n(rst_n), .job_v(job_v), .job_t(T), .job_ready(job_ready),
        .q_v(q_v), .q_w(q_w), .q_ready(q_ready), .kv_v(kv_stream_v), .kv_m(kv_m), .kv_w(kv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
        .p_v(p_v), .p_w(p_w), .p_ready(p_ready), .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f),
        .pv_cr(pv_cr), .qk_iss(), .pv_iss());

    // job streams
    reg  [7:0]   jn;                                // job (H heads from jn*H)
    reg  [7:0]   qi;                                // q words sent
    reg  [NW-1:0] ki;                               // rows sent
    reg  [NW-1:0] pb, pw;                           // probability block, word
    reg  [NW-1:0] nsc;                              // score beats received
    reg  [7:0]   npv;                               // pv beats received
    wire [NW-1:0] nblk = (T + TD - 1) / TD;
    wire [NW-1:0] prem = T - pb * TD;
    wire [NW-1:0] words_blk = (prem >= TD) ? H : ((prem + R - 1) / R);
    wire [NW-1:0] sc_need = (T + NL - 1) / NL;
    wire [7:0]   hb = jn * H;
    wire         q_go = q_v && q_ready;
    wire         kv_go = kv_stream_v && kv_ready;
    wire         p_go = p_v && p_ready;

    wire [NL-1:0] enc_ok;
    genvar gr;
    generate if (!PACKED_KV) begin : g_local_kv
        reg [15:0] rowbuf [0:TROWS*D-1];
        for (gr = 0; gr < NL; gr = gr + 1) begin : g_enc
            reg [ROWW-1:0] wd;
            reg            ok;
            reg [16*D-1:0] row;
            integer x;
            always @(*) begin
                for (x = 0; x < D; x = x + 1) row[16*x +: 16] = rowbuf[(ki + gr) * D + x];
                {ok, wd} = encode_row(row);
            end
            assign kv_w[gr*ROWW +: ROWW] = wd;
            assign enc_ok[gr] = ok || !kv_m[gr];
        end
    // ================================================================ stored-format encoding
    // BF16 v / 2^e as an E4M3 code: {ok, code}
    function automatic [8:0] fp8_code(input [15:0] v, input integer e);
        integer ev, sh;
        reg [7:0] sig;
        begin
            fp8_code = 9'd0;
            if (v[14:0] == 15'd0) fp8_code = {1'b1, v[15], 7'd0};
            else if (v[14:7] != 8'd0 && v[14:7] != 8'hFF) begin
                ev = v[14:7] - 127 - e;
                sig = {1'b1, v[6:0]};
                if (ev >= -6 && ev <= 8) begin
                    if (v[3:0] == 4'd0 && !(ev == 8 && v[6:4] == 3'd7))
                        fp8_code = {1'b1, v[15], 4'(ev + 7), v[6:4]};
                end else if (ev < -6 && ev >= -9) begin
                    sh = -ev - 2;                              // j = sig * 2^(ev+2)
                    if ((sig & ((8'd1 << sh) - 8'd1)) == 8'd0)
                        fp8_code = {1'b1, v[15], 4'd0, 3'(sig >> sh)};
                end
            end
        end
    endfunction

    // an E4M3 code of sig * 2^X (sig < 256, > 0): {ok, code}
    function automatic [8:0] e4m3_of(input [7:0] sig, input integer X);
        integer pp, ex, sh;
        begin
            e4m3_of = 9'd0;
            pp = 0;
            for (sh = 0; sh < 8; sh = sh + 1) if (sig[sh]) pp = sh;
            ex = pp + X;                                        // value exponent
            if (ex >= -6 && ex <= 8) begin
                // significand bits below pp-3 must be zero
                if (pp < 3 || ((sig & ((8'd1 << (pp - 3)) - 8'd1)) == 8'd0)) begin
                    reg [7:0] m3;
                    m3 = (pp >= 3) ? (sig >> (pp - 3)) : (sig << (3 - pp));
                    if (!(ex == 8 && m3[2:0] == 3'd7)) e4m3_of = {1'b1, 1'b0, 4'(ex + 7), m3[2:0]};
                end
            end else if (ex < -6) begin
                // subnormal: j * 2^-9, j = sig * 2^(X + 9) < 8
                if (X + 9 >= 0) begin
                    if ((sig << (X + 9)) < 8) e4m3_of = {1'b1, 1'b0, 4'd0, 3'(sig << (X + 9))};
                end else begin
                    sh = -(X + 9);
                    if (sh < 8 && (sig & ((8'd1 << sh) - 8'd1)) == 8'd0 && (sig >> sh) < 8)
                        e4m3_of = {1'b1, 1'b0, 4'd0, 3'(sig >> sh)};
                end
            end
        end
    endfunction

    // 16 BF16 values as E2M1 codes x one E4M3 scale: {ok, scale[7:0], nibbles[63:0]}
    function automatic [72:0] fp4_group(input [255:0] vs);
        reg [14:0] M;
        integer i, ci, c2, d, eM, ei, q2, odd, k2, found;
        reg [7:0] sigM, sig_s, sigi;
        reg [8:0] sc;
        reg [63:0] nib;
        reg        all_ok;
        reg [23:0] X, Y;
        reg [2:0]  code;
        reg        hit;
        begin
            fp4_group = 73'd0;
            M = 15'd0;
            for (i = 0; i < 16; i = i + 1) if (vs[16*i +: 15] > M) M = vs[16*i +: 15];
            if (M == 15'd0) fp4_group = {1'b1, 8'h38, 64'd0};
            else if (M[14:7] != 8'd0 && M[14:7] != 8'hFF) begin
                sigM = {1'b1, M[6:0]};
                eM = M[14:7];
                found = 0;
                for (ci = 0; ci < 7; ci = ci + 1) if (!found) begin
                    case (ci)                                // q = 6, 4, 3, 2, 1.5, 1, 0.5 as q2 = 2q = odd * 2^k2
                        0: begin q2 = 12; odd = 3; k2 = 2; end
                        1: begin q2 = 8;  odd = 1; k2 = 3; end
                        2: begin q2 = 6;  odd = 3; k2 = 1; end
                        3: begin q2 = 4;  odd = 1; k2 = 2; end
                        4: begin q2 = 3;  odd = 3; k2 = 0; end
                        5: begin q2 = 2;  odd = 1; k2 = 1; end
                        default: begin q2 = 1; odd = 1; k2 = 0; end
                    endcase
                    if (sigM % odd == 0) begin
                        // s = M * 2 / q2 = (sigM / odd) * 2^(eM - 127 - 7 + 1 - k2)
                        sig_s = sigM / odd;
                        sc = e4m3_of(sig_s, eM - 127 - 7 + 1 - k2);
                        if (sc[8]) begin
                            all_ok = 1'b1;
                            nib = 64'd0;
                            for (i = 0; i < 16; i = i + 1) begin
                                if (vs[16*i +: 15] == 15'd0) nib[4*i +: 4] = 4'd0;
                                else if (vs[16*i + 7 +: 8] == 8'd0) all_ok = 1'b0;
                                else begin
                                    // |v| * q2 == M * c2 for some c2 in {1,2,3,4,6,8,12}
                                    sigi = {1'b1, vs[16*i +: 7]};
                                    ei = vs[16*i + 7 +: 8];
                                    d = eM - ei;
                                    X = sigi * q2;
                                    hit = 1'b0; code = 3'd0;
                                    if (d >= 0 && d < 13) begin
                                        for (c2 = 1; c2 <= 7; c2 = c2 + 1) begin
                                            Y = sigM * ((c2 == 5) ? 6 : (c2 == 6) ? 8 : (c2 == 7) ? 12 : c2);
                                            if (!hit && X == (Y << d)) begin hit = 1'b1; code = 3'(c2); end
                                        end
                                    end
                                    if (!hit) all_ok = 1'b0;
                                    nib[4*i +: 4] = {vs[16*i + 15], code};
                                end
                            end
                            if (all_ok) begin
                                found = 1;
                                fp4_group = {1'b1, sc[7:0], nib};
                            end
                        end
                    end
                end
            end
        end
    endfunction

    // one D-element row (BF16, element x at [16x]) as its stored group words: {ok, word}
    function automatic [ROWW:0] encode_row(input [16*D-1:0] row);
        integer g2, x2, e, E;
        reg [14:0] M;
        reg [GW-1:0] gw;
        reg ok8, okr;
        reg [8:0] c8;
        reg [72:0] f0, f1;
        reg [ROWW-1:0] wd;
        begin
            okr = 1'b1;
            wd = {ROWW{1'b0}};
            for (g2 = 0; g2 < NG; g2 = g2 + 1) begin
                M = 15'd0;
                for (x2 = 0; x2 < 32; x2 = x2 + 1)
                    if (row[16*(32*g2 + x2) +: 15] > M) M = row[16*(32*g2 + x2) +: 15];
                E = M[14:7];
                e = (M == 15'd0) ? 0 : ((M[6:0] <= 7'd96) ? (E - 127 - 8) : (E - 127 - 7));
                ok8 = (e + 127 >= 0) && (e + 127 <= 254);
                gw = {GW{1'b0}};
                for (x2 = 0; x2 < 32; x2 = x2 + 1) begin
                    c8 = fp8_code(row[16*(32*g2 + x2) +: 16], e);
                    if (!c8[8]) ok8 = 1'b0;
                    gw[8*x2 +: 8] = c8[7:0];
                end
                gw[263:256] = 8'(e + 127);
                gw[264] = 1'b0;
                if (!ok8) begin
                    f0 = fp4_group(row[16*(32*g2) +: 256]);
                    f1 = fp4_group(row[16*(32*g2 + 16) +: 256]);
                    gw = {GW{1'b0}};
                    gw[63:0] = f0[63:0];
                    gw[127:64] = f1[63:0];
                    gw[135:128] = f0[71:64];
                    gw[143:136] = f1[71:64];
                    gw[264] = 1'b1;
                    if (!(f0[72] && f1[72])) okr = 1'b0;
                end
                wd[g2*GW +: GW] = gw;
            end
            encode_row = {okr, wd};
        end
    endfunction

    end else begin : g_packed_kv
        assign kv_w = packed_kv_w;
        assign enc_ok = {NL{1'b1}};
    end endgenerate

    // ---------------------------------------------------------------- sequencer
    reg  [31:0] wc, wend;                           // result words
    reg         efault;
    integer b, l, hh2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= A_IDLE; kv_re <= 1'b0; x_re <= 0; l1_v <= 1'b0; l2_v <= 1'b0; o_we <= 0;
            job_v <= 1'b0; q_v <= 1'b0; kv_v <= 1'b0; p_v <= 1'b0; sc_cr <= 1'b0; pv_cr <= 1'b0;
            efault <= 1'b0;
        end else begin
            kv_re <= 1'b0; x_re <= 0; o_we <= 0;
            l1_v <= 1'b0; l2_v <= l1_v; l2_c <= l1_c;
            sc_cr <= sc_v; pv_cr <= pv_v;
            case (st)
                A_IDLE: if (go) begin
                    st <= PACKED_KV ? A_LDX : A_LDKV;
                    lc <= 0; efault <= 1'b0;
                    lend <= PACKED_KV ? c_nhd * ((i_ks != 1) ? i_k : D) : c_ntile * i_k;
                end
                A_LDKV: begin
                    kv_re <= 1'b1;
                    l1_v <= 1'b1; l1_c <= lc;
                    lc <= lc + G;
                    if (lc + G >= lend) begin st <= A_LDX; lc <= 0; lend <= nhd * kx; end
                end
                A_LDX: begin
                    if (lc < lend) begin
                        for (p = 0; p < G; p = p + 1) x_re[p] <= (lc + p < lend);
                        l1_v <= 1'b1; l1_c <= lc;
                        lc <= lc + G;
                    end else if (!l1_v && !l2_v) begin
                        st <= A_JOB; jn <= 0;
                    end
                end
                A_JOB: begin
                    job_v <= 1'b1;
                    if (job_v && job_ready) begin
                        job_v <= 1'b0; st <= A_RUN;
                        qi <= 0; ki <= 0; pb <= 0; pw <= 0; nsc <= 0; npv <= 0;
                        q_v <= 1'b1; kv_v <= 1'b1; p_v <= 1'b1;
                    end
                end
                A_RUN: begin
                    if (q_go) begin qi <= qi + 1'b1; if (qi + 1 == H) q_v <= 1'b0; end
                    if (kv_go) begin ki <= ki + NL; if (ki + NL >= T) kv_v <= 1'b0; end
                    if (p_go) begin
                        if (pw + 1 == words_blk) begin
                            pw <= 0; pb <= pb + 1'b1;
                            if (pb + 1 == nblk) p_v <= 1'b0;
                        end else pw <= pw + 1'b1;
                    end
                    if ((kv_go && (enc_ok != {NL{1'b1}} ||
                                   (PACKED_KV && packed_kv_m != kv_m))) ||
                        (PACKED_KV && packed_kv_fault)) efault <= 1'b1;
                    if (sc_v) nsc <= nsc + 1'b1;
                    if (pv_v) npv <= npv + 1'b1;
                    if ((nsc + sc_v == sc_need) && (npv + pv_v == DPT) && !q_v && !kv_v && !p_v) begin
                        if (jn + 1 == nhd / H) begin
                            st <= A_WR; wc <= 0; wend <= nhd * ((nout + W - 1) / W);
                        end else begin
                            jn <= jn + 1'b1; st <= A_JOB;
                        end
                    end
                end
                A_WR: begin
                    for (p = 0; p < G; p = p + 1) o_we[p] <= (wc + p < wend) && oen_r;
                    wc <= wc + G;
                    if (wc + G >= wend) st <= A_IDLE;
                end
                default: st <= A_IDLE;
            endcase
        end
    end
    reg oen_r;
    always @(posedge clk) begin
        if (st == A_IDLE && go) begin
            pv <= (i_ks != 1);
            nout <= i_nout; kk <= i_k; ntile <= c_ntile; wb <= i_wbase; ts <= i_ts; ks <= i_ks;
            xb <= i_xbase; xks <= i_xks; xjs <= i_xjs; xcs <= i_xcs; ogs <= i_ogs; ob <= i_obase;
            ots <= i_ots; ojs <= i_ojs; nhd <= c_nhd; oen_r <= i_oen;
            T <= (i_ks != 1) ? i_k : i_nout;
            //: shapes the adapter serves: js = 0, mmode 1, the D-long axis D, one position, H | heads
            bad <= (i_js != 0) || !i_mmode || !i_round || (i_m > 3'd1) ||
                   (((i_ks != 1) ? i_nout : i_k) != D) || (((i_ks != 1) ? i_k : i_nout) > TROWS) ||
                   ((c_nhd % H) != 0) || (c_nhd > NHMAX);
        end
        // load addresses
        if (st == A_LDKV)
            for (p = 0; p < G; p = p + 1) kv_addr[p*AW +: AW] <= kvw(lc + p);
        if (st == A_LDX)
            for (p = 0; p < G; p = p + 1) x_addr[p*AW +: AW] <= xel(lc + p);
    end
    // load captures (the data is on kv_q / x_q while l2_v)
    reg l2_kv;                                      // the load in l2 is a KV load
    reg l1_kv;
    always @(posedge clk) begin
        l1_kv <= (st == A_LDKV);
        l2_kv <= l1_kv;
    end
    generate if (!PACKED_KV) begin : g_local_capture
        integer lq, ll;
        always @(posedge clk) if (l2_v && l2_kv) begin
            for (lq = 0; lq < G; lq = lq + 1)
                if (l2_c + lq < lend_kv)
                    for (ll = 0; ll < W; ll = ll + 1) begin : cap
                        reg [31:0] c, t, k, o;
                        c = l2_c + lq; t = c / kk; k = c % kk; o = t * W + ll;
                        if (!pv && o < T) g_local_kv.rowbuf[o * D + k] <= kv_q[(lq*W + ll)*32 + 16 +: 16];
                        if (pv && o < D) g_local_kv.rowbuf[k * D + o] <= kv_q[(lq*W + ll)*32 + 16 +: 16];
                    end
        end
    end endgenerate
    integer lq;
    always @(posedge clk) begin
        if (l2_v && !l2_kv)
            for (lq = 0; lq < G; lq = lq + 1)
                if (l2_c + lq < lend)
                    xbuf[((l2_c + lq) / kx) * TROWS + (l2_c + lq) % kx] <= rne16(x_q[lq*32 +: 32]);
    end
    reg [31:0] lend_kv;
    always @(posedge clk) if (st == A_IDLE && go) lend_kv <= c_ntile * i_k;

    // engine stream words
    integer qd, pj, ph;
    always @(*) begin
        for (qd = 0; qd < D; qd = qd + 1) q_w[qd*16 +: 16] = pv ? 16'd0 : xbuf[(hb + qi) * TROWS + qd];
        for (pj = 0; pj < R; pj = pj + 1)
            for (ph = 0; ph < H; ph = ph + 1)
                p_w[(pj*H + ph)*16 +: 16] = (pv && (pb * TD + pw * R + pj < T)) ?
                                            xbuf[(hb + ph) * TROWS + pb * TD + pw * R + pj] : 16'd0;
        for (pj = 0; pj < NL; pj = pj + 1) kv_m[pj] = (ki + pj < T);
    end

    // results
    integer sr, rh, tk;
    always @(posedge clk) begin
        if (st == A_RUN && sc_v && !pv)
            for (sr = 0; sr < NL; sr = sr + 1)
                if (sc_m[sr])
                    for (rh = 0; rh < H; rh = rh + 1)
                        obuf[(hb + rh) * TROWS + sc_row + sr] <= sc_y[(sr*H + rh)*32 +: 32];
        if (st == A_RUN && pv_v && pv)
            for (tk = 0; tk < NT; tk = tk + 1)
                for (rh = 0; rh < H; rh = rh + 1)
                    obuf[(hb + rh) * TROWS + tk * DPT + pv_c] <= pv_y[(tk*H + rh)*32 +: 32];
    end
    // activation counters (bench): ops run, and result values taken from the engine -- H scores per valid
    // q.k row lane (q.k ops), NT x H pv values per final p.v beat (p.v ops)
    reg [31:0] dbg_ops, dbg_elems;
    integer sci;
    reg [7:0] scn;
    always @(*) begin
        scn = 0;
        for (sci = 0; sci < NL; sci = sci + 1) scn = scn + sc_m[sci];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin dbg_ops <= 0; dbg_elems <= 0; end
        else begin
            if (st == A_IDLE && go) dbg_ops <= dbg_ops + 1;
            if (st == A_RUN && sc_v && !pv) dbg_elems <= dbg_elems + scn * H;
            else if (st == A_RUN && pv_v && pv) dbg_elems <= dbg_elems + NT * H;
        end
    end
    reg rfault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rfault <= 1'b0;
        else if (st == A_IDLE && go) rfault <= 1'b0;
        else if (st == A_RUN && ((sc_v && !pv && ((sc_f & {H{1'b1}} & mask_rows(sc_m)) != 0)) ||
                                 (pv_v && pv && (pv_f != 0)))) rfault <= 1'b1;
    end
    function automatic [NL*H-1:0] mask_rows(input [NL-1:0] m);
        integer a;
        begin
            for (a = 0; a < NL*H; a = a + 1) mask_rows[a] = m[a / H];
        end
    endfunction

    // result writes: word c = (head hh, tile t) -> ob + t*ots + (hh/IL)*ogs + (hh%IL)*ojs
    wire [NW-1:0] ntw = (nout + W - 1) / W;
    integer wq, wl;
    always @(posedge clk) begin
        for (wq = 0; wq < G; wq = wq + 1) begin : wr
            reg [31:0] c, hh, t;
            c = wc + wq; hh = c / ntw; t = c % ntw;
            o_addr[wq*AW +: AW] <= ob + t * ots + (hh / IL) * ogs + (hh % IL) * ojs;
            for (wl = 0; wl < W; wl = wl + 1) begin
                o_mask[wq*W + wl] <= (t * W + wl < nout);
                o_data[(wq*W + wl)*32 +: 32] <= obuf[hh * TROWS + t * W + wl];
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; end
        else begin
            idle <= (st == A_IDLE) && !go && !(|o_we);
            fault <= (st != A_IDLE) && (bad || efault || rfault);
        end
    end

endmodule
