`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bterm5_w10: the margin-first lane of the DS q-element (owner rule 2026-10-06: close with >= +60 ps at SS,
// register-to-register boundaries).  Same arithmetic as ot_v41_bterm4_w10 with P1S = 1, P2S = 1, NS = 1, WD = 1
// (every output bit-identical: the same decode, the same exact 42-bit carry-save total under another grouping --
// carry-save addition is exact modulo 2^42 under any grouping -- the same normalise, roundings and pack); the
// stages are cut finer, every class within ~50 ps in the Z18-Z22 routes gets its own register:
//   S0  m_   input capture at the pins (no logic between the element's word mux and a flop)       [new]
//   S1  p0_  decode: FP4 e2m1 / FP8 fields per lane (sign, significands, exponent fields), NaN per lane,
//            xe + we                                                                                  [was P0 + P1a]
//   S2  pa_  4x4 significand product (unsigned), shift amount, NaN OR                                [was P1a / P1b]
//   S3  p1_  the product's sign and the low two shift bits (12-bit signed partial term)              [was P1b]
//   S4  p2h_ term shift by {sh[4:2], 00} + CSA 32 -> 15                                               [was P2]
//   S5  p2_  CSA 15 -> 5                                                                              [new]
//   S6  p3_  CSA 5 -> 2                                                                               [was P3]
//   S7  p4a_ the 42-bit sum;  S8 p4_ sign-magnitude
//   S9  p5a_ normalise 32 / 16;  S10 p5b_ 8 / 4;  S11 p5_ 2 / 1 and the leading-bit exponent       [was 2 stages]
//   S12 p6a_ round-to-24 increment bit;  S13 p6_ the increment and the exponent carry               [was 1]
//   S14 p7a_ subnormal shift amount;  S15 p7_ subnormal shift, sticky, normal pack                    [was 1]
//   S16 p8_  subnormal round and pack
// LATENCY 17 (ot_v41_bterm4_w10 with P1S = 1: 12): +5 cycles a lane.  The tag rides the same 17 stages.
// ---------------------------------------------------------------------------
module ot_v41_bterm5_w10 #(
    parameter integer TW = 8,
    parameter integer NP = 0,         // 1: native partition (S81-QXPQ3: no driver > 32 loads), default 0 = unchanged
    parameter integer OK = 1,         // NP: kept copies of otag's slot field (top OKW bits) on otag_k (NP-LANE)
    parameter integer OKW = 1,        // NP: width of the copied slot field = otag[TW-1 -: OKW]
    parameter integer FPC = 4,        // kept copies of the FP4 select (32 = one per lane: q-element QM >= 5)
    parameter integer P0B = 0         // 3 (owner decision 2026-10-06 23:00, Z29c post-CTS at 730: q0_pm -158.8, p0_ws -> 260 ps
                                      // of wire -> product, the placer put the S1b product registers at the CSA end):
                                      // the decode -> product wire through an explicit register at its midpoint: S1b
                                      // the decoded fields only (a register-only wire stage), S1c the product and shift
                                      // sum, S2 a register-only wire stage; and the 32-lane terms registered after their
                                      // shift (S4a) before the 32 -> 15 CSA (p2h_c -48.3): +2 lane cycles over P0B = 2.
                                      // 2 (Z29b post-CTS at 730: the S1b copy sat beside the decode, the wire stayed in
                                      // front of the product, pa_pm -156): the product and shift sum formed in S1b next
                                      // to the decode, S2 a register-only wire stage.  SAFE (owner fail-fast 2026-10-06, Z26b post-CTS at 770: p0_ws -> 222 ps of wire ->
                                      // 4x4 product -> pa_pm -105.8): the decoded fields registered once more (S1b, +1
                                      // lane cycle) so the decode-to-product wire has its own stage; the 32-lane NaN OR
                                      // split 32 -> 8 there (8 -> 1 in S2)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire              fp4,
    input  wire [255:0]      xq,
    input  wire signed [9:0] xe,
    input  wire [255:0]      wq,
    input  wire signed [9:0] we,
    input  wire [TW-1:0]     tag,
    output wire              ov,
    output wire [31:0]       y,
    output wire              f,
    output wire [TW-1:0]     otag,
    // NP-LANE (S81-QXPQ3): OK kept copies of the LAST tag stage's slot field, cycle-identical to otag[TW-1 -: OKW]:
    // copy j = otag_k[j*OKW +: OKW] (j = 0 .. OK-1), each its own ot_v41_kreg (never merged), so each consumer slice
    // (the CHAIN sub-lane: chain4's accumulator read mux / slot compares) drives its <= 32 loads from its own copy.
    // The copies load their D net in groups of <= 32 (one kept stage-(LATENCY-1) copy per group).  NP = 0: all 0.
    output wire [OK*OKW-1:0] otag_k
);
    localparam integer W = 42;
    localparam integer LATENCY = 17 + (P0B != 0 ? 1 : 0) + (P0B >= 3 ? 2 : 0);
    function automatic [7:0] e2m1(input [3:0] c);
        if (c[2:1] == 2'd0) e2m1 = {c[3], c[0] ? 4'd6 : 4'd0, 3'd0};
        else                e2m1 = {c[3], {2'b00, c[2:1]} + 4'd6, c[0], 2'b00};
    endfunction
    integer i;
    // NP: one FP4 select copy per lane (u_l1 instantiates FPC = 4: 8 lanes = 80 loads a copy); NP = 0: FPC
    localparam integer FPN = (NP != 0) ? 32 : FPC;
    // NP slice of output bit k of an n-bit field cut into c contiguous slices (slice 0 = the top bits)
    function automatic integer npl_sl(input integer k, input integer n, input integer c);
        npl_sl = ((n - 1 - k) * c) / n;
    endfunction

    // valid chain (async reset), one bit a stage
    reg [LATENCY-1:0] vs;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vs <= '0;
        else vs <= {vs[LATENCY-2:0], v};

    // -- S0: input capture ------------------------------------------------------------------------------
    // the FP4 select in four kept copies (ot_v41_kreg: never merged with the tag delay line's copy of the same bit,
    // Z24b post-CTS: a merged fp4 flop in the tag line drove all 32 lanes' decode, -190 ps), one per 8 lanes
    wire [FPN-1:0]   m_fp4;
    for (genvar g = 0; g < FPN; g = g + 1) begin : g_f4
        ot_v41_kreg #(.W(1)) u_f (.clk(clk), .arst_n(1'b1), .d(fp4), .q(m_fp4[g]));
    end
    reg [255:0]      m_xq, m_wq;
    reg signed [9:0] m_xe, m_we;
    always @(posedge clk) begin
        m_xq <= xq; m_wq <= wq; m_xe <= xe; m_we <= we;
    end

    // -- S1: decode -----------------------------------------------------------------------------------
    reg               p0_sg [0:31];
    reg [3:0]         p0_xs [0:31], p0_ws [0:31], p0_xf [0:31], p0_wf [0:31];
    reg [31:0]        p0_nan;           // per lane (Z24b: the 8-lane NaN OR in the decode stage spanned the lane, -529 ps)
    reg signed [10:0] p0_es;
    reg [7:0]         xc, wc;
    always @(posedge clk) begin
        p0_es <= m_xe + m_we;
        for (i = 0; i < 32; i = i + 1) begin
            xc = m_xq[8*i +: 8];
            wc = m_fp4[(i * FPN) / 32] ? e2m1(m_wq[8*i +: 4]) : m_wq[8*i +: 8];
            p0_nan[i] <= (xc[6:0] == 7'h7F) | (wc[6:0] == 7'h7F);
            p0_sg[i] <= xc[7] ^ wc[7];
            p0_xs[i] <= {(xc[6:3] != 4'd0), xc[2:0]};
            p0_ws[i] <= {(wc[6:3] != 4'd0), wc[2:0]};
            p0_xf[i] <= (xc[6:3] == 4'd0) ? 4'd1 : xc[6:3];
            p0_wf[i] <= (wc[6:3] == 4'd0) ? 4'd1 : wc[6:3];
        end
    end

    // -- S1b (P0B): the decoded fields once more ------------------------------------------------------------
    reg               q0_sg [0:31];
    reg [3:0]         q0_xs [0:31], q0_ws [0:31], q0_xf [0:31], q0_wf [0:31];
    reg [31:0]        q0_nan;
    reg signed [10:0] q0_es;
    reg [7:0]         q0_pm [0:31];     // P0B >= 2: the 4x4 product formed in S1b (next to the decode), S2 a wire stage
    reg [4:0]         q0_sh [0:31];
    if (P0B != 0) begin : g_p0b
        always @(posedge clk) begin
            q0_es <= p0_es;
            for (i = 0; i < 32; i = i + 1) begin
                q0_sg[i] <= p0_sg[i]; q0_xs[i] <= p0_xs[i]; q0_ws[i] <= p0_ws[i]; q0_xf[i] <= p0_xf[i]; q0_wf[i] <= p0_wf[i];
                if (P0B == 2) begin
                    q0_pm[i] <= p0_xs[i] * p0_ws[i];
                    q0_sh[i] <= {1'b0, p0_xf[i]} + {1'b0, p0_wf[i]} - 5'd2;
                end
            end
            for (i = 0; i < 8; i = i + 1) q0_nan[i] <= |p0_nan[4*i +: 4];
            q0_nan[31:8] <= '0;
        end
    end else begin : g_np0b
        always @(*) begin
            q0_es = p0_es; q0_nan = p0_nan;
            for (i = 0; i < 32; i = i + 1) begin
                q0_sg[i] = p0_sg[i]; q0_xs[i] = p0_xs[i]; q0_ws[i] = p0_ws[i]; q0_xf[i] = p0_xf[i]; q0_wf[i] = p0_wf[i];
            end
        end
    end

    // -- S1c (P0B >= 3): product and shift sum from the S1b registers (S1b and S2 are register-only wire stages) ----
    reg               q1_sg [0:31];
    reg [7:0]         q1_pm [0:31];
    reg [4:0]         q1_sh [0:31];
    reg [7:0]         q1_nan;
    reg signed [10:0] q1_es;
    if (P0B >= 3) begin : g_p0c
        always @(posedge clk) begin
            q1_es <= q0_es; q1_nan <= q0_nan[7:0];
            for (i = 0; i < 32; i = i + 1) begin
                q1_sg[i] <= q0_sg[i];
                q1_pm[i] <= q0_xs[i] * q0_ws[i];
                q1_sh[i] <= {1'b0, q0_xf[i]} + {1'b0, q0_wf[i]} - 5'd2;
            end
        end
    end

    // -- S2: product, shift amount --------------------------------------------------------------------
    reg               pa_sg [0:31];
    reg [7:0]         pa_pm [0:31];
    reg [4:0]         pa_sh [0:31];
    reg               pa_nan;
    reg signed [10:0] pa_es;
    always @(posedge clk) begin
        pa_es <= (P0B >= 3) ? q1_es : q0_es;
`ifdef BT5_MUTANT_NS
        pa_nan <= (P0B >= 3 ? |q1_nan[5:0] : P0B != 0 ? |q0_nan[5:0] : |q0_nan[23:0]);         // negative control: 8 lanes dropped
`else
        pa_nan <= (P0B >= 3) ? |q1_nan : |q0_nan;
`endif
        for (i = 0; i < 32; i = i + 1) begin
            pa_sg[i] <= (P0B >= 3) ? q1_sg[i] : q0_sg[i];
            pa_pm[i] <= (P0B >= 3) ? q1_pm[i] : (P0B >= 2) ? q0_pm[i] : q0_xs[i] * q0_ws[i];
            pa_sh[i] <= (P0B >= 3) ? q1_sh[i] : (P0B >= 2) ? q0_sh[i] : {1'b0, q0_xf[i]} + {1'b0, q0_wf[i]} - 5'd2;
        end
    end

    // -- S3: signed partial term, low shift ------------------------------------------------------------
    reg signed [11:0] p1_q [0:31];
    reg [2:0]         p1_sq [0:31];
    reg               p1_nan;
    reg signed [10:0] p1_es;
    always @(posedge clk) begin
        p1_nan <= pa_nan; p1_es <= pa_es;
        for (i = 0; i < 32; i = i + 1) begin
`ifdef BT5_MUTANT_SH
            p1_q[i] <= $signed(pa_sg[i] ? -$signed({1'b0, pa_pm[i]}) : $signed({1'b0, pa_pm[i]})) <<< pa_sh[i][1];  // negative control
`else
            p1_q[i] <= $signed(pa_sg[i] ? -$signed({1'b0, pa_pm[i]}) : $signed({1'b0, pa_pm[i]})) <<< pa_sh[i][1:0];
`endif
            p1_sq[i] <= pa_sh[i][4:2];
        end
    end

    // -- S4: terms (units of 2^-18) and CSA 32 -> 15 ----------------------------------------------------
    reg [32*W-1:0] terms;
    if (NP != 0) begin : g_np_s4
        // NP: the S3 shift-amount register p1_sq in two kept copies per lane (one p1_sq bit drove 36 shifter cells):
        // copy a shifts the term's low 21 bits, copy b the high 21 bits (each half's shifter only from its own copy)
        wire [32*W-1:0] tnp;
        for (genvar l = 0; l < 32; l = l + 1) begin : g_l
            wire [2:0] qa, qb;
            ot_v41_kreg #(.W(3)) u_a (.clk(clk), .arst_n(1'b1), .d(pa_sh[l][4:2]), .q(qa));
            ot_v41_kreg #(.W(3)) u_b (.clk(clk), .arst_n(1'b1), .d(pa_sh[l][4:2]), .q(qb));
            wire [W-1:0] tx = {{(W-12){p1_q[l][11]}}, p1_q[l]};
            wire [W-1:0] ta = tx << {qa, 2'b00};
`ifdef OT_NP_LANE_MUT
            wire [W-1:0] tb = tx << {qb, 2'b01};          // negative control: the high half shifted one place too far
`else
            wire [W-1:0] tb = tx << {qb, 2'b00};
`endif
            assign tnp[W*l +: W] = {tb[W-1:21], ta[20:0]};
        end
        always @(*) terms = tnp;
    end else begin : g_o_s4
        always @(*)
            for (i = 0; i < 32; i = i + 1)
                terms[W*i +: W] = {{(W-12){p1_q[i][11]}}, p1_q[i]} << {p1_sq[i], 2'b00};
    end
    // S4a (P0B >= 3): the shifted terms registered before the 32 -> 15 CSA (owner rule 3: a reduction over > 4 inputs
    // gets a register level; Z29c post-CTS at 730: p2h_c -48.3)
    reg [32*W-1:0]    t4_t;
    reg               t4_nan;
    reg signed [10:0] t4_es;
    if (P0B >= 3) begin : g_t4
        always @(posedge clk) begin t4_t <= terms; t4_nan <= p1_nan; t4_es <= p1_es; end
    end else begin : g_nt4
        always @(*) begin t4_t = terms; t4_nan = p1_nan; t4_es = p1_es; end
    end
    wire [15*W-1:0] c15;
    ot_v41_csa #(.N(32), .M(15), .W(W)) u_csa1 (.d(t4_t), .q(c15));
    reg [15*W-1:0]    p2h_c;
    reg               p2h_nan;
    reg signed [10:0] p2h_es;
    always @(posedge clk) begin p2h_c <= c15; p2h_nan <= t4_nan; p2h_es <= t4_es; end

    // -- S5: CSA 15 -> 5 --------------------------------------------------------------------------------
    wire [5*W-1:0] c5;
    ot_v41_csa #(.N(15), .M(5), .W(W)) u_csa2 (.d(p2h_c), .q(c5));
    reg [5*W-1:0]     p2_c;
    reg               p2_nan;
    reg signed [10:0] p2_es;
    always @(posedge clk) begin p2_c <= c5; p2_nan <= p2h_nan; p2_es <= p2h_es; end

    // -- S6: CSA 5 -> 2 ---------------------------------------------------------------------------------
    wire [2*W-1:0] c2;
    ot_v41_csa #(.N(5), .M(2), .W(W)) u_csa3 (.d(p2_c), .q(c2));
    reg               p3_nan;
    reg signed [10:0] p3_es;
    reg [W-1:0]       p3_a, p3_b;
    always @(posedge clk) begin
        p3_nan <= p2_nan; p3_es <= p2_es;
        p3_a <= c2[W-1:0]; p3_b <= c2[2*W-1:W];
    end

    // -- S7: the carry-save pair's sum --------------------------------------------------------------------
    wire [W-1:0] s4a;
    wire         c4a;
    ot_v41_ksadd #(.W(W)) u_s4a (.a(p3_a), .b(p3_b), .cin(1'b0), .s(s4a), .cout(c4a));
    reg               p4a_nan;
    reg signed [10:0] p4a_es;
    reg [W-1:0]       p4a_s;
    always @(posedge clk) begin p4a_nan <= p3_nan; p4a_es <= p3_es; p4a_s <= s4a; end

    // -- S8: sign-magnitude ----------------------------------------------------------------------------------
    wire [W-1:0] ng;
    wire         cng;
    ot_v41_inc #(.W(W)) u_ng (.a(~p4a_s), .inc(1'b1), .y(ng), .co(cng));
    reg               p4_nan, p4_s;
    reg signed [11:0] p4_eb;
    reg [W-2:0]       p4_m;
    if (NP == 0) begin : g_o_s8
        always @(posedge clk) begin
            p4_nan <= p4a_nan;
            p4_eb <= p4a_es + 12'sd149;
            p4_s <= p4a_s[W-1];
            p4_m <= p4a_s[W-1] ? ng[W-2:0] : p4a_s[W-2:0];
        end
    end

    // -- S9: normalise 32 / 16 ---------------------------------------------------------------------------------
    reg [40:0] nma;
    reg [5:0]  lza;
    if (NP == 0) begin : g_o_s9c
        always @(*) begin
            nma = p4_m; lza = 6'd0;
            if (nma[40:9]  == 32'd0) begin nma = nma << 32; lza = lza + 6'd32; end
            if (nma[40:25] == 16'd0) begin nma = nma << 16; lza = lza + 6'd16; end
        end
    end
    reg               p5a_nan, p5a_s, p5a_z;
    reg signed [11:0] p5a_eb;
    reg [40:0]        p5a_nm;
    reg [5:0]         p5a_lz;
    if (NP == 0) begin : g_o_s9
        always @(posedge clk) begin
            p5a_nan <= p4_nan; p5a_s <= p4_s; p5a_z <= (p4_m == 41'd0);
            p5a_eb <= p4_eb; p5a_nm <= nma; p5a_lz <= lza;
        end
    end

    // -- S10: normalise 8 / 4 -----------------------------------------------------------------------------------
    reg [40:0] nmb;
    reg [5:0]  lzb;
    if (NP == 0) begin : g_o_s10c
        always @(*) begin
            nmb = p5a_nm; lzb = p5a_lz;
            if (nmb[40:33] == 8'd0) begin nmb = nmb << 8; lzb = lzb + 6'd8; end
            if (nmb[40:37] == 4'd0) begin nmb = nmb << 4; lzb = lzb + 6'd4; end
        end
    end
    reg               p5b_nan, p5b_s, p5b_z;
    reg signed [11:0] p5b_eb;
    reg [40:0]        p5b_nm;
    reg [5:0]         p5b_lz;
    if (NP == 0) begin : g_o_s10
        always @(posedge clk) begin
            p5b_nan <= p5a_nan; p5b_s <= p5a_s; p5b_z <= p5a_z;
            p5b_eb <= p5a_eb; p5b_nm <= nmb; p5b_lz <= lzb;
        end
    end

    // -- S11: normalise 2 / 1, leading-bit exponent ----------------------------------------------------------------
    reg [40:0] nm;
    reg [5:0]  lz;
    if (NP == 0) begin : g_o_s11c
        always @(*) begin
            nm = p5b_nm; lz = p5b_lz;
            if (nm[40:39] == 2'd0) begin nm = nm << 2; lz = lz + 6'd2; end
            if (nm[40] == 1'b0)    begin nm = nm << 1; lz = lz + 6'd1; end
        end
    end
    reg               p5_nan, p5_s, p5_z;
    reg signed [11:0] p5_ebl;
    reg [40:0]        p5_nm;
    always @(posedge clk) begin
        p5_nan <= p5b_nan; p5_s <= p5b_s; p5_z <= p5b_z;
        p5_ebl <= p5b_eb - $signed({6'd0, lz}); p5_nm <= nm;
    end

    // -- NP (S81-QXPQ3, no driver > 32 loads): S8 - S11 with kept copies --------------------------------------------
    // The magnitude register p4_m and the normalise registers p5a_nm / p5b_nm are each kept in C copies
    // (ot_v41_kreg); the normalise output is cut into C contiguous bit slices (slice 0 = the top bits) and slice s is
    // formed ONLY from copy s (its own zero detects and shift selects: one select drove 33 - 65 cells).  The S7 sign
    // p4a_s[41] (42 loads: the 41-bit sign-magnitude select) is kept in two copies, one per half of the select.
    // The leading-zero counts come from slice 0.  Same values, same cycles as NP = 0.
    localparam integer C8 = 2, C9 = 4, C10 = 2;   // q4_d4: C9 3 -> 4 (S10 slice-0 shift select 33 - 34 loads)
    function automatic [46:0] npl_n32(input [40:0] m);
        reg [40:0] x; reg [5:0] z;
        begin
            x = m; z = 6'd0;
            if (x[40:9]  == 32'd0) begin x = x << 32; z = z + 6'd32; end
            if (x[40:25] == 16'd0) begin x = x << 16; z = z + 6'd16; end
            npl_n32 = {x, z};
        end
    endfunction
    function automatic [46:0] npl_n8(input [40:0] m, input [5:0] zi);
        reg [40:0] x; reg [5:0] z;
        begin
            x = m; z = zi;
            if (x[40:33] == 8'd0) begin x = x << 8; z = z + 6'd8; end
            if (x[40:37] == 4'd0) begin x = x << 4; z = z + 6'd4; end
            npl_n8 = {x, z};
        end
    endfunction
    function automatic [46:0] npl_n2(input [40:0] m, input [5:0] zi);
        reg [40:0] x; reg [5:0] z;
        begin
            x = m; z = zi;
            if (x[40:39] == 2'd0) begin x = x << 2; z = z + 6'd2; end
            if (x[40] == 1'b0)    begin x = x << 1; z = z + 6'd1; end
            npl_n2 = {x, z};
        end
    endfunction
    if (NP != 0) begin : g_np_nrm
        // S7 sign copies (same D as p4a_s[41])
        wire [1:0] sg;
        ot_v41_kreg #(.W(1)) u_sg0 (.clk(clk), .arst_n(1'b1), .d(s4a[W-1]), .q(sg[0]));
        ot_v41_kreg #(.W(1)) u_sg1 (.clk(clk), .arst_n(1'b1), .d(s4a[W-1]), .q(sg[1]));
        // S8: magnitude in C8 copies
        wire [W-2:0] md;
        for (genvar k = 0; k < W - 1; k = k + 1) begin : g_md
            assign md[k] = sg[k >= (W - 1) / 2 ? 1 : 0] ? ng[k] : p4a_s[k];
        end
        wire [41*C8-1:0] m4;
        for (genvar c = 0; c < C8; c = c + 1) begin : g_m4
            ot_v41_kreg #(.W(41)) u_m (.clk(clk), .arst_n(1'b1), .d(md), .q(m4[41*c +: 41]));
        end
        always @(posedge clk) begin
            p4_nan <= p4a_nan;
            p4_eb <= p4a_es + 12'sd149;
            p4_s <= p4a_s[W-1];
        end
        always @(*) p4_m = m4[40:0];     // copy 0 (read only by the S9 zero flag below)
        // S9: slices of the 32 / 16 normalise, slice s from copy s
        wire [47*C8-1:0] r9;
        for (genvar c = 0; c < C8; c = c + 1) begin : g_r9
            assign r9[47*c +: 47] = npl_n32(m4[41*c +: 41]);
        end
        integer k9;
        always @(*) begin
            for (k9 = 0; k9 < 41; k9 = k9 + 1) nma[k9] = r9[47 * npl_sl(k9, 41, C8) + 6 + k9];
            lza = r9[5:0];
        end
        wire [41*C9-1:0] a5;
        for (genvar c = 0; c < C9; c = c + 1) begin : g_a5
            ot_v41_kreg #(.W(41)) u_m (.clk(clk), .arst_n(1'b1), .d(nma), .q(a5[41*c +: 41]));
        end
        always @(posedge clk) begin
            p5a_nan <= p4_nan; p5a_s <= p4_s; p5a_z <= (m4[41*(C8-1) +: 41] == 41'd0);
            p5a_eb <= p4_eb; p5a_lz <= lza;
        end
        always @(*) p5a_nm = a5[40:0];
        // S10: slices of the 8 / 4 normalise
        wire [47*C9-1:0] r10;
        for (genvar c = 0; c < C9; c = c + 1) begin : g_r10
            assign r10[47*c +: 47] = npl_n8(a5[41*c +: 41], p5a_lz);
        end
        integer k10;
        always @(*) begin
            for (k10 = 0; k10 < 41; k10 = k10 + 1) nmb[k10] = r10[47 * npl_sl(k10, 41, C9) + 6 + k10];
            lzb = r10[5:0];
        end
        wire [41*C10-1:0] b5;
        for (genvar c = 0; c < C10; c = c + 1) begin : g_b5
            ot_v41_kreg #(.W(41)) u_m (.clk(clk), .arst_n(1'b1), .d(nmb), .q(b5[41*c +: 41]));
        end
        always @(posedge clk) begin
            p5b_nan <= p5a_nan; p5b_s <= p5a_s; p5b_z <= p5a_z;
            p5b_eb <= p5a_eb; p5b_lz <= lzb;
        end
        always @(*) p5b_nm = b5[40:0];
        // S11: slices of the 2 / 1 normalise
        wire [47*C10-1:0] r11;
        for (genvar c = 0; c < C10; c = c + 1) begin : g_r11
            assign r11[47*c +: 47] = npl_n2(b5[41*c +: 41], p5b_lz);
        end
        integer k11;
        always @(*) begin
            for (k11 = 0; k11 < 41; k11 = k11 + 1) nm[k11] = r11[47 * npl_sl(k11, 41, C10) + 6 + k11];
            lz = r11[5:0];
        end
    end

    // -- S12: the round-to-24 increment bit ------------------------------------------------------------------------
    reg               p6a_nan, p6a_s, p6a_z, p6a_inc;
    reg signed [11:0] p6a_ebl;
    reg [23:0]        p6a_m24;
    always @(posedge clk) begin
        p6a_nan <= p5_nan; p6a_s <= p5_s; p6a_z <= p5_z; p6a_ebl <= p5_ebl;
        p6a_m24 <= p5_nm[40:17];
        p6a_inc <= p5_nm[16] & ((p5_nm[15:0] != 16'd0) | p5_nm[17]);
    end

    // -- S13: round to 24 bits (the golden's float32 of the exact dot) ------------------------------------------------
    wire [24:0] mr;
    wire        cmr;
    ot_v41_inc #(.W(25)) u_mr (.a({1'b0, p6a_m24}), .inc(p6a_inc), .y(mr), .co(cmr));
    reg               p6_nan, p6_s, p6_z;
    reg signed [11:0] p6_b;
    reg [22:0]        p6_f;
    always @(posedge clk) begin
        p6_nan <= p6a_nan; p6_s <= p6a_s; p6_z <= p6a_z;
        p6_b <= p6a_ebl + $signed({11'd0, mr[24]});
        p6_f <= mr[24] ? 23'd0 : mr[22:0];
    end

    // -- S14: subnormal shift amount -----------------------------------------------------------------------------------
    wire [11:0] rsh = 12'd1 - p6_b;
    reg               p7a_nan, p7a_s, p7a_sub, p7a_ovf, p7a_z;
    reg [4:0]         p7a_rs;
    reg [7:0]         p7a_b;
    reg [22:0]        p7a_f;
    always @(posedge clk) begin
        p7a_nan <= p6_nan; p7a_s <= p6_s; p7a_z <= p6_z; p7a_f <= p6_f; p7a_b <= p6_b[7:0];
        p7a_sub <= !p6_z && (p6_b < 12'sd1);
        p7a_ovf <= !p6_z && (p6_b > 12'sd254);
        p7a_rs <= (p6_b < -12'sd24) ? 5'd26 : rsh[4:0];
    end

    // -- S15: subnormal shift, sticky; normal / zero / inf pack --------------------------------------------------------
    wire [49:0] sw = {1'b1, p7a_f, 26'd0} >> p7a_rs;
    // NP-LANE: the subnormal shift from kept copies of the shift amount (one per 5-bit slice of the kept result
    // bits 49:25, MSB-first layers, plus one for the sticky window), bit-identical to sw / |sw[24:0]
    wire [49:0] swn;
    wire        swn_st;
    if (NP != 0) begin : g_np_s15
        wire [4:0] rk [0:5];
        for (genvar g = 0; g < 6; g = g + 1) begin : g_k
            ot_v41_kreg #(.W(5)) u_k (.clk(clk), .arst_n(1'b1), .d((p6_b < -12'sd24) ? 5'd26 : rsh[4:0]), .q(rk[g]));
        end
        wire [49:0] x = {1'b1, p7a_f, 26'd0};
        for (genvar g = 0; g < 5; g = g + 1) begin : g_s
            wire [4:0]  c = rk[g];
            wire [49:0] a16 = c[4] ? {16'd0, x[49:16]} : x;
            wire [49:0] a8  = c[3] ? {8'd0, a16[49:8]} : a16;
            wire [49:0] a4  = c[2] ? {4'd0, a8[49:4]} : a8;
            wire [49:0] a2  = c[1] ? {2'd0, a4[49:2]} : a4;
            wire [49:0] a1  = c[0] ? {1'd0, a2[49:1]} : a2;
            assign swn[25 + 5*g +: 5] = a1[25 + 5*g +: 5];
        end
        assign swn[24:0] = '0;
        // |(x >> r)[24:0]: g = {1, f} (g[k] = x[26 + k]) has a set bit k with r - 26 <= k <= r - 2
        wire [23:0] gx = {1'b1, p7a_f};
        reg st;
        always @* begin
            st = 1'b0;
            for (int k = 0; k < 24; k++)
`ifdef OT_NP_LANE_MUT_ST
                if (gx[k] && k + 1 <= rk[5] && k + 26 >= rk[5]) st = 1'b1;     // negative control: window one too wide
`else
                if (gx[k] && k + 2 <= rk[5] && k + 26 >= rk[5]) st = 1'b1;
`endif
        end
        assign swn_st = st;
    end else begin : g_o_s15
        assign swn = '0; assign swn_st = 1'b0;
    end
    reg               p7_nan, p7_sub, p7_ovf, p7_s;
    reg [31:0]        p7_n;
    reg [23:0]        p7_t;
    reg               p7_g, p7_st;
    wire [1:0]        p7_subk;        // NP-LANE: kept copies of p7_sub (the pack select halves)
    if (NP != 0) begin : g_np_sk
        for (genvar g = 0; g < 2; g = g + 1) begin : g_k
            ot_v41_kreg #(.W(1)) u_k (.clk(clk), .arst_n(1'b1), .d(p7a_sub), .q(p7_subk[g]));
        end
    end else begin : g_o_sk
        assign p7_subk = '0;
    end
    always @(posedge clk) begin
        p7_nan <= p7a_nan; p7_s <= p7a_s; p7_sub <= p7a_sub; p7_ovf <= p7a_ovf;
        if (p7a_z)        p7_n <= 32'd0;
        else if (p7a_ovf) p7_n <= {p7a_s, 8'hFF, 23'd0};
        else              p7_n <= {p7a_s, p7a_b, p7a_f};
        p7_t <= (NP != 0) ? swn[49:26] : sw[49:26];
        p7_g <= (NP != 0) ? swn[25] : sw[25];
        p7_st <= (NP != 0) ? swn_st : (sw[24:0] != 25'd0);
    end

    // -- S16: subnormal round and pack -----------------------------------------------------------------------------------
    wire        inc8 = p7_g & (p7_st | p7_t[0]);
    wire [23:0] tr;
    wire        ctr;
    ot_v41_inc #(.W(24)) u_tr (.a(p7_t), .inc(inc8), .y(tr), .co(ctr));
    reg         p8_f;
    reg [31:0]  p8_y;
    always @(posedge clk) begin
        p8_f <= p7_nan | p7_ovf;
        p8_y <= (NP != 0) ? {p7_subk[1] ? {p7_s, 7'd0, tr[23:16]} : p7_n[31:16], p7_subk[0] ? tr[15:0] : p7_n[15:0]}
                          : (p7_sub ? {p7_s, 7'd0, tr} : p7_n);
    end

    assign ov = vs[LATENCY-1];
    assign y = p8_y;
    assign f = p8_f;
    ot_hdc_delay #(.W(TW), .D(LATENCY)) u_tag (.clk(clk), .rst_n(rst_n), .d(tag), .q(otag));
    // NP-LANE: OK kept copies of the last tag stage's slot field (a parallel line one stage shorter, whose flops equal
    // u_tag's and merge with them, then the copies): each consumer slice loads its own copy
    if (NP != 0) begin : g_np_tk
        wire [OKW-1:0] tk1;
        ot_hdc_delay #(.W(OKW), .D(LATENCY - 1)) u_tk (.clk(clk), .rst_n(rst_n), .d(tag[TW-1 -: OKW]), .q(tk1));
        for (genvar j = 0; j < OK; j = j + 1) begin : g_k
            ot_v41_kreg #(.W(OKW)) u_k (.clk(clk), .arst_n(1'b1), .d(tk1), .q(otag_k[j*OKW +: OKW]));
        end
    end else begin : g_o_tk
        assign otag_k = '0;
    end
endmodule
