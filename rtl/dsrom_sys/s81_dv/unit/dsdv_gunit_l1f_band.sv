`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81c-TOK4-BAND (10-22, tree S81.STA.PAR.3): the BANDED gunit l1f -- clock-rule successor of dsdv_gunit_l1f_m
// (25,954 sinks on ONE clk over 475 x 389 um: TT spread 162 ps).  The front is cut at existing registers into three
// hard row bands, each its own small tree, under a single-root wires-only parent (< 0.6 mm: no landing, the crossings
// are plain flop-to-flop hops, ZERO latency change; cut analysis results/arch/s81_band_1022/cut_analysis.json):
//   A_lo  dsdv_gunit_l1f_ba0  lanes 0..7: bias macro 0 + its pin flops, s_bias, 8 adders, keys, sort8 #0 (+ its flags)
//   F     dsdv_gunit_l1f_bf   W input flops, SC store + write decode, beat read / forward -> s_val, select control,
//                             gather (hit decode + store read), merge (fold -> m1 -> cx8_2) and every E output
//   A_hi  dsdv_gunit_l1f_ba1  lanes 8..15: bias macro 1, adders, keys, sort8 #1
// dsdv_gunit_l1f_bp = the wires-only flat parent, same ports / parameters as dsdv_gunit_l1f, cycle-exact to it
// (tb_dsdv_gunit_l1f_band: every output, every edge).  Every band input lands in a flop or a macro pin; every band
// output leaves a flop (the adders' raw valid / error flops instead of the old vo && err AND).
// ---------------------------------------------------------------------------------------------------------------------

// ===================================================================================================================== A
module dsdv_gunit_l1f_acore #(
    parameter integer LH = 0,           // lane half: lanes 8 LH .. 8 LH + 7, bias macro LH
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          re, input wire [3:0] ra,                        // bias read {set, beat}, one beat ahead
    input  wire          bw_e, input wire [3:0] bw_a, input wire [255:0] bw_d,   // this macro's write enable
    input  wire [255:0]  sv,            // F's s_val, lanes 8 LH ..
    input  wire [13:0]   ctl,           // F's {s_lv[own 8], s_bn, s_l, s_f, s_v}
    output wire [327:0]  qa, output wire [327:0] qb, output wire [2:0] fo,  // sort8 result + flags
    output wire [23:0]   vf             // per lane {err[1:0], valid_out} of the adder (F forms the fault)
);
    localparam integer EW = 41, LW = 8 * EW, NL = 8, LA = 5;
`ifdef OT_S81_GUNIT_FWDOWN
    localparam integer NR = 21;
`else
    localparam integer NR = 13;
`endif
    integer k, j;
    genvar l;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // bias macro LH + its pin flops (dsdv_gunit_l1f: rdq / bwe reset rq[5], rad / bwa / bwd data)
    reg rdq, bwe; reg [3:0] rad, bwa; reg [255:0] bwd;
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin rdq <= 1'b0; bwe <= 1'b0; end else begin rdq <= re; bwe <= bw_e; end
    always @(posedge clk) begin rad <= ra; bwa <= bw_a; bwd <= bw_d; end
    wire [255:0] rd;
    ot_sram_1r1w_128x256_m1_r2c2 u_b (.clk(clk), .r_ce_in(rdq), .r_addr_in({3'b000, rad}), .rd_out(rd),
        .w_ce_in(bwe), .w_addr_in({3'b000, bwa}), .wd_in(bwd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg [NL*32-1:0] s_bias;
    always @(posedge clk) for (k = 0; k < NL; k = k + 1) s_bias[32 * k +: 32] <= (MUT == 1) ? 32'd0 : rd[32 * k +: 32];
    wire       s_v = ctl[0], s_f = ctl[1], s_l = ctl[2];
    wire [2:0] s_bn = ctl[5:3];
    wire [NL-1:0] s_lv = ctl[13:6];
    // 8 adds: operand register + LAT-4 ve adder = 5 (ot_s81sl_ve_qadd's adder, valid / error flops leave raw)
    wire [NL*32-1:0] y, y2;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_add
            localparam integer GL = 8 * LH + l;                       // the lane of dsdv_gunit_l1f
            reg pv;
            (* keep *) reg [31:0] pa, pa2, pb, pb2;
            always @(posedge clk or negedge rq[6 + GL / 4])
                if (!rq[6 + GL / 4]) pv <= 1'b0; else pv <= s_v && s_lv[l];
            always @(posedge clk) begin
                pa <= sv[32 * l +: 32]; pa2 <= sv[32 * l +: 32];
                pb <= s_bias[32 * l +: 32]; pb2 <= s_bias[32 * l +: 32];
            end
            wire vo; wire [1:0] er;
            ot_s81sl_ve_fadd u (.clk(clk), .rst_n(rq[6 + GL / 4]), .valid_in(pv), .a(pa), .a2(pa2), .b(pb), .b2(pb2),
                                .y(y[32 * l +: 32]), .y2(y2[32 * l +: 32]), .err(er), .valid_out(vo));
            assign vf[3 * l +: 3] = {er, vo};
        end
    endgenerate
    // select control delay lines (dsdv_gunit_l1f dv / dd / dl2, this half's lane valids)
    reg [LA*3-1:0] dv; reg [LA*(NL+3+2)-1:0] dd; (* keep *) reg [LA*NL-1:0] dl2;
    always @(posedge clk or negedge rq[10])
        if (!rq[10]) dv <= {LA*3{1'b0}}; else dv <= {dv[3*(LA-1)-1:0], s_l, s_f, s_v};
    always @(posedge clk) begin dd <= {dd[(NL+5)*(LA-1)-1:0], s_bn, s_lv, 2'b00}; dl2 <= {dl2[NL*(LA-1)-1:0], s_lv}; end
    wire [2:0] a_fl = dv[3*(LA-1) +: 3];
    wire [NL+4:0] a_dd = dd[(NL+5)*(LA-1) +: NL+5];
    wire [2:0] a_bn = a_dd[NL+4:NL+2]; wire [NL-1:0] a_lv = a_dd[NL+1:2];
    wire [NL-1:0] a_lv2 = dl2[NL*(LA-1) +: NL];
    // key register (ot_hdc_select's key map), copies A / B
    (* keep *) reg [NL*EW-1:0] kda, kdb;
    reg [2:0] kf;
    always @(posedge clk or negedge rq[10]) if (!rq[10]) kf <= 3'd0; else kf <= a_fl;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_key
            wire [31:0] v    = y[32 * l +: 32];
            wire [31:0] v2   = y2[32 * l +: 32];
            wire        zlo  = (v[30:0] == 31'd0);
            wire        zhi  = (v2[30:0] == 31'd0);
            wire [15:0] klo  = zlo ? 16'h0000 : v[31] ? ~v[15:0] : v[15:0];
            wire [15:0] khi  = zhi ? 16'h8000 : v2[31] ? ~v2[31:16] : {1'b1, v2[30:16]};
            wire        ninf = (v2 == 32'hFF80_0000);
            wire [3:0]  lk   = 8 * LH + l;
            wire [EW-1:0] rec = {1'b1, khi, klo, ~{a_bn, lk}, ninf};
            wire [EW-1:0] mrec = {a_lv2[l] ? rec[40:20] : 21'd0, a_lv[l] ? rec[19:0] : 20'd0};
            always @(posedge clk) begin kda[EW * l +: EW] <= mrec; kdb[EW * l +: EW] <= mrec; end
        end
    endgenerate
    dsdv_seln_sort8 #(.EW(EW), .FW(3)) u_s (.clk(clk), .rst_n(rq[11]), .fi(kf), .da(kda), .db(kdb), .fo(fo), .qa(qa), .qb(qb));
endmodule

module dsdv_gunit_l1f_ba0 #(parameter integer MUT = 0) (
    input  wire clk, input wire rst_n, input wire re, input wire [3:0] ra, input wire bw_e, input wire [3:0] bw_a,
    input  wire [255:0] bw_d, input wire [255:0] sv, input wire [13:0] ctl,
    output wire [327:0] qa, output wire [327:0] qb, output wire [2:0] fo, output wire [23:0] vf);
    dsdv_gunit_l1f_acore #(.LH(0), .MUT(MUT)) u_a (.clk(clk), .rst_n(rst_n), .re(re), .ra(ra), .bw_e(bw_e), .bw_a(bw_a),
        .bw_d(bw_d), .sv(sv), .ctl(ctl), .qa(qa), .qb(qb), .fo(fo), .vf(vf));
endmodule

module dsdv_gunit_l1f_ba1 #(parameter integer MUT = 0) (     // sort #1's flags are unused (dsdv_gunit_l1f: mf <= sf0)
    input  wire clk, input wire rst_n, input wire re, input wire [3:0] ra, input wire bw_e, input wire [3:0] bw_a,
    input  wire [255:0] bw_d, input wire [255:0] sv, input wire [13:0] ctl,
    output wire [327:0] qa, output wire [327:0] qb, output wire [23:0] vf);
    wire [2:0] fo_unused;
    dsdv_gunit_l1f_acore #(.LH(1), .MUT(MUT)) u_a (.clk(clk), .rst_n(rst_n), .re(re), .ra(ra), .bw_e(bw_e), .bw_a(bw_a),
        .bw_d(bw_d), .sv(sv), .ctl(ctl), .qa(qa), .qb(qb), .fo(fo_unused), .vf(vf));
endmodule

// ===================================================================================================================== F
module dsdv_gunit_l1f_bf (
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
    reg s_v, s_f, s_l; reg [2:0] s_bn; reg [NL-1:0] s_lv; reg [NL*32-1:0] s_val;
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) s_v <= 1'b0; else s_v <= cgo;
    always @(posedge clk) begin
        s_f <= cfwc[0]; s_l <= cl; s_bn <= cbc[2:0];
        for (k = 0; k < NL; k = k + 1) begin
            s_lv[k] <= k < clv;
            for (j = 0; j < 4; j = j + 1) s_val[32 * k + 8 * j +: 8] <= svn[32 * k + 8 * j +: 8];
        end
    end
    assign sv_lo = s_val[255:0];  assign sv_hi = s_val[511:256];
    assign ctl_lo = {s_lv[7:0], s_bn, s_l, s_f, s_v};
    assign ctl_hi = {s_lv[15:8], s_bn, s_l, s_f, s_v};
    // ---------------------------------------------------------------- merge (fold of both sorts -> m1 -> cx8_2)
    wire [LW-1:0] c1, c3;
    dsdv_seln_fold_cx #(.EW(EW)) u_m0 (.aa(s0a), .ab(s0b), .ba(s1a), .bb(s1b), .q(c1));
    (* keep *) reg [LW-1:0] m1a, m1b; reg [2:0] mf;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) mf <= 3'd0; else mf <= sf0;
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
            if (l < 8) begin : g_lo assign x = vf_lo[3 * l +: 3]; end
            else begin : g_hi assign x = vf_hi[3 * (l - 8) +: 3]; end
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

// ============================================================================ flat parent (wires only)
module dsdv_gunit_l1f_bp #(
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
    dsdv_gunit_l1f_bf u_f (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d), .we(we),
        .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn), .g_go(g_go), .g_hit(g_hit), .g_a(g_a),
        .sv_lo(sv_lo), .sv_hi(sv_hi), .ctl_lo(ctl_lo), .ctl_hi(ctl_hi), .s0a(s0a), .s0b(s0b), .sf0(sf0), .vf_lo(vf_lo),
        .s1a(s1a), .s1b(s1b), .vf_hi(vf_hi), .o_v(o_v), .o_f(o_f), .o_l(o_l), .o_g(o_g), .o_d(o_d), .o_flt(o_flt));
    dsdv_gunit_l1f_ba1 #(.MUT(MUT)) u_ahi (.clk(clk), .rst_n(rst_n), .re(re), .ra(ra), .bw_e(bw_e[1]), .bw_a(bw_a),
        .bw_d(bw_d), .sv(sv_hi), .ctl(ctl_hi), .qa(s1a), .qb(s1b), .vf(vf_hi));
endmodule
