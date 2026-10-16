`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bf16_lanes3 (bf-arch 2026-10-09): ot_v41_bf16_lanes2 (ot_v41_bf16_lanes2_rne_prepare.sv, same arithmetic, same
// stages, same latency) split into clock / reset TILES: each of the 16 lanes (its slice of the boundary word / x
// registers, its valid copy, its multiplier and its chunk chain) and the tag line + pairwise tree are separate tiles
// (ot_v41_tile_clk), each with its own local gate-enable copy, integrated clock gate and reset synchroniser copy.  The
// copies are the element's ze / reset synchroniser functions of the same inputs, so every register sees exactly the
// edges and the reset release it saw on the element's single gated clock (exact by construction).  Used only by
// ot_v41_rom_elem_qx_w10 TCG = 1 (opt-in); ot_v41_bf16_lanes2 is unchanged.
// Why (route bfp_pinclk_a_hm0_7fc782879-cl, TT): every setup miss was (1) reset recovery from ONE reset synchroniser
// copy per macro across ~25k lane flops (-42.1 ps, an 830 ps buffered reset net) and (2) the element's ONE root-level
// gate's enable (-31.8 ps); the FF hold misses inside the lanes (-4..-10 ps, ~1,800 endpoints) are leaf skew between
// back-to-back cut registers on a 1000 um gated tree.  Tiles give each lane a small local gated tree and reset tree.
// ---------------------------------------------------------------------------
module ot_v41_bf16_lanes3 #(
    parameter integer NCHB = 8,
    parameter integer GRADUAL_RNE = 0, // shared reviewed multiplier; no stage/port change
    parameter integer TRW = 2,         // tree-id width
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    // RC (BF rowfix re-cut A, 2026-10-07; default 0 = unchanged): bit-identical, +3 product cycles and +2 cycles per
    // tree level (lane latency +11): the product is ot_v41_bmul2_rne_prepare XS = 1 (8 stages); the chunk chains are
    // ot_v41_chain4 (PD = 1, ND = 4 kept forward-select copies: the routed BF HITFIX GRT SS worst -256 ps was one fwd5
    // register driving the operand mux of other lanes and the other macro, merged by synthesis); the 4-level pairwise
    // tree adders (feed-forward) use every stage cut (CUT 1_1111_1111).  The chains keep CUT (their LAT is the issue
    // side's slot-revisit rule).  RC = 2: as RC = 1 but the chunk chains are ot_v41_chain2u2 (unrolled by 2 on a
    // half-rate gated clock, bit-exact, +3 cycles; multicycle 2/1 SDC on their hs_* registers).
    parameter integer RC = 0,
    // XST (bf-arch, owner 2026-10-09: added cycles allowed): XST extra register stages on the lanes' inputs {v, word,
    // x slice, tag} before the lane tiles, a pipelined delivery of the capture word and the shared x slice to the 16
    // lanes (the placer spreads the stages along the wire as relays).  Every input is delayed by the same XST cycles:
    // values, per-lane order and the tree are unchanged, only the lanes' latency grows by XST (transaction level).
    parameter integer XST = 0
) (
    input  wire              fclk,     // free-running element clock
    input  wire              rst_pin,  // element reset pin
    input  wire              ze_d,     // element gate-enable next state (qx QZE ze_d)
    input  wire              v,
    input  wire [255:0]      w,        // 16 BF16 weights, lane l at [16l +: 16]
    input  wire [255:0]      x,        // 16 BF16 activations, lane l at [16l +: 16]
    input  wire [$clog2(NCHB)-1:0] slot,
    input  wire              first,
    input  wire              last,
    input  wire [TRW-1:0]    tree,
    input  wire              final_i,
    output wire              ov,
    output wire [31:0]       oval,
    output wire [TRW-1:0]    otree,
    output wire              ofinal,
    output wire              oerr,
    output wire              fault
);
    localparam integer HW = $clog2(NCHB);
    localparam integer TW = HW + 2 + TRW + 1;
    // 1.2 GHz: the word, x slice and tag are registered at the lanes' boundary (the element's capture mux and the
    // 16 lanes' fan-out are not in one cycle)
    // tree tile: the tag line, the 4-level pairwise tree and its delays
    wire clk, rst_n;
    ot_v41_tile_clk u_tt (.fclk(fclk), .rst_pin(rst_pin), .ze_d(ze_d), .gclk(clk), .rst_n(rst_n));
    // XST input relay stages (tree tile clock; only the valid is reset)
    wire          v_s;
    wire [255:0]  w_s, x_s;
    wire [TW-1:0] t_s;
    if (XST != 0) begin : g_xst
        reg [XST-1:0] sv;
        reg [255:0] sw [0:XST-1];
        reg [255:0] sx [0:XST-1];
        reg [TW-1:0] st [0:XST-1];
        always @(posedge clk or negedge rst_n) if (!rst_n) sv <= '0; else sv <= (XST > 1) ? {sv[XST-2:0], v} : v;
        always @(posedge clk) begin
            sw[0] <= w; sx[0] <= x; st[0] <= {slot, first, last, tree, final_i};
            for (int k = 1; k < XST; k++) begin sw[k] <= sw[k-1]; sx[k] <= sx[k-1]; st[k] <= st[k-1]; end
        end
`ifdef XST_MUTANT_TAG
        assign v_s = sv[XST-1]; assign w_s = sw[XST-1]; assign x_s = sx[XST-1]; assign t_s = (XST > 1) ? st[XST-2] : {slot, first, last, tree, final_i};  // negative control: tag one stage early
`else
        assign v_s = sv[XST-1]; assign w_s = sw[XST-1]; assign x_s = sx[XST-1]; assign t_s = st[XST-1];
`endif
    end else begin : g_nxst
        assign v_s = v; assign w_s = w; assign x_s = x; assign t_s = {slot, first, last, tree, final_i};
    end
    reg [TW-1:0] t_r;
    always @(posedge clk) t_r <= t_s;
    wire [TW-1:0] t_in = t_r;
    wire [TW-1:0] t_p;
    localparam integer PL = RC != 0 ? 8 : 5;                     // product latency
    localparam [8:0] CUTT = RC != 0 ? 9'b1_1111_1111 : CUT;    // tree adders
    localparam integer LATT = 1 + CUTT[0] + CUTT[1] + CUTT[2] + CUTT[3] + CUTT[4] + CUTT[5] + CUTT[6] + CUTT[7] + CUTT[8];
    ot_hdc_delay #(.W(TW), .D(PL)) u_pt (.clk(clk), .rst_n(rst_n), .d(t_in), .q(t_p));
    wire [15:0] pv;
    wire [15:0] pf;
    wire [31:0] prod [0:15];
    wire [15:0] cv, cf, cfault;
    wire [31:0] cs [0:15];
    wire [TRW:0] ct [0:15];
    genvar l;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l
        // lane tile: local gated clock lclk / reset lrst; the lane's own boundary registers (16-bit word and x slices,
        // valid copy) are the lane's local operand registers
        wire lclk, lrst;
`ifdef TCG_MUTANT_EN
        // negative control: lane 3's tile enable copy loads the wrong function (go-only), so lane 3 misses edges
        ot_v41_tile_clk u_tl (.fclk(fclk), .rst_pin(rst_pin), .ze_d(l == 3 ? 1'b0 : ze_d), .gclk(lclk), .rst_n(lrst));
`else
        ot_v41_tile_clk u_tl (.fclk(fclk), .rst_pin(rst_pin), .ze_d(ze_d), .gclk(lclk), .rst_n(lrst));
`endif
        reg [15:0] w_r, x_r;
        reg        v_r;
        always @(posedge lclk or negedge lrst) if (!lrst) v_r <= 1'b0; else v_r <= v_s;
        always @(posedge lclk) begin w_r <= w_s[16*l +: 16]; x_r <= x_s[16*l +: 16]; end
        ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(GRADUAL_RNE), .XS(RC != 0 ? 1 : 0)) u_m (.clk(lclk), .rst_n(lrst), .v(v_r), .a({w_r, 16'd0}), .b({x_r, 16'd0}),
                         .y(prod[l]), .fault(pf[l]));
        reg [PL-1:0] vp;
        always @(posedge lclk or negedge lrst) if (!lrst) vp <= '0; else vp <= {vp[PL-2:0], v_r};
        assign pv[l] = vp[PL-1];
        if (RC >= 2) begin : g_cu
        ot_v41_chain2u2 #(.NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(lclk), .rst_n(lrst), .v(pv[l]),
            .slot(t_p[TW-1 -: HW]), .first(t_p[TRW+2]), .last(t_p[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(t_p[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else if (RC != 0) begin : g_c4
        ot_v41_chain4 #(.PD(1), .ND(4), .NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(lclk), .rst_n(lrst), .v(pv[l]),
            .slot(t_p[TW-1 -: HW]), .first(t_p[TRW+2]), .last(t_p[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(t_p[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else begin : g_c2
        ot_v41_chain2 #(.NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(lclk), .rst_n(lrst), .v(pv[l]),
            .slot(t_p[TW-1 -: HW]), .first(t_p[TRW+2]), .last(t_p[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(t_p[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end
    end endgenerate
    // 4-level pairwise tree over the 16 chunk sums (all lanes emit in the same cycle)
    wire [31:0] lvv [0:4][0:15];
    wire [15:0] lve [0:4];
    wire [4:0] lvvld;
    wire [TRW:0] lvt [0:4];
    generate for (l = 0; l < 16; l = l + 1) begin : g_in
        assign lvv[0][l] = cs[l];
        assign lve[0][l] = cf[l];
    end endgenerate
    assign lvvld[0] = cv[0];
    assign lvt[0] = ct[0];
    genvar lv, k;
    generate for (lv = 0; lv < 4; lv = lv + 1) begin : g_lv
        localparam integer NN = 16 >> (lv + 1);
        for (k = 0; k < NN; k = k + 1) begin : g_n
            wire [1:0] e;
            wire vo;
            ot_v41_fadd #(.CUT(CUTT)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(lvvld[lv]), .a(lvv[lv][2*k]),
                                          .b(lvv[lv][2*k+1]), .y(lvv[lv+1][k]), .err(e), .valid_out(vo));
            reg [LATT-1:0] ep;
            always @(posedge clk) ep <= {ep[LATT-2:0], lve[lv][2*k] | lve[lv][2*k+1]};
            assign lve[lv+1][k] = ep[LATT-1] | (e != 2'd0);
        end
        for (k = NN; k < 16; k = k + 1) begin : g_z
            assign lvv[lv+1][k] = 32'd0;
            assign lve[lv+1][k] = 1'b0;
        end
        reg [LATT-1:0] vp;
        always @(posedge clk or negedge rst_n) if (!rst_n) vp <= '0; else vp <= {vp[LATT-2:0], lvvld[lv]};
        assign lvvld[lv+1] = vp[LATT-1];
        ot_hdc_delay #(.W(TRW + 1), .D(LATT)) u_t (.clk(clk), .rst_n(rst_n), .d(lvt[lv]), .q(lvt[lv+1]));
    end endgenerate
    assign ov = lvvld[4];
    assign oval = lvv[4][0];
    assign otree = lvt[4][TRW:1];
    assign ofinal = lvt[4][0];
    assign oerr = lve[4][0];
    assign fault = |cfault;
endmodule
