`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// FP8 activation quantiser at 1.2 GHz (DS-ROM recovery lever su_norm): the FP8 path (fp4 = 0) of
// rtl/hdc/v41/ot_hdc_actquant.sv, bit for bit, re-staged for 0.833 ns at ASAP7 SS.  ot_hdc_actquant screens at
// 745 MHz (its 2-level compare stages, the ot_fp32_mul_pipe scale multiply and the per-element shift / round /
// encode stages each miss by 100-510 ps), so:
//   * the 32 -> 1 magnitude max is one compare level a stage (5 stages; the 1e-4 floor joins the last level as a
//     three-way select of parallel compares);
//   * the scale product amax * float32(1/448) is the 1.2 GHz f12 multiplier (ot_hdc_qmul_lat LAT 5 through
//     rtl/hdc/ot_hdc_fastfp_lat_f12.sv): both are binary32 RNE, and amax >= 1e-4 keeps the product normal
//     (>= 2.2e-7), where every RNE multiplier is the same function;
//   * the per-element grid exponent, the rounding shift and the encode are two stages each.
// Function (tools/hdc_golden_v41.quant_fp8 / qdq_fp8): amax = max(max|x|, 1e-4); e = ceil_log2(RN(amax / 448));
// codes E4M3 of x * 2^-e (RNE); y = codes * 2^e as BF16.  Nonfinite input raises `fault`.
// LATENCY 18 (vs 13): S0 | 5 max levels | 5 multiply | e | 2 grid | 2 round | 2 encode.
//
// ot_dsrom_aq12f (DS-ROM field spine v10, 2026-10-05): ot_dsrom_aq12 bit for bit, same LATENCY 18, with the three
// classes the v9 R128 spine screens left in the quantiser fixed (v9 post-GRT, keep-aq12 variants, SS 60 ps):
//   * s11_dm / s11_ep broadcast to the 32 lanes' S12 subtracts (c1r128 e/f: s11_dm -> s12_dd -11.1 ps, 12-13
//     endpoints; a fanout tree of ~280 ps ahead of the subtract): four kept copies (ot_v41_kreg), 8 lanes each;
//   * the max tree's compares (c0r128 e/f: m3 -> m4 -2.5 / -4.3 ps, amax +10 ps; ABC maps a 31-bit `>=` as an
//     OR4/OR3 ripple of ~450 ps ahead of the select fanout): every compare (m1..m4 levels and S5) is the carry out
//     of a kept Kogge-Stone a + ~b + 1 (rtl/common/ot_prefix.sv ot_v41_ksadd), log2 depth;
//   * the 32-lane nonfinite OR into nf1 (c1r128_ek placement estimate -31.7 ps): four 8-lane partial ORs
//     registered at S1, reduced at S2 (nf2), so nf10 is unchanged in time.
// ot_dsrom_aq12 itself stays byte-identical (tools/dsrom_su_transport_measure.py and su records pin it).
// ---------------------------------------------------------------------------
module ot_dsrom_aq12f (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault
);
    localparam integer LATENCY = 18;
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    integer i;

    wire [LATENCY:0] vl;
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    // elements wait from S0 to the grid stage (S0 + 5 + 5 + 1 = 11 registers)
    reg  [1023:0] s0_x;
    always @(posedge clk) s0_x <= x;
    wire [1023:0] xg;
    ot_hdc_delay #(.W(1024), .D(11)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(xg));

    // -- S1..S4: 32 -> 2, one compare level a stage ---------------------------------------------
    reg [30:0] m1 [0:15];
    reg [30:0] m2 [0:7];
    reg [30:0] m3 [0:3];
    reg [30:0] m4 [0:1];
    reg  [3:0] nf1;                  // four 8-lane partial ORs (S1), reduced at S2
    reg        nf2, nf3, nf4, nf5;
    reg  [3:0] nfx;
    always @(*) begin
        nfx = 4'd0;
        for (i = 0; i < 32; i = i + 1) nfx[i/8] = nfx[i/8] | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end
    // a >= b as the carry out of a + ~b + 1 through a kept Kogge-Stone prefix (unsigned, 31 bits)
    // compare inputs: level 1 lanes 2k / 2k+1 of s0_x, levels 2..4 pairs of the previous level
    wire [15:0] ge1;
    wire [7:0]  ge2;
    wire [3:0]  ge3;
    wire [1:0]  ge4;
    genvar gk;
    generate
        for (gk = 0; gk < 16; gk = gk + 1) begin : g_c1
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(s0_x[64*gk +: 31]), .b(~s0_x[64*gk + 32 +: 31]), .cin(1'b1), .s(sd), .cout(ge1[gk]));
        end
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_c2
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(m1[2*gk]), .b(~m1[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge2[gk]));
        end
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_c3
            wire [30:0] sd;
            `ifdef OT_AQ12F_MUT_GE
            ot_v41_ksadd #(.W(31)) u_ge (.a(m2[2*gk]), .b(m2[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge3[gk]));
`else
            ot_v41_ksadd #(.W(31)) u_ge (.a(m2[2*gk]), .b(~m2[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge3[gk]));
`endif
        end
        for (gk = 0; gk < 2; gk = gk + 1) begin : g_c4
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(m3[2*gk]), .b(~m3[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge4[gk]));
        end
    endgenerate
    always @(posedge clk) begin
        for (i = 0; i < 16; i = i + 1) m1[i] <= ge1[i] ? s0_x[64*i +: 31] : s0_x[64*i + 32 +: 31];
        for (i = 0; i < 8; i = i + 1)  m2[i] <= ge2[i] ? m1[2*i] : m1[2*i+1];
        for (i = 0; i < 4; i = i + 1)  m3[i] <= ge3[i] ? m2[2*i] : m2[2*i+1];
`ifdef OT_AQ12F_MUT_SEL
        for (i = 0; i < 2; i = i + 1)  m4[i] <= ge4[i] ? m3[2*i+1] : m3[2*i];
`else
        for (i = 0; i < 2; i = i + 1)  m4[i] <= ge4[i] ? m3[2*i] : m3[2*i+1];
`endif
        nf1 <= nfx; nf2 <= |nf1; nf3 <= nf2; nf4 <= nf3; nf5 <= nf4;
    end
    // -- S5: max(m4[0], m4[1], floor): three parallel compares and a select -----------------------
    reg [30:0] amax;
    wire ab, af, bf;
    wire [30:0] sd_ab, sd_af, sd_bf;
    ot_v41_ksadd #(.W(31)) u_ab (.a(m4[0]), .b(~m4[1]), .cin(1'b1), .s(sd_ab), .cout(ab));
    ot_v41_ksadd #(.W(31)) u_af (.a(m4[0]), .b(~FLOOR_FP8), .cin(1'b1), .s(sd_af), .cout(af));
    ot_v41_ksadd #(.W(31)) u_bf (.a(m4[1]), .b(~FLOOR_FP8), .cin(1'b1), .s(sd_bf), .cout(bf));
    always @(posedge clk) amax <= (ab && af) ? m4[0] : (!ab && bf) ? m4[1] : FLOOR_FP8;

    // -- S6..S10: amax * (1/448) ----------------------------------------------------------------
    wire [31:0] prod;
    wire        pfault;
    ot_hdc_qmul_lat #(5) u_scale (clk, rst_n, vl[6], {1'b0, amax}, INV_448, prod, pfault);
    wire nf10;
    ot_hdc_delay #(.W(1), .D(5)) u_nf (.clk(clk), .rst_n(rst_n), .d(nf5), .q(nf10));

    // -- S11: e = ceil_log2(prod) -----------------------------------------------------------------
    // also e + 127 and e + 121, so S12's two exponent differences are one subtract each, in parallel
    // s11_ep / s11_dm: four kept copies (ot_v41_kreg), copy k feeding lanes 8k..8k+7 of S12
    reg signed [9:0]  s11_e;
    reg               s11_nf;
    wire [8:0] ce = {1'b0, prod[30:23]} + {8'd0, (prod[22:0] != 23'd0)};     // ceil_log2 + 127
    wire signed [10:0] ep_d = $signed({2'b00, ce});
    wire signed [10:0] dm_d = $signed({2'b00, ce}) - 11'sd6;
    wire [87:0] s11_epdm;                     // copy k: {dm, ep} at [22k +: 22]
    generate
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_s11c
            ot_v41_kreg #(.W(22)) u_c (.clk(clk), .arst_n(1'b1), .d({dm_d, ep_d}), .q(s11_epdm[22*gk +: 22]));
        end
    endgenerate
    always @(posedge clk) begin
        s11_e <= $signed({1'b0, ce}) - 10'sd127;
        s11_nf <= nf10 | pfault;
    end

    // -- S12: per-element exponent difference dd = -6 - (exp(x) - e) ----------------------------------
    reg signed [10:0] s12_ev [0:31];
    reg signed [10:0] s12_dd [0:31];
    reg [23:0]        s12_sig [0:31];
    reg [31:0]        s12_sgn;
    reg signed [9:0]  s12_e;
    reg               s12_nf;
    reg [7:0]         fld;
    reg signed [10:0] ev;   // max(fld, 1)
    always @(posedge clk) begin
        s12_e <= s11_e; s12_nf <= s11_nf;
        for (i = 0; i < 32; i = i + 1) begin
            fld = xg[32*i + 23 +: 8];
            //: ev = exp(x) - e with exp(x) = max(fld, 1) - 127;  dd = -6 - ev = (e + 121) - max(fld, 1)
            ev = $signed({3'b000, (fld == 8'd0) ? 8'd1 : fld});
            s12_ev[i] <= ev - $signed(s11_epdm[22*(i/8) +: 11]);
`ifdef OT_AQ12F_MUT_DD
            s12_dd[i] <= $signed(s11_epdm[22*(i/8) +: 11]) - ev;
`else
            s12_dd[i] <= $signed(s11_epdm[22*(i/8) + 11 +: 11]) - ev;
`endif
            s12_sig[i] <= {(fld != 8'd0), xg[32*i +: 23]};
            s12_sgn[i] <= xg[32*i + 31] && (xg[32*i +: 31] != 31'd0);
        end
    end
    // -- S13: grid exponent and shift ------------------------------------------------------------------
    reg [23:0]       s13_sig [0:31];
    reg [4:0]        s13_rs [0:31];
    reg signed [4:0] s13_g [0:31];
    reg [31:0]       s13_sgn;
    reg signed [9:0] s13_e;
    reg              s13_nf;
    always @(posedge clk) begin
        s13_e <= s12_e; s13_nf <= s12_nf; s13_sgn <= s12_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s13_sig[i] <= s12_sig[i];
            if (s12_dd[i] > 11'sd0) begin
                s13_g[i] <= -5'sd6;
                s13_rs[i] <= (s12_dd[i] > 11'sd6) ? 5'd26 : (5'd20 + s12_dd[i][4:0]);
            end else begin
                s13_g[i] <= s12_ev[i][4:0];
                s13_rs[i] <= 5'd20;
            end
        end
    end
    // -- S14: the rounding shift ----------------------------------------------------------------------
    reg [23:0]       s14_tq [0:31];
    reg [31:0]       s14_gd, s14_st, s14_sgn;
    reg signed [4:0] s14_g [0:31];
    reg signed [9:0] s14_e;
    reg              s14_nf;
    reg [50:0]       wide;
    always @(posedge clk) begin
        s14_e <= s13_e; s14_nf <= s13_nf; s14_sgn <= s13_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            wide = {s13_sig[i], 27'd0} >> s13_rs[i];
            s14_tq[i] <= wide[50:27];
            s14_gd[i] <= wide[26];
            s14_st[i] <= (wide[25:0] != 26'd0);
            s14_g[i] <= s13_g[i];
        end
    end
    // -- S15: round to the grid -------------------------------------------------------------------------
    reg [4:0]        s15_c [0:31];
    reg signed [4:0] s15_g [0:31];
    reg [31:0]       s15_sgn;
    reg signed [9:0] s15_e;
    reg              s15_nf;
    always @(posedge clk) begin
        s15_e <= s14_e; s15_nf <= s14_nf; s15_sgn <= s14_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s15_c[i] <= s14_tq[i][4:0] + {4'd0, s14_gd[i] & (s14_st[i] | s14_tq[i][0])};
            s15_g[i] <= s14_g[i];
        end
    end
    // -- S16: encode terms ------------------------------------------------------------------------------
    reg [4:0]         s16_c [0:31];
    reg [3:0]         s16_g4 [0:31];
    reg signed [11:0] s16_be [0:31];
    reg [7:0]         s16_cn [0:31];
    reg [6:0]         s16_sub [0:31];
    reg [31:0]        s16_sgn;
    reg signed [9:0]  s16_e;
    reg               s16_nf;
    reg [2:0]         p;
    reg [4:0]         c;
    reg signed [11:0] shs;
    always @(posedge clk) begin
        s16_e <= s15_e; s16_nf <= s15_nf; s16_sgn <= s15_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            c = s15_c[i];
            p = c[4] ? 3'd4 : c[3] ? 3'd3 : c[2] ? 3'd2 : c[1] ? 3'd1 : 3'd0;
            s16_c[i] <= c;
            s16_g4[i] <= s15_g[i][3:0];
            s16_be[i] <= $signed({9'd0, p}) + s15_g[i] - 12'sd3 + s15_e + 12'sd127;
            s16_cn[i] <= {3'd0, c} << (3'd7 - p);
            shs = s15_g[i] - 12'sd3 + s15_e + 12'sd133;
            s16_sub[i] <= (shs < 12'sd0) ? 7'd0 : ({2'd0, c} << shs[3:0]);
        end
    end
    // -- S17: codes and dequantised BF16 (output registers) ----------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= vl[LATENCY - 1]; fault <= vl[LATENCY - 1] && s16_nf; end
    end
    always @(posedge clk) begin
        e <= s16_e;
        for (i = 0; i < 32; i = i + 1) begin
            if (s16_c[i][4])      q[8*i +: 8] <= {s16_sgn[i], s16_g4[i] + 4'd8, 3'd0};
            else if (s16_c[i][3]) q[8*i +: 8] <= {s16_sgn[i], s16_g4[i] + 4'd7, s16_c[i][2:0]};
            else                  q[8*i +: 8] <= {s16_sgn[i], 4'd0, s16_c[i][2:0]};
            if (s16_c[i] == 5'd0)          y[16*i +: 16] <= {s16_sgn[i], 15'd0};
            else if (s16_be[i] >= 12'sd255) y[16*i +: 16] <= {s16_sgn[i], 8'hFF, 7'd0};
            else if (s16_be[i] >= 12'sd1)   y[16*i +: 16] <= {s16_sgn[i], s16_be[i][7:0], s16_cn[i][6:0]};
            else                            y[16*i +: 16] <= {s16_sgn[i], 8'd0, s16_sub[i]};
        end
    end
endmodule
