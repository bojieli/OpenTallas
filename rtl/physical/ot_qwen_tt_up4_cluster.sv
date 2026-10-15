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
// Pin stage = ONE hardened leaf qfd_tt_up4_pin on the cluster's W face (el1013-qwen-small-masters r3: a cluster parent
// keeps no flop of its own; it has no clock tree).  One capture flop on every pw / lf / sel bit and one launch flop on
// every ty / flt bit.  Cycles: pw, lf and sel +1 edge (their relative timing is unchanged, so the leaf keeps its DLY),
// ty and flt +1 edge: seen from the bands the tree top answers 2 edges later = ONE link relay stage
// (ot_qfd_band_lanes LNK + 1).  tt_use / tt_v are taken from leaf 0 (the four leaves see the same sel / tv / pw_v).
// The parent is WIRES ONLY: pin leaf <-> 4 band leaves, every seam leaf register -> wire -> leaf register.
//
// Clock: ref_tile clock form "entries" (define OT_QFD_UP4_CK_ENTRIES): one clock port per leaf (ck_pin, ck_l0..3), the
// die delivers phi - R_i at each.  Without the define the cluster has the single port ck (benches).
// OT_QFD_UP4_HARD: the leaves are hard children (LEF / LIB cells, no parameter overrides: the views are
// ot_qfd_band_upper NL 4 / NB 3 / LG 12 / LNK 0 / DLY 1 / TREE_LAT 7 / TCUT 7 and qfd_tt_up4_pin).
//
// OT_QFD_UP4_MUT (bench mutant only, never synthesized): leaves 1 and 2 receive each other's band-0 words.
// OT_QFD_UP4_PIN_MUT (bench mutant only): the pin leaf launches ty word (k 0, lane 0) one bit rotated.

// ---- the pin-stage leaf (hard leaf of the cluster) -------------------------------------------------------------------
`ifndef OT_QFD_UP4_HARD
module qfd_tt_up4_pin (
    input  wire          ck,
    input  wire          rst_n,
    // die side (cluster W face)
    input  wire [512:0]  pw0,
    input  wire [512:0]  pw1,
    input  wire [512:0]  pw2,
    input  wire          lf0,
    input  wire          lf1,
    input  wire          lf2,
    input  wire [25:0]   sel,
    output wire [1537:0] ty,
    output wire          flt,
    // leaf side
    output wire [1535:0] pw_a,
    output wire [2:0]    pv_a,
    output wire [2:0]    lf_a,
    output wire [25:0]   sel_a,
    input  wire [1535:0] ty_w,
    input  wire          use_w,
    input  wire          v_w,
    input  wire [3:0]    flt_w
);
    // the leaf's reset register (async assert, registered release)
    reg rt;
    always @(posedge ck or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep *) reg [1535:0] pw_q;
    (* keep *) reg [2:0]    pv_q, lf_q;
    (* keep *) reg [25:0]   sel_q;
    always @(posedge ck) begin pw_q <= {pw2[511:0], pw1[511:0], pw0[511:0]}; sel_q <= sel; end
    always @(posedge ck or negedge rt)
        if (!rt) begin pv_q <= 3'd0; lf_q <= 3'd0; end
        else begin pv_q <= {pw2[512], pw1[512], pw0[512]}; lf_q <= {lf2, lf1, lf0}; end
    assign pw_a = pw_q; assign pv_a = pv_q; assign lf_a = lf_q; assign sel_a = sel_q;
    (* keep *) reg [1535:0] ty_q;
    (* keep *) reg          use_q, v_q, flt_q;
`ifdef OT_QFD_UP4_PIN_MUT
    always @(posedge ck) ty_q <= {ty_w[1535:32], ty_w[30:0], ty_w[31]};
`else
    always @(posedge ck) ty_q <= ty_w;
`endif
    always @(posedge ck or negedge rt)
        if (!rt) begin use_q <= 1'b0; v_q <= 1'b0; flt_q <= 1'b0; end
        else begin use_q <= use_w; v_q <= v_w; flt_q <= |flt_w; end
    assign ty  = {v_q, use_q, ty_q};
    assign flt = flt_q;
endmodule
`endif

module qfd_tt_up4 #(
    parameter integer NB   = 3,
    parameter integer LG   = 12,
    parameter integer DLY  = 2,           // leaf c-tap delay (soft build / bench only; the hard leaf is DLY 1)
    parameter integer TREE_LAT = 7,
    parameter integer TCUT = 7,
    parameter integer LMUT = 0            // leaf-internal mutant (bench only)
) (
`ifdef OT_QFD_UP4_CK_ENTRIES
    input  wire                 ck_pin,
    input  wire                 ck_l0,
    input  wire                 ck_l1,
    input  wire                 ck_l2,
    input  wire                 ck_l3,
`else
    input  wire                 ck,
`endif
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
    // wires only: no flop, no gate at this level
`ifdef OT_QFD_UP4_CK_ENTRIES
    wire       c_pin = ck_pin;
    wire [3:0] c_l   = {ck_l3, ck_l2, ck_l1, ck_l0};
`else
    wire       c_pin = ck;
    wire [3:0] c_l   = {4{ck}};
`endif
    wire [1535:0] pw_a, ty_w;
    wire [2:0]    pv_a, lf_a;
    wire [25:0]   sel_a;
    wire [4*384-1:0] lty;
    wire [3:0] luse, lv, lflt;
    generate if (NB != 3 || LG != 12) begin : g_cfg_err
        QFD_TT_UP4_IS_NB3_LG12 u_cfg_err ();   // undefined: elaboration stops
    end endgenerate
    qfd_tt_up4_pin u_pin (.ck(c_pin), .rst_n(rst_n), .pw0(pw0), .pw1(pw1), .pw2(pw2), .lf0(lf0), .lf1(lf1), .lf2(lf2),
        .sel(sel), .ty(ty), .flt(flt), .pw_a(pw_a), .pv_a(pv_a), .lf_a(lf_a), .sel_a(sel_a), .ty_w(ty_w),
        .use_w(luse[0]), .v_w(lv[0]), .flt_w(lflt));
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
`ifdef OT_QFD_UP4_HARD
        ot_qfd_band_upper u_leaf (
`else
        ot_qfd_band_upper #(.NL(4), .NB(NB), .LNK(0), .DLY(DLY), .TREE_LAT(TREE_LAT), .MUT(LMUT), .TCUT(TCUT), .LG(LG)) u_leaf (
`endif
            .clk(c_l[l]), .rst_n(rst_n), .pw(lpw), .pw_v(pv_a), .lf(lf_a), .sel_e(sel_a[LG:0]), .tv_e(sel_a[2*LG+1:LG+1]),
            .tt_ty(lty[384*l +: 384]), .tt_use(luse[l]), .tt_v(lv[l]), .fault(lflt[l]));
    end endgenerate
    generate for (l = 0; l < 4; l = l + 1) begin : g_o
        for (k = 0; k < 3; k = k + 1) begin : g_k
            for (j = 0; j < 4; j = j + 1) begin : g_j
                assign ty_w[32*(k*16 + 4*l + j) +: 32] = lty[384*l + 32*(k*4 + j) +: 32];
            end
        end
    end endgenerate
endmodule

// ---- qfd_tt_up4_w: the slot WITHOUT a parent (el1013-qwen-small-masters r3, two-level form) ---------------------------
// The four leaves have no net between them, so the slot tt_up4_0 needs neither a parent route nor a pin stage: the die
// places 4 x ot_qfd_band_upper (kit qfd_tt_up4_leaf, 64.8 x 205.2, one row, words in on S, out on N) and gives each its
// own clock entry.  This wrapper is the RTL of that binding (wires only, per-leaf bundles = the leaf's own pins); it is
// what the composition bench runs (tb_qfd_band_lanes CL=2) and what the die netlist instantiates leaf by leaf.
//   pw_l<l>[383:0] = leaf l's band words: [32*(b*4 + j)] = band b, lane 4l + j        (in,  leaf S face)
//   pv_l<l>[2:0], lf_l<l>[2:0] = the bands' valid / fault, one copy a leaf (die fan-out) (in,  leaf S face)
//   sel_l<l>[25:0] = {tv_e[12:0], sel_e[12:0]}, one copy a leaf (die fan-out)            (in,  leaf W face)
//   ty_l<l>[383:0] = leaf l's tree-top words: [32*(k*4 + j)] = word k, lane 4l + j      (out, leaf N face)
//   tu_l<l>, tv_l<l>, flt_l<l> = tt_use / tt_v / fault of leaf l (the die uses leaf 0's tu / tv and ORs the faults in
//   its fault chain)                                                                     (out, leaf N face)
// Cycles: none added (the leaf pin registers are the stations): the tree top answers as the flat NL 16 block does.
// OT_QFD_UP4_MUT: leaves 1 and 2 receive each other's band-0 words (bench mutant only).
module qfd_tt_up4_w #(
    parameter integer DLY  = 1,           // soft build / bench only; the hard leaf is DLY 1
    parameter integer LNK  = 0,
    parameter integer TREE_LAT = 7,
    parameter integer TCUT = 7,
    parameter integer LMUT = 0,
    parameter integer RPIN = 0            // q14 r11: leaf reset pin register (soft build / bench; the hard view is RPIN 1)
) (
    input  wire [3:0]        ck,          // one clock entry a leaf
    input  wire [3:0]        rst_n,
    input  wire [4*384-1:0]  pw_l,
    input  wire [4*3-1:0]    pv_l,
    input  wire [4*3-1:0]    lf_l,
    input  wire [4*26-1:0]   sel_l,
    output wire [4*384-1:0]  ty_l,
    output wire [3:0]        tu_l,
    output wire [3:0]        tv_l,
    output wire [3:0]        flt_l
);
    genvar l;
    generate for (l = 0; l < 4; l = l + 1) begin : g_leaf
`ifdef OT_QFD_UP4_MUT
        localparam integer LS = (l == 1) ? 2 : (l == 2) ? 1 : l;
        wire [383:0] lpw = {pw_l[384*l + 128 +: 256], pw_l[384*LS +: 128]};
`else
        wire [383:0] lpw = pw_l[384*l +: 384];
`endif
`ifdef OT_QFD_UP4_HARD
        ot_qfd_band_upper u_leaf (
`else
        ot_qfd_band_upper #(.NL(4), .NB(3), .LNK(LNK), .DLY(DLY), .TREE_LAT(TREE_LAT), .MUT(LMUT), .TCUT(TCUT), .LG(12), .RPIN(RPIN)) u_leaf (
`endif
            .clk(ck[l]), .rst_n(rst_n[l]), .pw(lpw), .pw_v(pv_l[3*l +: 3]), .lf(lf_l[3*l +: 3]),
            .sel_e(sel_l[26*l +: 13]), .tv_e(sel_l[26*l + 13 +: 13]),
            .tt_ty(ty_l[384*l +: 384]), .tt_use(tu_l[l]), .tt_v(tv_l[l]), .fault(flt_l[l]));
    end endgenerate
endmodule
