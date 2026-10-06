`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_aq12m: the MARGIN restaging of ot_dsrom_aq12f (DS-ROM field spine v13, owner margin-first rule 2026-10-06:
// every block-internal SS setup path closes with >= +60 ps at 0.833 ns, i.e. routes at a 0.770 ns clock).  Bit for bit
// the function of ot_dsrom_aq12f / ot_dsrom_aq12 (FP8 path of ot_hdc_actquant; tools/hdc_golden_v41.quant_fp8); the same
// ports; every output sequence identical, LATENCY - 18 cycles later (rtl/test/dsrom_sys/tb_aq12m_eq.sv, lockstep).
// The v11 routed quantiser classes (slack at 0.833 ns, SS 60 ps), each given a register stage:
//   * s0_x -> m1 and m_k -> m_k+1 (+2..+34 ps): every max-tree level is two stages, the Kogge-Stone compare registered
//     (ge bits + the operands passed on) and then the select;
//   * m4 -> amax (+24 ps): the three S5 compares registered, the amax select in its own stage;
//   * amax -> multiplier stage 1 and the multiplier's internal stages (+21..+51 ps): the scale product is the f12
//     binary32 multiplier with EVERY cut (ot_hdc_fp32_mul_f12 CUTS 8'hFF, LAT 9; fixed top ot_dsrom_aq12m_mul so
//     synthesis keeps it as its own hierarchy);
//   * multiplier y -> the S11 kept copies (+28 ps): ceil_log2(prod) registered once (ce_r), the copies after it;
//   * S11 copies -> S12 subtracts (+40 ps): eight kept copies (4 lanes each, was 4 x 8) and each lane's max(fld, 1)
//     precomputed into a register, so S12 is one 11-bit subtract from two registers;
//   * S13 shift -> S14 sticky (+65 ps): the rounding shift registered (51 bits a lane), the sticky OR in the next stage.
// LATENCY 29 (aq12f 18): S0 | 4 x (compare | select) | S5 compare | amax | 9 multiply | ce | copies | S12 | S13 |
// shift | sticky | S15 | S16 | out.
// ---------------------------------------------------------------------------
module ot_dsrom_aq12m (
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
    localparam integer LATENCY = 29;
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    integer i;

    wire [LATENCY:0] vl;
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    // register cycle k reads cycle k-1: s0_x at 1; elements wait to the max(fld, 1) stage at 22 (xg at 21: 20 registers)
    reg  [1023:0] s0_x;
    always @(posedge clk) s0_x <= x;
    wire [1023:0] xg;
    ot_hdc_delay #(.W(1024), .D(20)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(xg));

    // -- max tree: level L compares at cycle 2L, selects at 2L + 1 (m1 3, m2 5, m3 7, m4 9) -----------------------
    reg [30:0] c1a [0:15], c1b [0:15];
    reg [30:0] m1 [0:15];
    reg [30:0] c2a [0:7],  c2b [0:7];
    reg [30:0] m2 [0:7];
    reg [30:0] c3a [0:3],  c3b [0:3];
    reg [30:0] m3 [0:3];
    reg [30:0] c4a [0:1],  c4b [0:1];
    reg [30:0] m4 [0:1];
    reg [15:0] g1r;
    reg [7:0]  g2r;
    reg [3:0]  g3r;
    reg [1:0]  g4r;
    reg  [3:0] nf1;                  // four 8-lane partial ORs (cycle 2), reduced at 3
    reg        nf2;
    reg  [3:0] nfx;
    always @(*) begin
        nfx = 4'd0;
        for (i = 0; i < 32; i = i + 1) nfx[i/8] = nfx[i/8] | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end
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
            ot_v41_ksadd #(.W(31)) u_ge (.a(m2[2*gk]), .b(~m2[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge3[gk]));
        end
        for (gk = 0; gk < 2; gk = gk + 1) begin : g_c4
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(m3[2*gk]), .b(~m3[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge4[gk]));
        end
    endgenerate
    always @(posedge clk) begin
        g1r <= ge1;
        for (i = 0; i < 16; i = i + 1) begin c1a[i] <= s0_x[64*i +: 31]; c1b[i] <= s0_x[64*i + 32 +: 31]; end
        for (i = 0; i < 16; i = i + 1) m1[i] <= g1r[i] ? c1a[i] : c1b[i];
        g2r <= ge2;
        for (i = 0; i < 8; i = i + 1) begin c2a[i] <= m1[2*i]; c2b[i] <= m1[2*i+1]; end
        for (i = 0; i < 8; i = i + 1) m2[i] <= g2r[i] ? c2a[i] : c2b[i];
        g3r <= ge3;
        for (i = 0; i < 4; i = i + 1) begin c3a[i] <= m2[2*i]; c3b[i] <= m2[2*i+1]; end
        for (i = 0; i < 4; i = i + 1) m3[i] <= g3r[i] ? c3a[i] : c3b[i];
        g4r <= ge4;
        for (i = 0; i < 2; i = i + 1) begin c4a[i] <= m3[2*i]; c4b[i] <= m3[2*i+1]; end
`ifdef OT_AQ12M_MUT_SEL
        for (i = 0; i < 2; i = i + 1) m4[i] <= g4r[i] ? c4b[i] : c4a[i];
`else
        for (i = 0; i < 2; i = i + 1) m4[i] <= g4r[i] ? c4a[i] : c4b[i];
`endif
        nf1 <= nfx; nf2 <= |nf1;
    end
    // -- S5: max(m4[0], m4[1], floor): the three compares registered (cycle 10), the select (amax, cycle 11) -----
    reg [30:0] amax, m4a, m4b;
    reg        abr, afr, bfr;
    wire ab, af, bf;
    wire [30:0] sd_ab, sd_af, sd_bf;
    ot_v41_ksadd #(.W(31)) u_ab (.a(m4[0]), .b(~m4[1]), .cin(1'b1), .s(sd_ab), .cout(ab));
    ot_v41_ksadd #(.W(31)) u_af (.a(m4[0]), .b(~FLOOR_FP8), .cin(1'b1), .s(sd_af), .cout(af));
    ot_v41_ksadd #(.W(31)) u_bf (.a(m4[1]), .b(~FLOOR_FP8), .cin(1'b1), .s(sd_bf), .cout(bf));
    always @(posedge clk) begin
        abr <= ab; afr <= af; bfr <= bf; m4a <= m4[0]; m4b <= m4[1];
        amax <= (abr && afr) ? m4a : (!abr && bfr) ? m4b : FLOOR_FP8;
    end

    // -- cycles 12..20: amax * (1/448), every multiplier cut (LAT 9) ------------------------------------------
    wire [31:0] prod;
    wire [1:0]  perr;
    wire        pvo;
    ot_dsrom_aq12m_mul u_scale (.clk(clk), .rst_n(rst_n), .valid_in(vl[11]), .a({1'b0, amax}), .b(INV_448), .y(prod),
                                .err(perr), .valid_out(pvo));
    wire pfault = pvo && (perr != 2'd0);
    wire nf20;                                   // nf2 (cycle 3) aligned with prod (cycle 20)
    ot_hdc_delay #(.W(1), .D(17)) u_nf (.clk(clk), .rst_n(rst_n), .d(nf2), .q(nf20));

    // -- cycle 21: ce = ceil_log2(prod) + 127 registered once -------------------------------------------------------
    reg [8:0] ce_r;
    reg       ce_nf;
    always @(posedge clk) begin
        ce_r <= {1'b0, prod[30:23]} + {8'd0, (prod[22:0] != 23'd0)};
        ce_nf <= nf20 | pfault;
    end
    // -- cycle 22 (S11): e, and {e + 121 (dm), e + 127 (ep)} in eight kept copies, copy k feeding lanes 4k..4k+3 ----
    //    each lane's max(fld, 1) and the S12 pass-through fields registered from xg in the same cycle
    reg signed [9:0]  s11_e;
    reg               s11_nf;
    wire signed [10:0] ep_d = $signed({2'b00, ce_r});
    wire signed [10:0] dm_d = $signed({2'b00, ce_r}) - 11'sd6;
    wire [175:0] s11_epdm;                    // copy k: {dm, ep} at [22k +: 22]
    generate
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_s11c
            ot_v41_kreg #(.W(22)) u_c (.clk(clk), .arst_n(1'b1), .d({dm_d, ep_d}), .q(s11_epdm[22*gk +: 22]));
        end
    endgenerate
    reg [7:0]  s11_ev [0:31];                 // max(fld, 1)
    reg [23:0] s11_sig [0:31];
    reg [31:0] s11_sgn;
    reg [7:0]  fld;
    always @(posedge clk) begin
        s11_e <= $signed({1'b0, ce_r}) - 10'sd127;
        s11_nf <= ce_nf;
        for (i = 0; i < 32; i = i + 1) begin
            fld = xg[32*i + 23 +: 8];
            s11_ev[i] <= (fld == 8'd0) ? 8'd1 : fld;
            s11_sig[i] <= {(fld != 8'd0), xg[32*i +: 23]};
            s11_sgn[i] <= xg[32*i + 31] && (xg[32*i +: 31] != 31'd0);
        end
    end

    // -- cycle 23 (S12): per-element exponent difference dd = -6 - (exp(x) - e) ------------------------------------
    reg signed [10:0] s12_ev [0:31];
    reg signed [10:0] s12_dd [0:31];
    reg [23:0]        s12_sig [0:31];
    reg [31:0]        s12_sgn;
    reg signed [9:0]  s12_e;
    reg               s12_nf;
    reg signed [10:0] ev;
    always @(posedge clk) begin
        s12_e <= s11_e; s12_nf <= s11_nf; s12_sgn <= s11_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            ev = $signed({3'b000, s11_ev[i]});
            s12_ev[i] <= ev - $signed(s11_epdm[22*(i/4) +: 11]);
`ifdef OT_AQ12M_MUT_DD
            s12_dd[i] <= $signed(s11_epdm[22*(i/4) +: 11]) - ev;
`else
            s12_dd[i] <= $signed(s11_epdm[22*(i/4) + 11 +: 11]) - ev;
`endif
            s12_sig[i] <= s11_sig[i];
        end
    end
    // -- cycle 24 (S13): grid exponent and shift ------------------------------------------------------------------
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
    // -- cycle 25 (S14a): the rounding shift, registered (51 bits a lane) ---------------------------------------
    reg [50:0]       s14_w [0:31];
    reg [31:0]       s14a_sgn;
    reg signed [4:0] s14a_g [0:31];
    reg signed [9:0] s14a_e;
    reg              s14a_nf;
    always @(posedge clk) begin
        s14a_e <= s13_e; s14a_nf <= s13_nf; s14a_sgn <= s13_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s14_w[i] <= {s13_sig[i], 27'd0} >> s13_rs[i];
            s14a_g[i] <= s13_g[i];
        end
    end
    // -- cycle 26 (S14b): quotient, guard and the sticky OR --------------------------------------------------------
    reg [23:0]       s14_tq [0:31];
    reg [31:0]       s14_gd, s14_st, s14_sgn;
    reg signed [4:0] s14_g [0:31];
    reg signed [9:0] s14_e;
    reg              s14_nf;
    always @(posedge clk) begin
        s14_e <= s14a_e; s14_nf <= s14a_nf; s14_sgn <= s14a_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s14_tq[i] <= s14_w[i][50:27];
            s14_gd[i] <= s14_w[i][26];
`ifdef OT_AQ12M_MUT_ST
            s14_st[i] <= 1'b0;                                           // mutant: sticky dropped
`else
            s14_st[i] <= (s14_w[i][25:0] != 26'd0);
`endif
            s14_g[i] <= s14a_g[i];
        end
    end
    // -- cycle 27 (S15): round to the grid -------------------------------------------------------------------------
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
    // -- cycle 28 (S16): encode terms ------------------------------------------------------------------------------
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
    // -- cycle 29 (S17): codes and dequantised BF16 (output registers) ----------------------------------------------
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

// the scale multiplier with every f12 cut point (LAT 9): a plain module name, kept as its own synthesis hierarchy
module ot_dsrom_aq12m_mul (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                           output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_f12 #(.CUTS(8'hFF)) u (.*);
endmodule
