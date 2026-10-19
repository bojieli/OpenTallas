`timescale 1ns/1ps
// ot_v41_segtree5_rp (S81-C199 reset partition, 2026-10-19, opt-in OT_BF_RSTPART): ot_v41_segtree5 (same events, same
// adds, same next-state expressions) whose reset input is the RAW reset source rst_pin (the column's landed reset copy,
// a register on the same free clock).  The 241 asynchronous resets the caller's single synchroniser drove are split over
// kept same-edge synchroniser copies (ot_v41_rst_copy): u_rc -> the control (sv / x_v / y_v / add_v / queue pointers /
// ov / oerr / fault), the adder is ot_v41_fadd_rp (its own two copies), and one copy per TWO trees -> those trees' have / herr / in-flight state (2 x
// (LV + LV + IW) = 28 resets).  have / herr / infl become per-tree registers with the identical next-state expressions.
// Every copy is the same register function as the synchroniser it replaces (d = 1, async clear from the same source,
// same clock), so every reset releases on the same edge.  Only valid on the free-running clock (OT_BF_TILE_FREECLK).
module ot_v41_segtree5_rp #(
    parameter integer NT = 4,
    parameter integer LV = 5,
    parameter integer QD = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    parameter integer EARLY = 0      // 1: a final node with nothing held above it and nothing of its tree in the
                                     //    adder leaves at once instead of being promoted (+0) level by level
) (
    input  wire                     clk,
    input  wire                     rst_pin,
    input  wire                     in_v,
    input  wire [$clog2(NT)-1:0]    in_tree,
    input  wire [2:0]               in_pos,     // position (MTP) of the tree's nodes; leaves with its value
    input  wire [31:0]              in_val,
    input  wire                     in_final,
    input  wire                     in_err,
    output reg                      ov,
    output reg  [$clog2(NT)-1:0]    otree,
    output reg  [2:0]               opos,
    output reg  [31:0]              oval,
    output reg                      oerr,
    output reg                      fault
);
    localparam integer PW = $clog2(NT);
    localparam integer LW = $clog2(LV + 1);
    localparam integer QW = $clog2(QD);
    localparam integer NP = (NT + 1) / 2;   // tree pairs (one reset copy each)
    // FOREP (S81-C199-FANOUT 2026-10-19, opt-in OT_BF_FOREP, default off = unchanged): kept same-edge register copies and
    // registered one-hot decodes so no flop drives > ~32 loads.  (1) sv: kept copies per consumer slice (e_d 4 x 8 bits,
    // the tree one-hot halves, the level decodes) -- the original keeps the control.  (2) the event's slot one-hot e_oh /
    // e_above formed from REGISTERED decodes (tree one-hot of st and of the queue head h_t, level one-hot / above-mask of
    // st), loaded on the same edges as st / h_t, so st's tree / level bits no longer fan out over the 2 x NH compares.
    // (3) the same-slot forward compare y == x registered one stage earlier as e == x (xy_eq).  (4) y_v / y_f / y_e: one
    // kept copy per tree pair for that pair's 2*LV slot terms and per-tree inc/dec (y_v copies reset by the pair's reset
    // copy, the same register function).  (5) y_fw: 3 kept copies, one per ~11 bits of u_held.  (6) x_oh: a kept copy
    // x_ohd for the high half of the held-operand read.  Every copy loads the same d on the same clock: zero cycles.
    wire rst_n;
    ot_v41_rst_copy u_rc (.clk(clk), .rst_pin(rst_pin), .rst_n(rst_n));
    // base-node queue
    reg [31:0] qv [0:QD-1];
    reg [PW-1:0] qt [0:QD-1];
    reg qf [0:QD-1], qe [0:QD-1];
    reg [2:0] qp [0:QD-1];
    reg [2:0] tpos [0:NT-1];
    reg [QW-1:0] qr, qw;
    reg [QW:0] qc;
    // held left operands
    reg [31:0] held [0:NT*LV-1];
    wire [NT*LV-1:0] have, herr;     // per-tree registers (g_tr below)
    // adder result (event at level + 1), registered once before it is an event (1.2 GHz: the event decision and
    // the held-operand write no longer follow the adder's output stage in the same cycle)
    wire [31:0] sum_a;
    wire [1:0] err_a;
    wire sv_a;
    wire [PW+LW+1:0] st_a;
    reg  [31:0] sum;
    reg  [1:0] err;
    reg  sv;
    reg  [PW+LW+1:0] st;     // {tree, level, final, err}
    always @(posedge clk or negedge rst_n) if (!rst_n) sv <= 1'b0; else sv <= sv_a;
    always @(posedge clk) begin sum <= sum_a; err <= err_a; st <= st_a; end
`ifdef OT_BF_FOREP
    (* keep *) reg [3:0] sv_d;       // e_d bytes
    (* keep *) reg [1:0] sv_t;       // e_toh halves
    (* keep *) reg       sv_l;       // e_t / e_l / e_loh / e_lab
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sv_d <= '0; sv_t <= '0; sv_l <= 1'b0; end
        else begin sv_d <= {4{sv_a}}; sv_t <= {2{sv_a}}; sv_l <= sv_a; end
    // registered decodes of st's tree / level (same edge as st)
    reg [NT-1:0] st_toh;
    reg [LV-1:0] st_loh, st_lab;
    integer di;
    always @(posedge clk) begin
        for (di = 0; di < NT; di = di + 1) st_toh[di] <= st_a[PW+LW+1 -: PW] == di;
        for (di = 0; di < LV; di = di + 1) begin
            st_loh[di] <= di == st_a[LW+1 -: LW];
            st_lab[di] <= di > st_a[LW+1 -: LW];
        end
    end
`endif
    // STAGE 1 -- the event considered this cycle: adder result first, else the queue head.  It is registered
    // (x_*) with its held-operand index decoded one-hot and the mask of its tree's levels above it, so the
    // decision stage below is a few AND-OR levels over registers (1.2 GHz at SS).  An event spends one cycle in
    // each stage; the decision stage reads and writes the held operands in the same cycle, so consecutive
    // events of one tree see each other's updates.
    wire use_q = !sv && qc != 0;
    reg [31:0] h_v;
    reg [PW-1:0] h_t;
    reg h_f, h_e;
    reg [2:0] h_p;
    wire        e_v = sv || qc != 0;
`ifdef OT_BF_FOREP
    wire [PW-1:0] e_t = sv_l ? st[PW+LW+1 -: PW] : h_t;
    wire [LW-1:0] e_l = sv_l ? st[LW+1 -: LW] : {LW{1'b0}};
`else
    wire [PW-1:0] e_t = sv ? st[PW+LW+1 -: PW] : h_t;
    wire [LW-1:0] e_l = sv ? st[LW+1 -: LW] : {LW{1'b0}};
`endif
    wire        e_f = sv ? st[1] : h_f;
    wire        e_e = sv ? (st[0] | err != 2'd0) : h_e;
`ifdef OT_BF_FOREP
    wire [31:0] e_d = {sv_d[3] ? sum[31:24] : h_v[31:24], sv_d[2] ? sum[23:16] : h_v[23:16],
                       sv_d[1] ? sum[15:8] : h_v[15:8], sv_d[0] ? sum[7:0] : h_v[7:0]};
`else
    wire [31:0] e_d = sv ? sum : h_v;
`endif
    localparam integer NH = NT * LV;
    reg [NH-1:0] e_oh, e_above;
    integer li, ti, hi;
`ifdef OT_BF_FOREP
    reg [NT-1:0] h_toh;                    // registered tree one-hot of the queue head (same edge as h_t)
    reg [NT-1:0] e_toh;
    reg [LV-1:0] e_loh, e_lab;
    always @* begin
        for (ti = 0; ti < NT; ti = ti + 1) e_toh[ti] = sv_t[(ti * 2) / NT] ? st_toh[ti] : h_toh[ti];
        // a queue node is a base node: level 0, every level above it
        for (li = 0; li < LV; li = li + 1) begin
            e_loh[li] = sv_l ? st_loh[li] : (li == 0);
            e_lab[li] = sv_l ? st_lab[li] : (li > 0);
        end
        for (hi = 0; hi < NH; hi = hi + 1) begin
            e_oh[hi] = e_toh[hi / LV] & e_loh[hi % LV];
            e_above[hi] = e_toh[hi / LV] & e_lab[hi % LV];
        end
    end
`else
    always @* begin
        e_oh = '0; e_above = '0;
        for (hi = 0; hi < NH; hi = hi + 1) begin
            if (hi / LV == e_t && hi % LV == e_l) e_oh[hi] = 1'b1;
            if (hi / LV == e_t && hi % LV > e_l) e_above[hi] = 1'b1;
        end
    end
`endif
    reg          x_v, x_f, x_e, x_add;
    reg [PW-1:0] x_t;
    reg [LW-1:0] x_l;
    reg [31:0]   x_d;
    reg [NH-1:0] x_oh, x_above;
    reg [NT-1:0] x_toh;
    reg [2:0]    x_pos;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= e_v;
`ifdef OT_BF_FOREP
    (* keep *) reg [NH-1:0] x_ohd;       // kept copy of x_oh for the high half of the held read
    reg xy_eq;                           // (e_t, e_l) == (x_t, x_l): next cycle's (x == y) of the forward
    always @(posedge clk) begin
        x_t <= e_t; x_l <= e_l; x_f <= e_f; x_e <= e_e; x_d <= e_d; x_add <= sv;
        x_oh <= e_oh; x_above <= e_above; x_ohd <= e_oh;
        x_toh <= e_toh;
        x_pos <= use_q ? h_p : tpos[e_t];
        xy_eq <= e_t == x_t && e_l == x_l;
    end
`else
    always @(posedge clk) begin
        x_t <= e_t; x_l <= e_l; x_f <= e_f; x_e <= e_e; x_d <= e_d; x_add <= sv;
        x_oh <= e_oh; x_above <= e_above;
        for (ti = 0; ti < NT; ti = ti + 1) x_toh[ti] <= e_t == ti;
        x_pos <= use_q ? h_p : tpos[e_t];
    end
`endif
    // STAGE 2a (x1) -- read into group partials (see the header)
    localparam integer IW = $clog2(LAT + 5);
    localparam integer NG = 4;
    localparam integer GS = (NH + NG - 1) / NG;
    wire [IW-1:0] infl [0:NT-1];     // per-tree registers (g_tr below)
    reg          y_v, y_f, y_e, y_add;
    reg [PW-1:0] y_t;
    reg [LW-1:0] y_l;
    reg [31:0]   y_d;
    reg [NH-1:0] y_oh, y_above;
    reg [NT-1:0] y_toh;
    reg [2:0]    y_pos;
    reg [NG-1:0] y_hv, y_ab, y_he;
    reg [32*NG-1:0] y_hd;
    reg          y_fw, y_fe;
    reg [31:0]   y_fd;
    reg [IW-1:0] y_infl;
`ifdef OT_BF_FOREP
    wire [NP-1:0] y_vg;                         // per tree pair kept copies of y_v (g_yv below)
    (* keep *) reg [NP-1:0] y_fg, y_eg;         // per tree pair copies of y_f / y_e
    (* keep *) reg [2:0]    y_fwc;              // copies of y_fw, one per ~11 bits of u_held
`endif
    // STAGE 2b (x2) -- decide from registers
    wire y_have = |y_hv;
    wire above = |y_ab;
    wire idle_tree = y_infl == (y_add ? {{(IW-1){1'b0}}, 1'b1} : {IW{1'b0}});
    wire early = (EARLY != 0) && y_v && y_f && !y_have && !above && idle_tree;
    wire top = y_l == LV[LW-1:0] || early;
    wire pair = y_v && !top && y_have;
    wire promote = y_v && !top && !y_have && y_f;
    wire hold = y_v && !top && !y_have && !y_f;
    reg [31:0] u_held;
    reg        u_herr;
    always @* begin
        u_held = 32'd0;
        for (int g = 0; g < NG; g++) u_held = u_held | y_hd[32*g +: 32];
`ifdef OT_BF_FOREP
        for (int b = 0; b < 32; b++) if (y_fwc[(b * 3) / 32]) u_held[b] = y_fd[b];
`else
        if (y_fw) u_held = y_fd;
`endif
        u_herr = y_fw ? y_fe : |y_he;
    end
    // segtree3's local forms on the x2 event (have / infl are current here)
    reg [NT-1:0] t_inc, t_dec;
    reg [NH-1:0] s_hold, s_pair;
    integer tj;
    reg hv_t, ab_t, id_t, ea_t, tp_t;
    always @* begin
        for (tj = 0; tj < NT; tj = tj + 1) begin
            hv_t = |(have[tj*LV +: LV] & y_oh[tj*LV +: LV]);
            ab_t = |(have[tj*LV +: LV] & y_above[tj*LV +: LV]);
            id_t = infl[tj] == (y_add ? {{(IW-1){1'b0}}, 1'b1} : {IW{1'b0}});
`ifdef OT_BF_FOREP
            ea_t = (EARLY != 0) && y_fg[tj / 2] && !hv_t && !ab_t && id_t;
            tp_t = y_l == LV[LW-1:0] || ea_t;
            t_inc[tj] = y_vg[tj / 2] && y_toh[tj] && !tp_t && (hv_t || y_fg[tj / 2]);
            t_dec[tj] = y_vg[tj / 2] && y_toh[tj] && y_add;
`else
            ea_t = (EARLY != 0) && y_f && !hv_t && !ab_t && id_t;
            tp_t = y_l == LV[LW-1:0] || ea_t;
            t_inc[tj] = y_v && y_toh[tj] && !tp_t && (hv_t || y_f);
            t_dec[tj] = y_v && y_toh[tj] && y_add;
`endif
        end
        for (tj = 0; tj < NH; tj = tj + 1) begin
`ifdef OT_BF_FOREP
`ifdef QP_MUTANT_TREE
            s_hold[tj] = y_vg[tj / (2 * LV)] && y_oh[tj] && !y_fg[tj / (2 * LV)];   // negative control: ignores the held bit
`else
            s_hold[tj] = y_vg[tj / (2 * LV)] && y_oh[tj] && !have[tj] && !y_fg[tj / (2 * LV)];
`endif
            s_pair[tj] = y_vg[tj / (2 * LV)] && y_oh[tj] && have[tj];
`else
`ifdef QP_MUTANT_TREE
            s_hold[tj] = y_v && y_oh[tj] && !y_f;                         // negative control: ignores the held bit
`else
            s_hold[tj] = y_v && y_oh[tj] && !have[tj] && !y_f;
`endif
            s_pair[tj] = y_v && y_oh[tj] && have[tj];
`endif
        end
    end
    // x1 reads (next state for have / above / infl; held / herr read now, the x2 event's same-slot hold forwarded)
    wire [NH-1:0] have_nx = (have & ~s_pair) | s_hold;
    reg  [NG-1:0] r_hv, r_ab, r_he;
    reg  [32*NG-1:0] r_hd;
    reg  [IW-1:0] r_infl;
    integer gi;
    always @* begin
        r_hv = '0; r_ab = '0; r_he = '0; r_hd = '0; r_infl = '0;
        for (gi = 0; gi < NH; gi = gi + 1) begin
            r_hv[gi / GS] = r_hv[gi / GS] | (have_nx[gi] & x_oh[gi]);
            r_ab[gi / GS] = r_ab[gi / GS] | (have_nx[gi] & x_above[gi]);
            r_he[gi / GS] = r_he[gi / GS] | (herr[gi] & x_oh[gi]);
`ifdef OT_BF_FOREP
            if (x_oh[gi])  r_hd[32*(gi / GS) +: 16] = r_hd[32*(gi / GS) +: 16] | held[gi][15:0];
            if (x_ohd[gi]) r_hd[32*(gi / GS) + 16 +: 16] = r_hd[32*(gi / GS) + 16 +: 16] | held[gi][31:16];
`else
            if (x_oh[gi]) r_hd[32*(gi / GS) +: 32] = r_hd[32*(gi / GS) +: 32] | held[gi];
`endif
        end
        for (gi = 0; gi < NT; gi = gi + 1)
            if (x_toh[gi]) r_infl = r_infl | (infl[gi] + (t_inc[gi] ? 1'b1 : 1'b0) - (t_dec[gi] ? 1'b1 : 1'b0));
    end
`ifdef ST_MUTANT_FW
    wire r_fw = 1'b0;                                                   // negative control: no same-slot forward
`elsif OT_BF_FOREP
    wire r_fw = hold && xy_eq;                                          // xy_eq == (y_t == x_t && y_l == x_l)
`else
    wire r_fw = hold && y_t == x_t && y_l == x_l;
`endif
    always @(posedge clk or negedge rst_n) if (!rst_n) y_v <= 1'b0; else y_v <= x_v;
    always @(posedge clk) begin
        y_t <= x_t; y_l <= x_l; y_f <= x_f; y_e <= x_e; y_d <= x_d; y_add <= x_add;
        y_oh <= x_oh; y_above <= x_above; y_toh <= x_toh; y_pos <= x_pos;
        y_hv <= r_hv; y_ab <= r_ab; y_he <= r_he; y_hd <= r_hd; y_infl <= r_infl;
        y_fw <= r_fw; y_fd <= y_d; y_fe <= y_e;
`ifdef OT_BF_FOREP
        y_fwc <= {3{r_fw}}; y_fg <= {NP{x_f}}; y_eg <= {NP{x_e}};
`endif
    end
    // kept copies of the x2 operand for the held writes, one per slot group
    wire [31:0] y_dc [0:NG-1];
    for (genvar g = 0; g < NG; g = g + 1) begin : g_dc
        ot_v41_kreg #(.W(32)) u_d (.clk(clk), .arst_n(1'b1), .d(x_d), .q(y_dc[g]));
    end
    wire [PW-1:0] out_t = y_t;
    reg [31:0] add_a, add_b;
    reg        add_v;
    always @(posedge clk) begin
        add_a <= pair ? u_held : y_d;
        add_b <= pair ? y_d : 32'd0;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) add_v <= 1'b0; else add_v <= pair | promote;
    ot_v41_fadd_rp #(.CUT(CUT)) u_add (.clk(clk), .rst_pin(rst_pin), .valid_in(add_v), .a(add_a), .b(add_b),
                                     .y(sum_a), .err(err_a), .valid_out(sv_a));
    ot_hdc_delay #(.W(PW + LW + 2), .D(LAT + 1)) u_t (.clk(clk), .rst_n(rst_n),
        .d({y_t, y_l + 1'b1, y_f, y_e | (pair && u_herr)}), .q(st_a));
    // per-tree state: tree t's have / herr slots and in-flight count, reset by the copy of its tree pair
    wire [(NT+1)/2-1:0] rst_t;
    for (genvar tp = 0; tp < (NT + 1) / 2; tp = tp + 1) begin : g_rt
`ifdef OT_BF_RSTPART_MUT_TREE
        ot_v41_rst_copy u_r (.clk(clk), .rst_pin(tp == 3 ? 1'b0 : rst_pin), .rst_n(rst_t[tp]));   // negative control: trees 6-7 held in reset
`else
        ot_v41_rst_copy u_r (.clk(clk), .rst_pin(rst_pin), .rst_n(rst_t[tp]));
`endif
    end
`ifdef OT_BF_FOREP
    // y_v copies, one per tree pair, reset by that pair's reset copy (the same register function as y_v)
    for (genvar vp = 0; vp < NP; vp = vp + 1) begin : g_yv
        (* keep *) reg q;
        always @(posedge clk or negedge rst_t[vp])
`ifdef OT_BF_FOREP_MUT_TREE
            if (!rst_t[vp]) q <= 1'b0; else q <= (vp == 0) ? 1'b0 : x_v;   // negative control: pair 0's copy stuck
`else
            if (!rst_t[vp]) q <= 1'b0; else q <= x_v;
`endif
        assign y_vg[vp] = q;
    end
    wire [NH-1:0] herr_nx;
    for (genvar hx = 0; hx < NH; hx = hx + 1) begin : g_hx
        assign herr_nx[hx] = (herr[hx] & ~s_hold[hx]) | (y_eg[hx / (2 * LV)] & s_hold[hx]);
    end
`else
    wire [NH-1:0] herr_nx = (herr & ~s_hold) | (y_e ? s_hold : '0);
`endif
    for (genvar tt = 0; tt < NT; tt = tt + 1) begin : g_tr
        reg [LV-1:0] hv_q, he_q;
        reg [IW-1:0] in_q;
        always @(posedge clk or negedge rst_t[tt / 2])
            if (!rst_t[tt / 2]) begin
                hv_q <= '0; he_q <= '0; in_q <= '0;
            end else begin
                hv_q <= have_nx[tt*LV +: LV];
                he_q <= herr_nx[tt*LV +: LV];
                in_q <= in_q + (t_inc[tt] ? 1'b1 : 1'b0) - (t_dec[tt] ? 1'b1 : 1'b0);
            end
        assign have[tt*LV +: LV] = hv_q;
        assign herr[tt*LV +: LV] = he_q;
        assign infl[tt] = in_q;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qw <= 0; qc <= 0; ov <= 1'b0; oerr <= 1'b0; fault <= 1'b0;
        end else begin
            if (in_v) qw <= qw + 1'b1;
            if (use_q) qr <= qr + 1'b1;
            qc <= qc + (in_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (in_v && qc == QD && !use_q) fault <= 1'b1;
            if (y_v && y_l == LV[LW-1:0] && !y_f) fault <= 1'b1;    // more base nodes than 2^LV: not the root
            ov <= y_v && top;
            oerr <= y_v && top && y_e;
        end
    end
    always @(posedge clk) begin
        if (in_v) begin qv[qw] <= in_val; qt[qw] <= in_tree; qf[qw] <= in_final; qe[qw] <= in_err; qp[qw] <= in_pos; end
        if (use_q) tpos[h_t] <= h_p;
        opos <= y_pos;
        if (qr + (use_q ? 1'b1 : 1'b0) == qw) begin      // the head-to-be is the node arriving now (if any)
            h_v <= in_val; h_t <= in_tree; h_f <= in_final; h_e <= in_err; h_p <= in_pos;
`ifdef OT_BF_FOREP
            for (ti = 0; ti < NT; ti = ti + 1) h_toh[ti] <= in_tree == ti;
`endif
        end else begin
            h_v <= qv[qr + (use_q ? 1'b1 : 1'b0)]; h_t <= qt[qr + (use_q ? 1'b1 : 1'b0)];
            h_f <= qf[qr + (use_q ? 1'b1 : 1'b0)]; h_e <= qe[qr + (use_q ? 1'b1 : 1'b0)];
            h_p <= qp[qr + (use_q ? 1'b1 : 1'b0)];
`ifdef OT_BF_FOREP
            for (ti = 0; ti < NT; ti = ti + 1) h_toh[ti] <= qt[qr + (use_q ? 1'b1 : 1'b0)] == ti;
`endif
        end
        for (hi = 0; hi < NH; hi = hi + 1) if (s_hold[hi]) held[hi] <= y_dc[hi / GS];
        oval <= y_d;
        otree <= y_t;
    end
`ifdef QP_CHECK
    // the x1 partials against the direct reductions at x2, and the local forms against the global decision
    reg [31:0] c_held; reg c_herr;
    always @* begin
        c_held = 32'd0; c_herr = 1'b0;
        for (int h = 0; h < NH; h++) if (y_oh[h]) begin c_held = c_held | held[h]; c_herr = c_herr | herr[h]; end
    end
    always @(negedge clk) if (rst_n && y_v) begin
        if (y_have !== |(have & y_oh) || above !== |(have & y_above) || y_infl !== infl[y_t])
            begin $display("QP_CHECK FAIL segtree5 x1 read %m %t", $time); $fatal(1); end
        if (pair && (u_held !== c_held || u_herr !== c_herr))
            begin $display("QP_CHECK FAIL segtree5 held read %m %t", $time); $fatal(1); end
        if (s_hold !== (hold ? y_oh : {NH{1'b0}})) begin $display("QP_CHECK FAIL segtree hold %m %t", $time); $fatal(1); end
        if (s_pair !== (pair ? y_oh : {NH{1'b0}})) begin $display("QP_CHECK FAIL segtree pair %m %t", $time); $fatal(1); end
        for (int t = 0; t < NT; t++)
            if (t_inc[t] !== ((pair | promote) && y_t == t)) begin $display("QP_CHECK FAIL segtree inc %m %t", $time); $fatal(1); end
    end
`endif
endmodule
