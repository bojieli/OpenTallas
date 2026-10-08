`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bf16_lanes3 (s81-bf deep full-rate BF, 2026-10-07, OPTIONAL lever): ot_v41_bf16_lanes2 (RC 0..2 unchanged in
// function) plus DEEP (see the parameter).  Golden order unchanged: each chunk chain sequential from +0, the 4-level
// pairwise tree; only latencies change.  The issuer must revisit a chain slot >= RDC cycles later.
// ---------------------------------------------------------------------------
// ot_v41_bf16_lanes2: ot_v41_bf16_lanes on the LAT-stage adders (chain2, fadd) for 1.2 GHz at SS (W10).
// ot_v41_bf16_lanes: the optional BF16 path of the V4.1 ROM-array element (W10; model: BF16 lanes on
// 2,048 of the busiest die's 13,798 macros).
//
// Golden mv / matvec_c under R-ARITH chunk8 (tools/hdc_golden_v41.py): products w * bf16(x) in binary32 (a
// BF16 x BF16 product is exact), each golden chunk of 8 consecutive products summed sequentially from +0,
// chunk sums combined by the padded pairwise tree.  A BF16 unit is a lane group of 16 consecutive golden
// chunks (128 elements); word b of a unit carries element b of each chunk (lane l <- chunk 16h + l), so
// each of the 16 lanes runs its own chunk chains (NCHB slots, one pipelined FP32 adder).  The 16 chunk sums
// of a unit complete in the same cycle and meet in a 15-adder, 4-level pairwise tree whose root is the
// golden level-4 node of that lane group; it leaves as one base node for the element's segment tree.
// Latency: product 5 (ot_v41_bmul2) + chain 5 + tree 20.
// The product is ot_v41_bmul2 (= W13b's ot_hdc_bmul SPLIT = 1): two 8x4 partial products in stage 2, a keep-prefix add in
// stage 3.  The single-stage 8x8 product was the column pair's SS endpoint (c1, ideal clock: u_m.s2_p[15], -154.7 ps,
// 848 ps of product logic).  Bit-identical (SPLIT 0 vs 1: 4,393,224 cycles, 0 mismatches) and latency unchanged.
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
    // DEEP (s81-bf deep full-rate BF, 2026-10-07, OPTIONAL; requires RC = 1): 1 = moderate, 2 = aggressive.  Product
    // ot_v41_bmul3_rne XS 2 (9 stages); one more input register rank
    // (routed g_mi -> w_r -182 ps); chunk chains ot_v41_chain5 with every adder step cut (CUT 1_1111_1111) and
    // F5 = 0 (DEEP 2: + SPLIT6 + SPLIT9); tree adders ot_v41_fadd3 CUT 1_1111_1111 + SPLIT6 (DEEP 2: + SPLIT9).
    // Chain latency LATC = 10 (DEEP 1) / 12 (DEEP 2); a slot must be revisited >= LATC + 1 cycles later (RDC).
    parameter integer DEEP = 0,
    parameter integer S6C = DEEP >= 2 ? 1 : 0,
    parameter integer S9C = DEEP >= 2 ? 1 : 0,
    parameter integer LATC = DEEP != 0 ? 10 + S6C + S9C : LAT,
    parameter integer RDC = DEEP != 0 ? LATC + 1 : LAT
) (
    input  wire              clk,
    input  wire              rst_n,
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
    reg [255:0] w_r0, x_r0;
    reg         v_r0;
    reg [TW-1:0] t_r0;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_r0 <= 1'b0; else v_r0 <= v;
    always @(posedge clk) begin w_r0 <= w; x_r0 <= x; t_r0 <= {slot, first, last, tree, final_i}; end
    wire [255:0] w_r, x_r;
    wire         v_r;
    wire [TW-1:0] t_r;
    if (DEEP != 0) begin : g_in2
        // second rank: the capture mux -> lanes wire gets a whole cycle (each word / x bit then drives one lane)
        reg [255:0] w_q, x_q;
        reg         v_q;
        always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= v_r0;
        always @(posedge clk) begin w_q <= w_r0; x_q <= x_r0; end
        reg [TW-1:0] t_q;
        always @(posedge clk) t_q <= t_r0;
        assign w_r = w_q; assign x_r = x_q; assign v_r = v_q; assign t_r = t_q;
    end else begin : g_in1
        assign w_r = w_r0; assign x_r = x_r0; assign v_r = v_r0; assign t_r = t_r0;
    end
    wire [TW-1:0] t_in = t_r;
    wire [TW-1:0] t_p;
    localparam integer PL = DEEP != 0 ? 9 : RC != 0 ? 8 : 5;                     // product latency
    localparam [8:0] CUTT = RC != 0 ? 9'b1_1111_1111 : CUT;
    localparam integer S6T = DEEP != 0 ? 1 : 0, S9T = DEEP >= 2 ? 1 : 0;    // tree adders
    localparam integer LATT = 1 + CUTT[0] + CUTT[1] + CUTT[2] + CUTT[3] + CUTT[4] + CUTT[5] + CUTT[6] + CUTT[7] + CUTT[8] + S6T + S9T;
    ot_hdc_delay #(.W(TW), .D(PL)) u_pt (.clk(clk), .rst_n(rst_n), .d(t_in), .q(t_p));
    wire [15:0] pv;
    wire [15:0] pf;
    wire [31:0] prod [0:15];
    wire [15:0] cv, cf, cfault;
    wire [31:0] cs [0:15];
    wire [TRW:0] ct [0:15];
    genvar l;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l
        ot_v41_bmul3_rne #(.GRADUAL_RNE(GRADUAL_RNE), .XS(DEEP != 0 ? 2 : RC != 0 ? 1 : 0)) u_m (.clk(clk), .rst_n(rst_n), .v(v_r), .a({w_r[16*l +: 16], 16'd0}), .b({x_r[16*l +: 16], 16'd0}),
                         .y(prod[l]), .fault(pf[l]));
        reg [PL-1:0] vp;
        always @(posedge clk or negedge rst_n) if (!rst_n) vp <= '0; else vp <= {vp[PL-2:0], v_r};
        assign pv[l] = vp[PL-1];
        if (DEEP != 0) begin : g_c5
        ot_v41_chain5 #(.PD(1), .ND(4), .NCH(NCHB), .TW(TRW + 1), .CUT(9'b1_1111_1111), .SPLIT6(S6C), .SPLIT9(S9C), .F5(0)) u_c (
            .clk(clk), .rst_n(rst_n), .v(pv[l]),
            .slot(t_p[TW-1 -: HW]), .first(t_p[TRW+2]), .last(t_p[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(t_p[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else if (RC >= 2) begin : g_cu
        ot_v41_chain2u2 #(.NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(clk), .rst_n(rst_n), .v(pv[l]),
            .slot(t_p[TW-1 -: HW]), .first(t_p[TRW+2]), .last(t_p[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(t_p[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else if (RC != 0) begin : g_c4
        ot_v41_chain4 #(.PD(1), .ND(4), .NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(clk), .rst_n(rst_n), .v(pv[l]),
            .slot(t_p[TW-1 -: HW]), .first(t_p[TRW+2]), .last(t_p[TRW+1]), .term(prod[l]), .term_f(pf[l]),
            .tag(t_p[TRW:0]), .ov(cv[l]), .osum(cs[l]), .of(cf[l]), .otag(ct[l]), .fault(cfault[l]));
        end else begin : g_c2
        ot_v41_chain2 #(.NCH(NCHB), .TW(TRW + 1), .CUT(CUT)) u_c (.clk(clk), .rst_n(rst_n), .v(pv[l]),
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
            ot_v41_fadd3 #(.CUT(CUTT), .SPLIT6(S6T), .SPLIT9(S9T)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(lvvld[lv]), .a(lvv[lv][2*k]),
                                          .b(lvv[lv][2*k+1]), .o0_ext(105'd0), .y(lvv[lv+1][k]), .err(e), .valid_out(vo));
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
