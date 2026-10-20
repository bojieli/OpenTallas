`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_segtree7: ot_v41_segtree6 (YF = 1, ce = 1) in structurally safe native-partition form (S81-QXPQ3 2026-10-20,
// owner SAFE checklist items 3 / 4 / 5).  Same events, same adds, same order, same output cycle for every output
// (zero added cycles); the q element instantiates it for NP = 1 (QS >= 5: the tree runs on the gated clock, so ce = 1).
//   (5) storage: the held left operands and their error bits (NT * LV slots x 33 b = 2.6 kb) live in a 1R1W SRAM macro
//       (ot_sram_1r1w_128x64_m1_p192, row = {tree, level}) instead of an 80-slot flop array with per-slot write enables
//       and an 80:1 read select.  The read address is the e-stage event's slot (sampled on the edge that loads x), so
//       the macro's output is the x1 read of segtree6.  The x2 event's write lands on the next edge; a slot written on
//       the SAME edge as the read (the event two ahead) is forwarded from registers (fw2: its decision and slot compare
//       registered on that edge, its operand z_d / error z_e), the event one ahead as before (y_fw, now in kept copies).
//   (3) fan-out: every wide select is a kept copy (ot_v41_kreg) per <= 32-load slice: the event-valid / final per
//       20-slot group (s_hold / s_pair), the adder-result valid per e-stage consumer, the queue head flags per head
//       slice; the base-node queue's read and write pointers are one-hot rings, one kept copy per head slice / field
//       half (no binary 8:1 select, no per-entry decode); the in-flight update uses the global decision (t_inc =
//       (pair | promote) at the event's tree, segtree6's QP_CHECK identity) instead of 16 slot-local forms; the e-stage
//       slot decode is two-level (tree one-hot x level compare).  The adder is ot_v41_fadd_np (bit-identical).
//   pq-tags glue: OSK kept copies of the output tree's one-hot {otree[PW-1] ^ opos[0], otree[PW-2:0]} (the PQ bank /
//   segment index of the tag lookup) leave with otree, so the lookup is an AND-OR over registered one-hot copies.
//   resets: NR regional reset leaves (rst_n[k], each <= 32 loads; the parent gives each its own kept leaf).
// ST7_CHECK (simulation): a shadow of segtree6's held / herr flops checks every x1 read and the in-flight identity.
// ---------------------------------------------------------------------------
module ot_v41_segtree7 #(
    parameter integer NT = 16,
    parameter integer LV = 5,
    parameter integer QD = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 8,
    parameter integer EARLY = 1,
    parameter integer OSK = 2,
    parameter integer NR = 12
) (
    input  wire                     clk,
    input  wire [NR-1:0]            rst_n,
    input  wire                     pclk,
    input  wire                     in_v,
    input  wire [3:0]               in_vk,      // four kept copies of in_v (the queue write pointer / enables, one per field slice)
    input  wire [$clog2(NT)-1:0]    in_tree,
    input  wire [2:0]               in_pos,
    input  wire [31:0]              in_val,
    input  wire                     in_final,
    input  wire                     in_err,
    output reg                      ov,
    output reg  [$clog2(NT)-1:0]    otree,
    output reg  [2:0]               opos,
    output reg  [31:0]              oval,
    output reg                      oerr,
    output reg                      fault,
    output wire [OSK*NT-1:0]        osel
);
    localparam integer PW = $clog2(NT);
    localparam integer LW = $clog2(LV + 1);
    localparam integer NH = NT * LV;
    localparam integer IW = $clog2(LAT + 6);
    localparam integer NG = 4;                      // slot groups (x1 partials, event-valid copies)
    localparam integer GS = (NH + NG - 1) / NG;
`ifndef SYNTHESIS
    initial if (PW + LW != 7 || QD != 8 || LAT != 8) $fatal(1, "ot_v41_segtree7: 128-row held SRAM ({tree, level} = 7 b), QD 8, LAT 8");
`endif
    // regional resets (k): 0 control, 1-3 have, 4-5 in-flight counts, 6 queue flags, 7-8 queue pointers, 9 adder
    // valid / err, 10 adder sum, 11 output / tree-copy control
    wire r_c = rst_n[0], r_q = rst_n[6], r_p0 = rst_n[7], r_p1 = rst_n[8], r_av = rst_n[9], r_ay = rst_n[10], r_o = rst_n[11];

    // ---------------- adder result, registered once (as segtree6) ----------------
    wire [31:0] sum_a;
    wire [1:0]  err_a;
    wire        sv_a;
    wire [PW+LW+1:0] st_a;
    reg  [31:0] sum;
    reg  [1:0]  err;
    reg  [PW+LW+1:0] st;      // {tree, level, final, err}
    always @(posedge clk) begin sum <= sum_a; err <= err_a; st <= st_a; end
    // sv copies: 0 control (e_v, x_add, use_q, count), 1 / 5 slot decode trees 0-7 / 8-15, 2 address / x_t / compares,
    // 3-4 operand halves, 6 the tpos read
    wire [6:0] svk;
    for (genvar g = 0; g < 7; g = g + 1) begin : g_sv
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_s (.clk(clk), .arst_n(r_c), .d(sv_a), .q(svk[g]));
    end
    wire sv = svk[0];

    // ---------------- base-node queue: one-hot rings ----------------
    localparam integer NQ = 5;                      // head slices: 4 x 8 value bits, 4 = tree / final / error / position
    reg  [PW-1:0] qt [0:QD-1];
    reg  [31:0] qv [0:QD-1];
    reg  qf [0:QD-1], qe [0:QD-1];
    reg  [2:0] qp [0:QD-1];
    reg  [$clog2(QD):0] qc;
    wire [$clog2(QD):0] qc_nx = qc + (in_v ? 1'b1 : 1'b0) - ((!sv && qc != 0) ? 1'b1 : 1'b0);
    wire [2:0]    fl_nx = {qc_nx == QD, qc_nx == 1, qc_nx == 0};
    wire [2:0]    fl [0:NQ-1];
    wire [NQ-1:0] svc;
    for (genvar g = 0; g < NQ; g = g + 1) begin : g_fl
        ot_v41_kreg #(.W(3), .AR(1), .RV(3'b001)) u_f (.clk(clk), .arst_n(r_q), .d(fl_nx), .q(fl[g]));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_s (.clk(clk), .arst_n(r_q), .d(sv_a), .q(svc[g]));
    end
    reg [NQ-1:0] uq, byp;
    always @* for (int c = 0; c < NQ; c++) begin
        uq[c]  = !svc[c] && !fl[c][0];
        byp[c] = fl[c][0] || (fl[c][1] && !svc[c]) || (fl[c][2] && svc[c]);
    end
    function automatic [QD-1:0] rotl(input [QD-1:0] x); rotl = {x[QD-2:0], x[QD-1]}; endfunction
    // write pointer: copies 0-2 write value bits 10:0 / 21:11 / 31:22, copy 3 tree / final / error / position
    wire [QD-1:0] wpk [0:3];
    for (genvar g = 0; g < 4; g = g + 1) begin : g_wp
        ot_v41_kreg #(.W(QD), .AR(1), .RV({{(QD-1){1'b0}}, 1'b1})) u_w (.clk(clk), .arst_n(r_p0), .d(in_vk[g] ? rotl(wpk[g]) : wpk[g]), .q(wpk[g]));
    end
    // read pointer (one-hot of qr), one copy per head slice; slice c's next-head one-hot = qr + use_q
    wire [QD-1:0] rpk [0:NQ-1];
    wire [QD-1:0] nxs [0:NQ-1];
    for (genvar g = 0; g < NQ; g = g + 1) begin : g_rp
        ot_v41_kreg #(.W(QD), .AR(1), .RV({{(QD-1){1'b0}}, 1'b1})) u_r (.clk(clk), .arst_n(g == 0 ? r_p0 : r_p1), .d(uq[g] ? rotl(rpk[g]) : rpk[g]), .q(rpk[g]));
`ifdef OT_NP_TREE_MUT_Q
        assign nxs[g] = rpk[g];                                                // negative control: the pop's advance ignored
`else
        assign nxs[g] = uq[g] ? rotl(rpk[g]) : rpk[g];
`endif
    end
    always @(posedge clk) begin
        for (int i = 0; i < QD; i++) begin
            if (in_vk[0] && wpk[0][i]) qv[i][10:0] <= in_val[10:0];
            if (in_vk[1] && wpk[1][i]) qv[i][21:11] <= in_val[21:11];
            if (in_vk[2] && wpk[2][i]) qv[i][31:22] <= in_val[31:22];
            if (in_vk[3] && wpk[3][i]) begin qt[i] <= in_tree; qf[i] <= in_final; qe[i] <= in_err; qp[i] <= in_pos; end
        end
    end
    reg [31:0] h_v; reg [PW-1:0] h_t; reg h_f, h_e; reg [2:0] h_p;
    reg [31:0] rdv; reg [PW-1:0] rdt; reg rdf, rde; reg [2:0] rdp;
    always @* begin
        rdv = '0; rdt = '0; rdf = 1'b0; rde = 1'b0; rdp = '0;
        for (int i = 0; i < QD; i++) begin
            for (int c = 0; c < 4; c++) if (nxs[c][i]) rdv[8*c +: 8] = rdv[8*c +: 8] | qv[i][8*c +: 8];
            if (nxs[4][i]) begin rdt = rdt | qt[i]; rdf = rdf | qf[i]; rde = rde | qe[i]; rdp = rdp | qp[i]; end
        end
    end
    always @(posedge clk) begin
        for (int c = 0; c < 4; c++) h_v[8*c +: 8] <= byp[c] ? in_val[8*c +: 8] : rdv[8*c +: 8];
        if (byp[4]) begin h_t <= in_tree; h_f <= in_final; h_e <= in_err; h_p <= in_pos; end
        else begin h_t <= rdt; h_f <= rdf; h_e <= rde; h_p <= rdp; end
    end
    wire use_q = !sv && qc != 0;

    // ---------------- STAGE 1 (e): the event considered this cycle ----------------
    wire          e_v  = sv || qc != 0;
    wire          e_f  = sv ? st[1] : h_f;
    wire          e_e  = sv ? (st[0] | err != 2'd0) : h_e;
    wire [PW-1:0] e_t1 = svk[1] ? st[PW+LW+1 -: PW] : h_t;      // slot decode, trees 0-7
    wire [LW-1:0] e_l1 = svk[1] ? st[LW+1 -: LW] : {LW{1'b0}};
    wire [PW-1:0] e_t5 = svk[5] ? st[PW+LW+1 -: PW] : h_t;      // slot decode, trees 8-15
    wire [LW-1:0] e_l5 = svk[5] ? st[LW+1 -: LW] : {LW{1'b0}};
    wire [PW-1:0] e_t6 = svk[6] ? st[PW+LW+1 -: PW] : h_t;      // tpos read
    wire [PW-1:0] e_t2 = svk[2] ? st[PW+LW+1 -: PW] : h_t;      // address, x_t, tpos, compares
    wire [LW-1:0] e_l2 = svk[2] ? st[LW+1 -: LW] : {LW{1'b0}};
    wire [31:0]   e_d  = {svk[4] ? sum[31:16] : h_v[31:16], svk[3] ? sum[15:0] : h_v[15:0]};
    reg  [NT-1:0] e_toh;
    reg  [LV-1:0] e_leq, e_lgt, e_leq5, e_lgt5;
    reg  [NH-1:0] e_oh, e_above;
    always @* begin
        for (int t = 0; t < NT; t++) e_toh[t] = (t < NT / 2) ? e_t1 == t : e_t5 == t;
        for (int l = 0; l < LV; l++) begin e_leq[l] = e_l1 == l; e_lgt[l] = l > e_l1; e_leq5[l] = e_l5 == l; e_lgt5[l] = l > e_l5; end
        for (int h = 0; h < NH; h++) begin
            e_oh[h] = e_toh[h / LV] && ((h / LV < NT / 2) ? e_leq[h % LV] : e_leq5[h % LV]);
            e_above[h] = e_toh[h / LV] && ((h / LV < NT / 2) ? e_lgt[h % LV] : e_lgt5[h % LV]);
        end
    end
    reg [2:0] tpos [0:NT-1];
    reg          x_v, x_f, x_e, x_add;
    reg [PW-1:0] x_t;
    reg [LW-1:0] x_l;
    reg [31:0]   x_d;
    reg [NH-1:0] x_oh, x_above;
    reg [NT-1:0] x_toh;
    reg [2:0]    x_pos;
    always @(posedge clk or negedge r_c) if (!r_c) x_v <= 1'b0; else x_v <= e_v;
    always @(posedge clk) begin
        x_t <= e_t2; x_l <= e_l2; x_f <= e_f; x_e <= e_e; x_d <= e_d; x_add <= sv;
        x_oh <= e_oh; x_above <= e_above; x_toh <= e_toh;
        x_pos <= use_q ? h_p : tpos[e_t6];
        if (use_q) tpos[h_t] <= h_p;
    end

    // ---------------- held store: 1R1W SRAM, row {tree, level}, bits {herr, held} ----------------
    wire [63:0] h_rd;
    wire        hold;
    reg          y_v, y_f, y_e, y_add;
    reg [PW-1:0] y_t;
    reg [LW-1:0] y_l;
    reg [31:0]   y_d;
    ot_sram_1r1w_128x64_m1_p192 u_hst (.clk(clk), .r_ce_in(1'b1), .r_addr_in({e_t2, e_l2}), .rd_out(h_rd),
        .w_ce_in(hold), .w_addr_in({y_t, y_l}), .wd_in({31'd0, y_e, y_d}), .w_mask_in({31'd0, 33'h1_ffff_ffff}));
    // fw2: the x2 event of THIS edge holds the slot read on this edge (registered decision and slot compare)
    wire [2:0] fw2;            // 0 bits 10:0, 1 bits 21:11, 2 bits 31:22 + error
    for (genvar g = 0; g < 3; g = g + 1) begin : g_f2
`ifdef OT_NP_TREE_MUT_F2
        ot_v41_kreg #(.W(1)) u_f (.clk(clk), .arst_n(1'b1), .d(1'b0), .q(fw2[g]));      // negative control: no same-edge forward
`else
        ot_v41_kreg #(.W(1)) u_f (.clk(clk), .arst_n(1'b1), .d(hold && y_t == e_t2 && y_l == e_l2), .q(fw2[g]));
`endif
    end
    reg [31:0] z_d; reg z_e;

    // ---------------- STAGE 2a (x1): read into group partials ----------------
    reg [IW-1:0] infl [0:NT-1];
    reg [NH-1:0] y_oh;
    reg [NT-1:0] y_toh;
    reg [2:0]    y_pos;
    reg [NG-1:0] y_hv, y_ab;
    reg [31:0]   y_hd;
    reg          y_he;
    reg [31:0]   y_fd;
    reg          y_fe;
    reg [IW-1:0] y_infl;
    wire [2:0]   y_fw;         // kept copies of the one-ahead forward: 0 bits 15:0, 1 bits 31:16, 2 error
    wire [NG-1:0] vnf, vv;     // per slot group: y_v && !y_f (hold), y_v (pair)
    for (genvar g = 0; g < NG; g = g + 1) begin : g_vg
        ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_v (.clk(clk), .arst_n(r_c), .d({x_v && !x_f, x_v}), .q({vnf[g], vv[g]}));
    end
    // STAGE 2b (x2) decision from registers
    wire y_have = |y_hv;
    wire above = |y_ab;
    wire idle_tree = y_infl == (y_add ? {{(IW-1){1'b0}}, 1'b1} : {IW{1'b0}});
    wire early = (EARLY != 0) && y_v && y_f && !y_have && !above && idle_tree;
    wire top = y_l == LV[LW-1:0] || early;
    wire pair = y_v && !top && y_have;
    wire promote = y_v && !top && !y_have && y_f;
    assign hold = y_v && !top && !y_have && !y_f;
    wire inc = pair || promote;
    wire inc2;                 // trees 8-15: the decision from a second kept copy of its registers (below)
    wire vadd = y_v && y_add;
    wire [31:0] u_held = {y_fw[1] ? y_fd[31:16] : y_hd[31:16], y_fw[0] ? y_fd[15:0] : y_hd[15:0]};
    wire        u_herr = y_fw[2] ? y_fe : y_he;
    reg  [NH-1:0] have;
    reg  [NH-1:0] s_hold, s_pair;
    always @* for (int h = 0; h < NH; h++) begin
`ifdef OT_NP_TREE_MUT_H
        s_hold[h] = vv[h / GS] && y_oh[h] && !have[h];               // negative control: the final bit ignored
`else
        s_hold[h] = vnf[h / GS] && y_oh[h] && !have[h];
`endif
        s_pair[h] = vv[h / GS] && y_oh[h] && have[h];
    end
    wire [NH-1:0] have_nx = (have & ~s_pair) | s_hold;
    reg  [NT-1:0] t_inc, t_dec;
    always @* for (int t = 0; t < NT; t++) begin t_inc[t] = y_toh[t] && ((t < NT / 2) ? inc : inc2); t_dec[t] = y_toh[t] && vadd; end
    reg  [NG-1:0] r_hv, r_ab;
    always @* begin
        r_hv = '0; r_ab = '0;
        for (int h = 0; h < NH; h++) begin
            r_hv[h / GS] = r_hv[h / GS] | (have_nx[h] & x_oh[h]);
            r_ab[h / GS] = r_ab[h / GS] | (have_nx[h] & x_above[h]);
        end
    end
    wire [31:0] r_hd = {fw2[2] ? z_d[31:22] : h_rd[31:22], fw2[1] ? z_d[21:11] : h_rd[21:11], fw2[0] ? z_d[10:0] : h_rd[10:0]};
    wire        r_he = fw2[2] ? z_e : h_rd[32];
    // YF in-flight read from registers
    reg same_r;
    always @(posedge clk or negedge r_c) if (!r_c) same_r <= 1'b0; else same_r <= x_v && e_t2 == x_t;
    wire [IW-1:0] yi_p = y_infl + 1'b1 - (y_add ? 1'b1 : 1'b0);
    wire [IW-1:0] yi_n = y_infl - (y_add ? 1'b1 : 1'b0);
    wire [IW-1:0] yf_same = inc ? yi_p : yi_n;
    reg  [IW-1:0] r_infl_s;
    always @* begin
        r_infl_s = '0;
        for (int t = 0; t < NT; t++) if (x_toh[t]) r_infl_s = r_infl_s | infl[t];
    end
    wire [IW-1:0] r_infl_y = (y_v && same_r) ? yf_same : r_infl_s;
    // a second copy of the decision's registers (kept), whose decision drives the in-flight increments of trees 8-15
    wire [NG-1:0] y_hv2, y_ab2; wire y_v2, y_f2, y_add2; wire [LW-1:0] y_l2; wire [IW-1:0] y_infl2;
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_yv2 (.clk(clk), .arst_n(r_c), .d(x_v), .q(y_v2));
    ot_v41_kreg #(.W(2 * NG + 2 + LW + IW)) u_yd2 (.clk(clk), .arst_n(1'b1), .d({r_hv, r_ab, x_f, x_add, x_l, r_infl_y}),
        .q({y_hv2, y_ab2, y_f2, y_add2, y_l2, y_infl2}));
    wire have2 = |y_hv2;
    wire early2 = (EARLY != 0) && y_v2 && y_f2 && !have2 && !(|y_ab2) && y_infl2 == (y_add2 ? {{(IW-1){1'b0}}, 1'b1} : {IW{1'b0}});
    wire top2 = y_l2 == LV[LW-1:0] || early2;
    assign inc2 = y_v2 && !top2 && (have2 || y_f2);
`ifdef OT_NP_TREE_MUT_F
    wire r_fw = 1'b0;                                                     // negative control: no one-ahead forward
`else
    wire r_fw = hold && y_t == x_t && y_l == x_l;
`endif
    for (genvar g = 0; g < 3; g = g + 1) begin : g_fw
        ot_v41_kreg #(.W(1)) u_f (.clk(clk), .arst_n(1'b1), .d(r_fw), .q(y_fw[g]));
    end
    always @(posedge clk or negedge r_c) if (!r_c) y_v <= 1'b0; else y_v <= x_v;
    always @(posedge clk) begin
        y_t <= x_t; y_l <= x_l; y_f <= x_f; y_e <= x_e; y_d <= x_d; y_add <= x_add;
        y_oh <= x_oh; y_toh <= x_toh; y_pos <= x_pos;
        y_hv <= r_hv; y_ab <= r_ab; y_hd <= r_hd; y_he <= r_he; y_infl <= r_infl_y;
        y_fd <= y_d; y_fe <= y_e;
        z_d <= y_d; z_e <= y_e;
    end

    // ---------------- adder-operand stage (as segtree6, NZ = 4 pair copies) ----------------
    localparam integer NZ = 4;
    reg [31:0] z_h;
    reg        z_v;
    always @(posedge clk) z_h <= u_held;
    always @(posedge clk or negedge r_c) if (!r_c) z_v <= 1'b0; else z_v <= inc;
    wire [NZ-1:0] z_pair;
    for (genvar g = 0; g < NZ; g = g + 1) begin : g_zp
        ot_v41_kreg #(.W(1)) u_p (.clk(clk), .arst_n(1'b1), .d(pair), .q(z_pair[g]));
    end
    reg [31:0] add_a, add_b;
    reg        add_v;
    always @(posedge clk) begin
        for (int b = 0; b < 32; b++) begin
            add_a[b] <= z_pair[b / (32 / (NZ / 2))] ? z_h[b] : z_d[b];
            add_b[b] <= z_pair[NZ / 2 + b / (32 / (NZ / 2))] ? z_d[b] : 1'b0;
        end
    end
    always @(posedge clk or negedge r_c) if (!r_c) add_v <= 1'b0; else add_v <= z_v;
    wire [31:0] ad_yk; wire ad_vk;
    ot_v41_fadd_np #(.CUT(CUT), .NYK(0), .NVK(0)) u_add (.clk(pclk), .rst_v(r_av), .rst_y(r_ay), .rst_k(1'b1), .valid_in(add_v),
        .a(add_a), .b(add_b), .o0_ext(105'd0), .y(sum_a), .err(err_a), .valid_out(sv_a), .yk(ad_yk), .vk(ad_vk));
    ot_hdc_delay #(.W(PW + LW + 2), .D(LAT + 2)) u_t (.clk(pclk), .rst_n(1'b1),
        .d({y_t, y_l + 1'b1, y_f, y_e | (pair && u_herr)}), .q(st_a));

    // ---------------- state updates ----------------
    for (genvar g = 0; g < 3; g = g + 1) begin : g_hv
        localparam integer LO = (NH * g) / 3, HI = (NH * (g + 1)) / 3;
        always @(posedge clk or negedge rst_n[1 + g]) if (!rst_n[1 + g]) have[HI-1:LO] <= '0; else have[HI-1:LO] <= have_nx[HI-1:LO];
    end
    for (genvar g = 0; g < 2; g = g + 1) begin : g_in
        always @(posedge clk or negedge rst_n[4 + g])
            if (!rst_n[4 + g]) for (int t = g * NT / 2; t < (g + 1) * NT / 2; t++) infl[t] <= '0;
            else for (int t = g * NT / 2; t < (g + 1) * NT / 2; t++) infl[t] <= infl[t] + (t_inc[t] ? 1'b1 : 1'b0) - (t_dec[t] ? 1'b1 : 1'b0);
    end
    always @(posedge clk or negedge r_q) if (!r_q) qc <= '0; else qc <= qc + (in_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
    always @(posedge clk or negedge r_o) begin
        if (!r_o) begin ov <= 1'b0; oerr <= 1'b0; fault <= 1'b0; end
        else begin
            if (in_v && qc == QD && !use_q) fault <= 1'b1;
            if (y_v && y_l == LV[LW-1:0] && !y_f) fault <= 1'b1;
            ov <= y_v && top;
            oerr <= y_v && top && y_e;
        end
    end
    always @(posedge clk) begin opos <= y_pos; oval <= y_d; otree <= y_t; end
    // pq-tags glue: one-hot {tree[PW-1] ^ pos[0], tree[PW-2:0]} of the leaving node, OSK kept copies
    reg [NT-1:0] os_d;
    always @* for (int t = 0; t < NT; t++) os_d[t] = {y_t[PW-1] ^ y_pos[0], y_t[PW-2:0]} == t;
    for (genvar g = 0; g < OSK; g = g + 1) begin : g_os
        ot_v41_kreg #(.W(NT)) u_o (.clk(clk), .arst_n(1'b1), .d(os_d), .q(osel[NT*g +: NT]));
    end

`ifdef ST7_CHECK
    // shadow of segtree6's held / herr flops: every x1 read must equal it (the SRAM read + both forwards)
    reg [31:0] sh_held [0:NH-1]; reg [NH-1:0] sh_herr;
    always @(posedge clk) for (int h = 0; h < NH; h++) if (s_hold[h]) begin sh_held[h] <= y_d; sh_herr[h] <= y_e; end
    reg [NH-1:0] y_above_chk;
    always @(posedge clk) y_above_chk <= x_above;
    reg [31:0] c_hd; reg c_he;
    always @* begin
        c_hd = '0; c_he = 1'b0;
        for (int h = 0; h < NH; h++) if (y_oh[h]) begin c_hd = c_hd | sh_held[h]; c_he = c_he | sh_herr[h]; end
    end
    always @(negedge clk) if (&rst_n && y_v) begin
        if (pair && (u_held !== c_hd || u_herr !== c_he)) begin $display("ST7_CHECK FAIL held read %m %t", $time); $fatal(1); end
        if (s_hold !== (hold ? y_oh : {NH{1'b0}}) || s_pair !== (pair ? y_oh : {NH{1'b0}}))
            begin $display("ST7_CHECK FAIL hold / pair %m %t", $time); $fatal(1); end
        if (y_have !== |(have & y_oh) || above !== |(have & y_above_chk) || y_infl !== infl[y_t])
            begin $display("ST7_CHECK FAIL x1 read %m %t", $time); $fatal(1); end
    end
`endif
endmodule
