`timescale 1ns/1ps
// ot_v41_bf16_half (DIE-S81-51/RF-H 3-core bf_col, 2026-11-03): one half (8 lanes) of ot_v41_bf16_lanes3 as its own hard
// core.  Lanes 0..7 of the half are lanes 8*h + 0..7 of lanes3, with the same lane tiles, multipliers (RNECUT: the RNE
// encode cut, XS 2), chunk chains and the first three levels of the pairwise tree; the root (fourth) level adds the
// two halves' sums in ot_v41_bf_col3_c.  Faces:
//   * clk is the column clock (own core clock entry); rst_c = the column's r_rst face copy (g_pin.r_rst_a/b: same function,
//     same edges); ze_c = out-face flop after the column's r_ze (g_pin.r_ze_a/b), captured once here (u_ze_f): the half's
//     tile clocks follow the column tiles' by +2 edges (RF-H r2, see below), its resets release on the column reset's edge;
//   * v / w / x / t are registered on the column side (ot_v41_bf_col3_c, = lanes3 XST stage 1) and again here
//     (u_fiv / u_fi, = lanes3 XST stage 2): lanes3 XST = 2 with the two relay stages on the two core faces;
//   * every output is registered here (u_fov / u_fo) and again on the column side: +2 cycles on the BF sums.
module ot_v41_bf16_half #(
    parameter integer NCHB = 8,
    parameter integer GRADUAL_RNE = 0,
    parameter integer TRW = 2,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer RC = 0,
    parameter integer TNODE = 0,
    parameter integer RNECUT = 0
) (
    input  wire              clk,
    input  wire              rst_c,            // = ot_v41_bf_col g_pin.r_rst (registered in the column core)
    input  wire              ze_c,             // = ot_v41_bf_col g_pin.r_ze
    input  wire              v,
    input  wire [127:0]      w,
    input  wire [127:0]      x,
    input  wire [$clog2(NCHB)+TRW+3-1:0] t,   // {slot, first, last, tree, final}
    output wire              ov,
    output wire [31:0]       oval,
    output wire              oerr,
    output wire [TRW:0]      otag,             // {tree, final}
    output wire              fault
);
    localparam integer HW = $clog2(NCHB);
    localparam integer TW = HW + 2 + TRW + 1;
    wire b_rst = rst_c;                // = ot_v41_bf_col g_pin.r_rst (HDLY 0)
    // RF-H r2 (FACE_GUARD: one capture flop per input pin): ze_c lands in ONE in-face flop u_ze_f, which feeds every
    // tile's local enable copy.  With the column out-face r_ze_a/b that is +2 edges on the halves' gate enable vs the
    // column tiles (open and close); the BF words reach the halves later than that (tb_col3 free=0: ze_d rises with the
    // first issue, latency still exactly +3), and the column's drain window covers the later close.
    wire b_ze;
`ifdef RFH3_MUTANT_ZE
    // negative control: the halves' gate enable arrives RFH3_MUTANT_ZE edges later (first words hit a closed gate)
    reg [`RFH3_MUTANT_ZE-1:0] ze_mut;
    always @(posedge clk or negedge rst_c) if (!rst_c) ze_mut <= '1; else ze_mut <= {ze_mut, ze_c};
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b1)) u_ze_f (.clk(clk), .arst_n(rst_c), .d(ze_mut[`RFH3_MUTANT_ZE-1]), .q(b_ze));
`else
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b1)) u_ze_f (.clk(clk), .arst_n(rst_c), .d(ze_c), .q(b_ze));
`endif
    wire fclk = clk, rst_pin = b_rst, ze_dd = b_ze;
    wire tclk, rst_n;
    ot_v41_tile_clk u_tt (.fclk(fclk), .rst_pin(rst_pin), .ze_d(ze_dd), .gclk(tclk), .rst_n(rst_n));
    wire clk_t = tclk;
    wire          v_s;
    wire [127:0]  w_s, x_s;
    wire [TW-1:0] t_s;
`ifdef RFH3_MUTANT_FACE
    // negative control: the input face drops the valid of slot 1
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_fiv (.clk(tclk), .arst_n(rst_n), .d(v && t[TW-1 -: HW] != 1), .q(v_s));
`else
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_fiv (.clk(tclk), .arst_n(rst_n), .d(v), .q(v_s));
`endif
    ot_v41_kreg #(.W(256 + TW)) u_fi (.clk(tclk), .arst_n(1'b1), .d({w, x, t}), .q({w_s, x_s, t_s}));
    localparam integer PL = RC != 0 ? (RNECUT != 0 ? 9 : 8) : 5;
    localparam [8:0] CUTT = RC != 0 ? 9'b1_1111_1111 : CUT;
    localparam integer LATT = 1 + CUTT[0] + CUTT[1] + CUTT[2] + CUTT[3] + CUTT[4] + CUTT[5] + CUTT[6] + CUTT[7] + CUTT[8];
    reg [TW-1:0] t_r;
    always @(posedge clk_t) t_r <= t_s;
    wire [TW-1:0] t_in = t_r;
    wire [TW-1:0] t_p;
    ot_hdc_delay #(.W(TW), .D(PL)) u_pt (.clk(clk_t), .rst_n(rst_n), .d(t_in), .q(t_p));
    wire [8*TW-1:0] t_local;
    assign t_local = {8{t_p}};
    wire [7:0] pv;
    wire [7:0] pf;
    wire [31:0] prod [0:7];
    wire [7:0] cv, cf, cfault;
    wire [31:0] cs [0:7];
    wire [TRW:0] ct [0:7];
    genvar l;
    generate for (l = 0; l < 8; l = l + 1) begin : g_l
        wire [TW-1:0] lane_tag = t_local[TW*l +: TW];
        // lane tile: local gated clock lclk / reset lrst; the lane's own boundary registers (16-bit word and x slices,
        // valid copy) are the lane's local operand registers
        wire lclk, lrst;
`ifdef TCG_MUTANT_EN
        // negative control: lane 3's tile enable copy loads the wrong function (go-only), so lane 3 misses edges
        ot_v41_tile_clk u_tl (.fclk(fclk), .rst_pin(rst_pin), .ze_d(l == 3 ? 1'b0 : ze_dd), .gclk(lclk), .rst_n(lrst));
`else
        ot_v41_tile_clk u_tl (.fclk(fclk), .rst_pin(rst_pin), .ze_d(ze_dd), .gclk(lclk), .rst_n(lrst));
`endif
        reg [15:0] w_r, x_r;
        reg        v_r;
        always @(posedge lclk or negedge lrst) if (!lrst) v_r <= 1'b0; else v_r <= v_s;
        always @(posedge lclk) begin w_r <= w_s[16*l +: 16]; x_r <= x_s[16*l +: 16]; end
        ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(GRADUAL_RNE), .XS(RC != 0 ? (RNECUT != 0 ? 2 : 1) : 0)) u_m (.clk(lclk), .rst_n(lrst), .v(v_r), .a({w_r, 16'd0}), .b({x_r, 16'd0}),
                         .y(prod[l]), .fault(pf[l]));
        reg [PL-1:0] vp;
        always @(posedge lclk or negedge lrst) if (!lrst) vp <= '0; else vp <= {vp[PL-2:0], v_r};
        assign pv[l] = vp[PL-1];
        if (RC >= 2) begin : g_cu
        ot_v41_chain2u2 #(.NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(lclk), .rst_n(lrst), .v(pv[l]),
            .slot(lane_tag[TW-1 -: HW]), .first(lane_tag[TRW+2]), .last(lane_tag[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(lane_tag[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else if (RC != 0) begin : g_c4
        ot_v41_chain4 #(.PD(1), .ND(4), .NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(lclk), .rst_n(lrst), .v(pv[l]),
            .slot(lane_tag[TW-1 -: HW]), .first(lane_tag[TRW+2]), .last(lane_tag[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(lane_tag[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else begin : g_c2
        ot_v41_chain2 #(.NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(lclk), .rst_n(lrst), .v(pv[l]),
            .slot(lane_tag[TW-1 -: HW]), .first(lane_tag[TRW+2]), .last(lane_tag[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(lane_tag[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end
    end endgenerate
    // 3-level pairwise tree over this half's 8 chunk sums (all lanes emit in the same cycle)
    wire [31:0] lvv [0:3][0:7];
    wire [7:0] lve [0:3];
    wire [3:0] lvvld;
    wire [TRW:0] lvt [0:3];
    generate for (l = 0; l < 8; l = l + 1) begin : g_in
        assign lvv[0][l] = cs[l];
        assign lve[0][l] = cf[l];
    end endgenerate
    assign lvvld[0] = cv[0];
    assign lvt[0] = ct[0];
    genvar lv, k;
    generate for (lv = 0; lv < 3; lv = lv + 1) begin : g_lv
        localparam integer NN = 8 >> (lv + 1);
        for (k = 0; k < NN; k = k + 1) begin : g_n
            wire [1:0] e;
            wire vo;
            wire nclk;
            if (TNODE != 0) begin : g_tn
                wire nrst_unused;
                ot_v41_tile_clk u_tn (.fclk(fclk), .rst_pin(rst_pin), .ze_d(ze_dd), .gclk(nclk), .rst_n(nrst_unused));
            end else begin : g_ntn
                assign nclk = clk_t;
            end
            ot_v41_fadd #(.CUT(CUTT)) u_a (.clk(nclk), .rst_n(rst_n), .valid_in(lvvld[lv]), .a(lvv[lv][2*k]),
                                          .b(lvv[lv][2*k+1]), .y(lvv[lv+1][k]), .err(e), .valid_out(vo));
            reg [LATT-1:0] ep;
            always @(posedge nclk) ep <= {ep[LATT-2:0], lve[lv][2*k] | lve[lv][2*k+1]};
            assign lve[lv+1][k] = ep[LATT-1] | (e != 2'd0);
        end
        for (k = NN; k < 8; k = k + 1) begin : g_z
            assign lvv[lv+1][k] = 32'd0;
            assign lve[lv+1][k] = 1'b0;
        end
        reg [LATT-1:0] vp;
        always @(posedge clk_t or negedge rst_n) if (!rst_n) vp <= '0; else vp <= {vp[LATT-2:0], lvvld[lv]};
        assign lvvld[lv+1] = vp[LATT-1];
        ot_hdc_delay #(.W(TRW + 1), .D(LATT)) u_t (.clk(clk_t), .rst_n(rst_n), .d(lvt[lv]), .q(lvt[lv+1]));
    end endgenerate
    // output face
    ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_fov (.clk(tclk), .arst_n(rst_n), .d({lvvld[3], |cfault}), .q({ov, fault}));
    ot_v41_kreg #(.W(33 + TRW + 1)) u_fo (.clk(tclk), .arst_n(1'b1), .d({lvv[3][0], lve[3][0], lvt[3]}), .q({oval, oerr, otag}));
endmodule
