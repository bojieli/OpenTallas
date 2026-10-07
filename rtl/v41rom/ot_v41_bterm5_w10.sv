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
    parameter integer FPC = 4,        // kept copies of the FP4 select (32 = one per lane: q-element QM >= 5)
    parameter integer P0B = 0         // 2 (Z29b post-CTS at 730: the S1b copy sat beside the decode, the wire stayed in
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
    output wire [TW-1:0]     otag
);
    localparam integer W = 42;
    localparam integer LATENCY = 17 + (P0B != 0 ? 1 : 0);
    function automatic [7:0] e2m1(input [3:0] c);
        if (c[2:1] == 2'd0) e2m1 = {c[3], c[0] ? 4'd6 : 4'd0, 3'd0};
        else                e2m1 = {c[3], {2'b00, c[2:1]} + 4'd6, c[0], 2'b00};
    endfunction
    integer i;

    // valid chain (async reset), one bit a stage
    reg [LATENCY-1:0] vs;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vs <= '0;
        else vs <= {vs[LATENCY-2:0], v};

    // -- S0: input capture ------------------------------------------------------------------------------
    // the FP4 select in four kept copies (ot_v41_kreg: never merged with the tag delay line's copy of the same bit,
    // Z24b post-CTS: a merged fp4 flop in the tag line drove all 32 lanes' decode, -190 ps), one per 8 lanes
    wire [FPC-1:0]   m_fp4;
    for (genvar g = 0; g < FPC; g = g + 1) begin : g_f4
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
            wc = m_fp4[(i * FPC) / 32] ? e2m1(m_wq[8*i +: 4]) : m_wq[8*i +: 8];
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
                q0_pm[i] <= p0_xs[i] * p0_ws[i];
                q0_sh[i] <= {1'b0, p0_xf[i]} + {1'b0, p0_wf[i]} - 5'd2;
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

    // -- S2: product, shift amount --------------------------------------------------------------------
    reg               pa_sg [0:31];
    reg [7:0]         pa_pm [0:31];
    reg [4:0]         pa_sh [0:31];
    reg               pa_nan;
    reg signed [10:0] pa_es;
    always @(posedge clk) begin
        pa_es <= q0_es;
`ifdef BT5_MUTANT_NS
        pa_nan <= (P0B != 0 ? |q0_nan[5:0] : |q0_nan[23:0]);                                   // negative control: 8 lanes dropped
`else
        pa_nan <= |q0_nan;
`endif
        for (i = 0; i < 32; i = i + 1) begin
            pa_sg[i] <= q0_sg[i];
            pa_pm[i] <= (P0B >= 2) ? q0_pm[i] : q0_xs[i] * q0_ws[i];
            pa_sh[i] <= (P0B >= 2) ? q0_sh[i] : {1'b0, q0_xf[i]} + {1'b0, q0_wf[i]} - 5'd2;
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
    always @(*)
        for (i = 0; i < 32; i = i + 1)
            terms[W*i +: W] = {{(W-12){p1_q[i][11]}}, p1_q[i]} << {p1_sq[i], 2'b00};
    wire [15*W-1:0] c15;
    ot_v41_csa #(.N(32), .M(15), .W(W)) u_csa1 (.d(terms), .q(c15));
    reg [15*W-1:0]    p2h_c;
    reg               p2h_nan;
    reg signed [10:0] p2h_es;
    always @(posedge clk) begin p2h_c <= c15; p2h_nan <= p1_nan; p2h_es <= p1_es; end

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
    always @(posedge clk) begin
        p4_nan <= p4a_nan;
        p4_eb <= p4a_es + 12'sd149;
        p4_s <= p4a_s[W-1];
        p4_m <= p4a_s[W-1] ? ng[W-2:0] : p4a_s[W-2:0];
    end

    // -- S9: normalise 32 / 16 ---------------------------------------------------------------------------------
    reg [40:0] nma;
    reg [5:0]  lza;
    always @(*) begin
        nma = p4_m; lza = 6'd0;
        if (nma[40:9]  == 32'd0) begin nma = nma << 32; lza = lza + 6'd32; end
        if (nma[40:25] == 16'd0) begin nma = nma << 16; lza = lza + 6'd16; end
    end
    reg               p5a_nan, p5a_s, p5a_z;
    reg signed [11:0] p5a_eb;
    reg [40:0]        p5a_nm;
    reg [5:0]         p5a_lz;
    always @(posedge clk) begin
        p5a_nan <= p4_nan; p5a_s <= p4_s; p5a_z <= (p4_m == 41'd0);
        p5a_eb <= p4_eb; p5a_nm <= nma; p5a_lz <= lza;
    end

    // -- S10: normalise 8 / 4 -----------------------------------------------------------------------------------
    reg [40:0] nmb;
    reg [5:0]  lzb;
    always @(*) begin
        nmb = p5a_nm; lzb = p5a_lz;
        if (nmb[40:33] == 8'd0) begin nmb = nmb << 8; lzb = lzb + 6'd8; end
        if (nmb[40:37] == 4'd0) begin nmb = nmb << 4; lzb = lzb + 6'd4; end
    end
    reg               p5b_nan, p5b_s, p5b_z;
    reg signed [11:0] p5b_eb;
    reg [40:0]        p5b_nm;
    reg [5:0]         p5b_lz;
    always @(posedge clk) begin
        p5b_nan <= p5a_nan; p5b_s <= p5a_s; p5b_z <= p5a_z;
        p5b_eb <= p5a_eb; p5b_nm <= nmb; p5b_lz <= lzb;
    end

    // -- S11: normalise 2 / 1, leading-bit exponent ----------------------------------------------------------------
    reg [40:0] nm;
    reg [5:0]  lz;
    always @(*) begin
        nm = p5b_nm; lz = p5b_lz;
        if (nm[40:39] == 2'd0) begin nm = nm << 2; lz = lz + 6'd2; end
        if (nm[40] == 1'b0)    begin nm = nm << 1; lz = lz + 6'd1; end
    end
    reg               p5_nan, p5_s, p5_z;
    reg signed [11:0] p5_ebl;
    reg [40:0]        p5_nm;
    always @(posedge clk) begin
        p5_nan <= p5b_nan; p5_s <= p5b_s; p5_z <= p5b_z;
        p5_ebl <= p5b_eb - $signed({6'd0, lz}); p5_nm <= nm;
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
    reg               p7_nan, p7_sub, p7_ovf, p7_s;
    reg [31:0]        p7_n;
    reg [23:0]        p7_t;
    reg               p7_g, p7_st;
    always @(posedge clk) begin
        p7_nan <= p7a_nan; p7_s <= p7a_s; p7_sub <= p7a_sub; p7_ovf <= p7a_ovf;
        if (p7a_z)        p7_n <= 32'd0;
        else if (p7a_ovf) p7_n <= {p7a_s, 8'hFF, 23'd0};
        else              p7_n <= {p7a_s, p7a_b, p7a_f};
        p7_t <= sw[49:26];
        p7_g <= sw[25];
        p7_st <= (sw[24:0] != 25'd0);
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
        p8_y <= p7_sub ? {p7_s, 7'd0, tr} : p7_n;
    end

    assign ov = vs[LATENCY-1];
    assign y = p8_y;
    assign f = p8_f;
    ot_hdc_delay #(.W(TW), .D(LATENCY)) u_tag (.clk(clk), .rst_n(rst_n), .d(tag), .q(otag));
endmodule
