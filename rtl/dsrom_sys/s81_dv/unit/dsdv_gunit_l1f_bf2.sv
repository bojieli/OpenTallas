`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81e-FP (10-23, tree S81.STA.PAR.3, COORD tile review): F2 = the F band of the banded gunit l1f with SEAM PIN
// FLOPS.  Copy of dsdv_gunit_l1f_bf / _bp (dsdv_gunit_l1f_band.sv, untouched: the CLOSED A bands a0 / a1 bind it) with
//   (1) s0a / s0b / s1a / s1b / sf0 / vf_lo / vf_hi landed in face flops before the fold: +1 edge on the merge path
//       (gate l1fb_f 10-22: s0a[42] -> fold -> m1b -615 ps SS = 14 logic levels behind an unregistered seam pin);
//   (2) ctl_hi leaves its own kept copy of {s_bn, s_l, s_f, s_v} (one flop per face; zero edges).
// dsdv_gunit_l1f_bp2 = wires-only flat parent (A bands unchanged + F2).  Proof: run_l1f_band2.sh (dsdv_gunit golden bench
// with the banded F2 l1f driving, merge outputs compared one edge late, gather outputs on the same edge).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l1f_bf2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    sa_r, input wire [223:0] sa_d, input wire [5:0] sb_r, input wire [223:0] sb_d,
    input  wire [13:0]   we,
    input  wire          c_go, input wire c_fw, input wire c_l, input wire [2:0] c_bn, input wire [4:0] c_lvn,
    input  wire          g_go, input wire [5:0] g_hit, input wire [41:0] g_a,
    output wire [255:0]  sv_lo, output wire [255:0] sv_hi,
    output wire [13:0]   ctl_lo, output wire [13:0] ctl_hi,
    input  wire [327:0]  s0a, input wire [327:0] s0b, input wire [2:0] sf0, input wire [23:0] vf_lo,
    input  wire [327:0]  s1a, input wire [327:0] s1b, input wire [23:0] vf_hi,
    output reg           o_v, output reg o_f, output reg o_l, output reg o_g, output reg [245:0] o_d,
    output reg           o_flt
);
    localparam integer EW = 41, LW = 8 * EW, NL = 16, NS = 7 * NL;
`ifdef OT_S81_GUNIT_FWDOWN
    localparam integer NW = 24, ND = 8, NB = 32, NG = 4, NQ = 18, NR = 21;
`else
    localparam integer NW = 9, ND = 5, NB = 32, NG = 4, NQ = 18, NR = 13;
`endif
    integer i, j, k;
    genvar g, l, h, t;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops (dsdv_gunit_l1f, unchanged)
    (* keep *) reg [NW*14-1:0]  wqc;
    (* keep *) reg [NW*6-1:0]   arc, brc;
    (* keep *) reg [ND*224-1:0] adc, bdc;
    (* keep *) reg [NB*3-1:0]   cbc;
    (* keep *) reg [3:0]        cfwc;
    (* keep *) reg [NG*6-1:0]   ghc;
    (* keep *) reg [NG*42-1:0]  gac;
    reg cgo, cl, gq; reg [4:0] clv;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_wq
`ifdef OT_S81_GUNIT_FWDOWN
            localparam integer WR_REGION=(g<8)?g/2:13+(g-8)/2;
`else
            localparam integer WR_REGION=g/2;
`endif
            always @(posedge clk or negedge rq[WR_REGION])
                if (!rq[WR_REGION]) wqc[14 * g +: 14] <= 14'd0; else wqc[14 * g +: 14] <= we;
            always @(posedge clk) begin arc[6 * g +: 6] <= sa_r; brc[6 * g +: 6] <= sb_r; end
        end
        for (g = 0; g < ND; g = g + 1) begin : g_dq
            always @(posedge clk) begin adc[224 * g +: 224] <= sa_d; bdc[224 * g +: 224] <= sb_d; end
        end
        for (g = 0; g < NB; g = g + 1) begin : g_bq
            always @(posedge clk) cbc[3 * g +: 3] <= c_bn;
        end
        for (g = 0; g < NG; g = g + 1) begin : g_gq
            always @(posedge clk) begin ghc[6 * g +: 6] <= g_hit; gac[42 * g +: 42] <= g_a; end
        end
    endgenerate
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin cgo <= 1'b0; gq <= 1'b0; end
        else begin cgo <= c_go; gq <= g_go; end
    always @(posedge clk) begin cfwc <= {4{c_fw}}; cl <= c_l; clv <= c_lvn; end
    // ---------------------------------------------------------------- SC store (dsdv_gunit_l1f, unchanged)
    wire [NW*64-1:0] aoh, boh;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_dec
            (* keep = 1 *) dsdv_l1f_dec64 u_da (.a(arc[6 * g +: 6]), .y(aoh[64 * g +: 64]));
            (* keep = 1 *) dsdv_l1f_dec64 u_db (.a(brc[6 * g +: 6]), .y(boh[64 * g +: 64]));
        end
    endgenerate
    reg  [NS*32-1:0] sc;
    wire [4*NS-1:0]  wh;
    wire [NS*32-1:0] wdv;
    wire [4*NL-1:0]  whf;
    wire [NL*32-1:0] wdf;
    generate
        for (g = 0; g < NS; g = g + 1) begin : g_e
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [7:0] en, hit, enf, hitf; wire [127:0] dd, ddf;
                for (t = 0; t < 4; t = t + 1) begin : g_t
                    localparam integer IX = 64 * (g / 16) + 16 * t + (g % 16), WJ = IX % 7, RJ = IX / 7;
                    localparam integer CW = g / 14, CD = g / 28;
`ifdef OT_S81_GUNIT_FWDOWN
                    localparam integer FW=8+((g<NL)?g:0), FD=4+((g<NL)?g/4:0);
`else
                    localparam integer FW=NW-1, FD=ND-1;
`endif
                    assign en[2 * t]      = wqc[14 * CW + WJ];      assign en[2 * t + 1]  = wqc[14 * CW + 7 + WJ];
                    assign hit[2 * t]     = aoh[64 * CW + RJ];      assign hit[2 * t + 1] = boh[64 * CW + RJ];
                    assign dd[32 * t +: 16]      = adc[224 * CD + 32 * WJ + 16 * h +: 16];
                    assign dd[32 * t + 16 +: 16] = bdc[224 * CD + 32 * WJ + 16 * h +: 16];
                    assign enf[2 * t]     = wqc[14 * FW + WJ];      assign enf[2 * t + 1] = wqc[14 * FW + 7 + WJ];
                    assign hitf[2 * t]    = aoh[64 * FW + RJ];      assign hitf[2 * t + 1] = boh[64 * FW + RJ];
                    assign ddf[32 * t +: 16]      = adc[224 * FD + 32 * WJ + 16 * h +: 16];
                    assign ddf[32 * t + 16 +: 16] = bdc[224 * FD + 32 * WJ + 16 * h +: 16];
                end
                (* keep = 1 *) dsdv_l1f_wdec8 u_w (.en(en), .hit(hit), .d(dd), .wh(wh[4 * g + 2 * h +: 2]), .wd(wdv[32 * g + 16 * h +: 16]));
                always @(posedge clk) begin
                    if (wh[4 * g + 2 * h])     sc[32 * g + 16 * h +: 8]     <= wdv[32 * g + 16 * h +: 8];
                    if (wh[4 * g + 2 * h + 1]) sc[32 * g + 16 * h + 8 +: 8] <= wdv[32 * g + 16 * h + 8 +: 8];
                end
                if (g < NL) begin : g_f
                    (* keep = 1 *) dsdv_l1f_wdec8 u_f (.en(enf), .hit(hitf), .d(ddf), .wh(whf[4 * g + 2 * h +: 2]),
                                                       .wd(wdf[32 * g + 16 * h +: 16]));
                end
            end
        end
    endgenerate
    wire [NB*7-1:0] cbh;
    generate
        for (g = 0; g < NB; g = g + 1) begin : g_bd
            (* keep = 1 *) dsdv_l1f_dec7 u_d (.a(cbc[3 * g +: 3]), .y(cbh[7 * g +: 7]));
        end
    endgenerate
    reg [NL*32-1:0] rdb;
    always @(*) begin
        rdb = {NL*32{1'b0}};
        for (i = 0; i < NL * 32; i = i + 1)
            for (j = 0; j < 7; j = j + 1)
                if (cbh[7 * (i / 16) + j]) rdb[i] = rdb[i] | sc[32 * NL * j + i];
    end
    wire [NL*32-1:0] svn;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_fw
            for (h = 0; h < 4; h = h + 1) begin : g_y
                (* keep = 1 *) dsdv_l1f_mux8 u_m (.s(cfwc[2 * (h / 2) + l / 8] && whf[4 * l + h]), .a(wdf[32 * l + 8 * h +: 8]),
                                                  .b(rdb[32 * l + 8 * h +: 8]), .y(svn[32 * l + 8 * h +: 8]));
            end
        end
    endgenerate
    // F2: the shared {s_bn, s_l, s_f, s_v} flops become two kept copies, one at each seam face (were one flop driving an S
    // AND an N pin 173 um apart: ctl_lo[4] reg->out -153 ps SS in the l1fb_f gate); same next value, same edge.
    reg s_v, s_f, s_l; reg [2:0] s_bn; reg [NL-1:0] s_lv; reg [NL*32-1:0] s_val;
    (* keep *) reg s_vh, s_fh, s_lh; (* keep *) reg [2:0] s_bnh;
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin s_v <= 1'b0; s_vh <= 1'b0; end else begin s_v <= cgo; s_vh <= cgo; end
    always @(posedge clk) begin
        s_f <= cfwc[0]; s_l <= cl; s_bn <= cbc[2:0];
        s_fh <= cfwc[1]; s_lh <= cl; s_bnh <= cbc[5:3];
        for (k = 0; k < NL; k = k + 1) begin
            s_lv[k] <= k < clv;
            for (j = 0; j < 4; j = j + 1) s_val[32 * k + 8 * j +: 8] <= svn[32 * k + 8 * j +: 8];
        end
    end
    assign sv_lo = s_val[255:0];  assign sv_hi = s_val[511:256];
    assign ctl_lo = {s_lv[7:0], s_bn, s_l, s_f, s_v};
    assign ctl_hi = {s_lv[15:8], s_bnh, s_lh, s_fh, s_vh};
    // ---------------------------------------------------------------- merge (fold of both sorts -> m1 -> cx8_2)
    wire [LW-1:0] c1, c3;
    // F2 seam landing (STW-S81e-FP 10-23): every A-band input lands in a face pin flop before the fold (was: A sort flop ->
    // seam -> 14 levels of fold compare -> m1, -615 ps SS / 1,398 unregistered pins).  +1 edge on the merge path only
    // (o_v / o_f / o_l / o_flt and the merge words of o_d); the gather path is unchanged and follows by causality (l1c
    // issues g_go from the lists it receives).  Booked for MU.S81.CAL (router select +1 edge).
    (* keep *) reg [LW-1:0] s0a_q, s0b_q, s1a_q, s1b_q;
    (* keep *) reg [2:0] sf0_q; (* keep *) reg [23:0] vfl_q, vfh_q;
    always @(posedge clk) begin s0a_q <= s0a; s0b_q <= s0b; s1a_q <= s1a; s1b_q <= s1b; end
    always @(posedge clk or negedge rq[12])
        if (!rq[12]) begin sf0_q <= 3'd0; vfl_q <= 24'd0; vfh_q <= 24'd0; end
        else begin sf0_q <= sf0; vfl_q <= vf_lo; vfh_q <= vf_hi; end
    dsdv_seln_fold_cx #(.EW(EW)) u_m0 (.aa(s0a_q), .ab(s0b_q), .ba(s1a_q), .bb(s1b_q), .q(c1));
    (* keep *) reg [LW-1:0] m1a, m1b; reg [2:0] mf;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) mf <= 3'd0; else mf <= sf0_q;
    always @(posedge clk) begin m1a <= c1; m1b <= c1; end
    dsdv_seln_cx8_2 #(.EW(EW), .J1(2), .KB1(8), .J2(1), .KB2(8)) u_m1 (.da(m1a), .db(m1b), .q(c3));
    // ---------------------------------------------------------------- gather + outputs (dsdv_gunit_l1f, unchanged)
    reg [6*NS-1:0] hs;
    (* keep *) reg [NQ-1:0] gq2;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) gq2 <= {NQ{1'b0}}; else gq2 <= {NQ{gq}};
    always @(posedge clk)
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                hs[NS * j + i] <= ghc[6 * (i / 28) + j] && {gac[42 * (i / 28) + 7 * j + 4 +: 3], gac[42 * (i / 28) + 7 * j +: 4]} == 7'(i);
    reg [191:0] gd;
    always @(*) begin
        gd = 192'd0;
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                if (hs[NS * j + i]) gd[32 * j +: 32] = gd[32 * j +: 32] | sc[32 * i +: 32];
    end
    // adder faults: ot_s81sl_ve_qadd's fault = valid_out && err != 0, formed here from the A bands' raw flops
    wire [NL-1:0] yf;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_yf
            wire [2:0] x;
            if (l < 8) begin : g_lo assign x = vfl_q[3 * l +: 3]; end
            else begin : g_hi assign x = vfh_q[3 * (l - 8) +: 3]; end
            assign yf[l] = x[0] && (x[2:1] != 2'd0);
        end
    endgenerate
    always @(posedge clk or negedge rq[12])
        if (!rq[12]) begin o_v <= 1'b0; o_f <= 1'b0; o_l <= 1'b0; o_g <= 1'b0; o_flt <= 1'b0; end
        else begin
            o_v <= mf[0]; o_f <= mf[1]; o_l <= mf[2]; o_g <= gq2[NQ - 1];
            if (|yf || (gq2[NQ - 1] && mf[0])) o_flt <= 1'b1;
        end
    wire [245:0] onext = {54'd0, gd};
    always @(posedge clk)
        for (i = 0; i < 246; i = i + 1) o_d[i] <= gq2[i / 14] ? onext[i] : c3[i];
endmodule

module dsdv_gunit_l1f_bp2 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    sa_r, input wire [223:0] sa_d, input wire [5:0] sb_r, input wire [223:0] sb_d,
    input  wire [13:0]   we,
    input  wire          c_go, input wire c_fw, input wire c_l, input wire [2:0] c_bn, input wire [4:0] c_lvn,
    input  wire          re, input wire [3:0] ra,
    input  wire [1:0]    bw_e, input wire [3:0] bw_a, input wire [255:0] bw_d,
    input  wire          g_go, input wire [5:0] g_hit, input wire [41:0] g_a,
    output wire          o_v, output wire o_f, output wire o_l, output wire o_g, output wire [245:0] o_d,
    output wire          o_flt
);
    wire [255:0] sv_lo, sv_hi;
    wire [13:0]  ctl_lo, ctl_hi;
    wire [327:0] s0a, s0b, s1a, s1b;
    wire [2:0]   sf0;
    wire [23:0]  vf_lo, vf_hi;
    dsdv_gunit_l1f_ba0 #(.MUT(MUT)) u_alo (.clk(clk), .rst_n(rst_n), .re(re), .ra(ra), .bw_e(bw_e[0]), .bw_a(bw_a),
        .bw_d(bw_d), .sv(sv_lo), .ctl(ctl_lo), .qa(s0a), .qb(s0b), .fo(sf0), .vf(vf_lo));
    dsdv_gunit_l1f_bf2 u_f (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d), .we(we),
        .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn), .g_go(g_go), .g_hit(g_hit), .g_a(g_a),
        .sv_lo(sv_lo), .sv_hi(sv_hi), .ctl_lo(ctl_lo), .ctl_hi(ctl_hi), .s0a(s0a), .s0b(s0b), .sf0(sf0), .vf_lo(vf_lo),
        .s1a(s1a), .s1b(s1b), .vf_hi(vf_hi), .o_v(o_v), .o_f(o_f), .o_l(o_l), .o_g(o_g), .o_d(o_d), .o_flt(o_flt));
    dsdv_gunit_l1f_ba1 #(.MUT(MUT)) u_ahi (.clk(clk), .rst_n(rst_n), .re(re), .ra(ra), .bw_e(bw_e[1]), .bw_a(bw_a),
        .bw_d(bw_d), .sv(sv_hi), .ctl(ctl_hi), .qa(s1a), .qb(s1b), .vf(vf_hi));
endmodule
