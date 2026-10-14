// Qwen ROM TP8 die (track B): tree-top upper CLUSTER cell qfd_tt_up4 of contract v4b T13 (slot tt_up4_0,
// 345.576 x 388.776): 4 hardened leaves ot_qfd_band_upper #(NL 4) (kit physical/ref_tile/qfd_tt_up4_leaf, 64.8 x 205.2,
// one row along x) + the pin stage of the cluster.  The 16 lanes are independent in the upper levels, so 4 leaves of 4
// lanes compute exactly what one NL 16 block computes; the cluster only slices the words by lane.
//
// Die bundles (first field = MSB):
//   pw<b>[512:0] = {pw_v[b], band b's 16 lane words (lane l at [32*l])}                 (in,  W)   b = 0..2
//   lf<b>        = band b's fault                                                         (in,  W)
//   sel[25:0]    = {tv_e[12:0], sel_e[12:0]}  (LG 12)                                     (in,  S)
//   ty[1537:0]   = {tt_v, tt_use, tt_ty[1535:0]}, tt_ty word (k, lane l) at [32*(k*16 + l)], k = 0..2   (out, W)
//   flt          = OR of the 4 leaves' faults                                             (out, E)
// Leaf l takes lanes 4l .. 4l+3: leaf pw[32*(b*4 + j)] = pw<b>[32*(4l + j)], tt_ty[32*(k*16 + 4l + j)] = leaf tt_ty[32*(k*4 + j)].
//
// Pin stage (the only flops of the parent, all AT the cluster pins): one capture flop on every pw / lf / sel bit and one
// launch flop on every ty / flt bit.  Cycles: pw, lf and sel +1 edge (their relative timing is unchanged, so the leaf keeps
// its DLY), ty and flt +1 edge: seen from the bands the tree top answers 2 edges later = ONE link relay stage
// (ot_qfd_band_lanes LNK + 1).  tt_use / tt_v are taken from leaf 0 (the four leaves see the same sel / tv / pw_v).
//
// OT_QFD_UP4_MUT (bench mutant only, never synthesized): leaves 1 and 2 receive each other's band-0 words.
module qfd_tt_up4 #(
    parameter integer NB   = 3,
    parameter integer LG   = 12,
    parameter integer DLY  = 2,           // leaf c-tap delay as benched (the cluster adds no skew between pw and sel)
    parameter integer TREE_LAT = 7,
    parameter integer TCUT = 7,
    parameter integer LMUT = 0            // leaf-internal mutant (bench only)
) (
    input  wire                 ck,
    input  wire                 rst_n,
    input  wire [512:0]         pw0,
    input  wire [512:0]         pw1,
    input  wire [512:0]         pw2,
    input  wire                 lf0,
    input  wire                 lf1,
    input  wire                 lf2,
    input  wire [2*(LG+1)-1:0]  sel,
    output wire [1537:0]        ty,
    output wire                 flt
);
    // ---- capture pin stage ----------------------------------------------------------------------------------------
    (* keep *) reg [3*512-1:0] pw_a;
    (* keep *) reg [2:0]       pv_a, lf_a;
    (* keep *) reg [2*(LG+1)-1:0] sel_a;
    always @(posedge ck) begin pw_a <= {pw2[511:0], pw1[511:0], pw0[511:0]}; sel_a <= sel; end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pv_a <= 3'd0; lf_a <= 3'd0; end
        else begin pv_a <= {pw2[512], pw1[512], pw0[512]}; lf_a <= {lf2, lf1, lf0}; end
    // ---- 4 leaves ---------------------------------------------------------------------------------------------------
    wire [4*384-1:0] lty;
    wire [3:0] luse, lv, lflt;
    genvar l, b, j, k;
    generate for (l = 0; l < 4; l = l + 1) begin : g_leaf
        wire [NB*4*32-1:0] lpw;
        for (b = 0; b < NB; b = b + 1) begin : g_b
            for (j = 0; j < 4; j = j + 1) begin : g_j
`ifdef OT_QFD_UP4_MUT
                localparam integer LS = (b == 0 && l == 1) ? 2 : (b == 0 && l == 2) ? 1 : l;
`else
                localparam integer LS = l;
`endif
                assign lpw[32*(b*4 + j) +: 32] = pw_a[512*b + 32*(4*LS + j) +: 32];
            end
        end
        ot_qfd_band_upper #(.NL(4), .NB(NB), .LNK(0), .DLY(DLY), .TREE_LAT(TREE_LAT), .MUT(LMUT), .TCUT(TCUT), .LG(LG)) u_leaf (
            .clk(ck), .rst_n(rst_n), .pw(lpw), .pw_v(pv_a), .lf(lf_a), .sel_e(sel_a[LG:0]), .tv_e(sel_a[2*LG+1:LG+1]),
            .tt_ty(lty[384*l +: 384]), .tt_use(luse[l]), .tt_v(lv[l]), .fault(lflt[l]));
    end endgenerate
    // ---- launch pin stage -------------------------------------------------------------------------------------------
    wire [1535:0] ty_w;
    generate for (l = 0; l < 4; l = l + 1) begin : g_o
        for (k = 0; k < 3; k = k + 1) begin : g_k
            for (j = 0; j < 4; j = j + 1) begin : g_j
                assign ty_w[32*(k*16 + 4*l + j) +: 32] = lty[384*l + 32*(k*4 + j) +: 32];
            end
        end
    end endgenerate
    (* keep *) reg [1535:0] ty_q;
    (* keep *) reg          use_q, v_q, flt_q;
    always @(posedge ck) ty_q <= ty_w;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin use_q <= 1'b0; v_q <= 1'b0; flt_q <= 1'b0; end
        else begin use_q <= luse[0]; v_q <= lv[0]; flt_q <= |lflt; end
    assign ty  = {v_q, use_q, ty_q};
    assign flt = flt_q;
endmodule
