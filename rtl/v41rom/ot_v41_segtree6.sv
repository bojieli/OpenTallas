`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_segtree6: ot_v41_segtree5 for the margin-first q-element (QM >= 2, owner rule 2026-10-06: +60 ps planned SS
// slack at 0.833 ns).  Two changes, same events / adds / order per tree, so every output value and every per-tree
// output order is segtree5's; output TIMES are one cycle later per tree level:
//   (1) adder-operand stage (+1 cycle a level): the x2 decision (pair / promote) and both operand candidates (the held
//       left operand, the event's value) are registered (z_*), and the 64-bit adder-operand select is driven by NZ
//       kept copies of the registered pair bit, each selecting 64 / NZ bits (Z20c: y_hv -> pair -> 30-load select ->
//       add_a +11.6 ps; add_b +32.5 ps).  The in-flight count still counts the event from its decision to its result.
//   (2) queue head without the pointer compare: "the head-to-be is the node arriving now" (qr + use_q == qw) is
//       (qc == use_q) || (qc == QD && !use_q), formed from registered count flags (qc == 0 / 1 / QD) held in NQ kept
//       copies, each driving a slice of the head registers; the next-entry read uses a registered qr + 1 (Z20c:
//       qc -> XNOR -> 30-load -> h_v +9.4 ps; h_e / h_t / h_p / h_f +27..49 ps).  Zero cycles.
// QP_CHECK additionally asserts the flag form against the pointer compare every cycle.
// ---------------------------------------------------------------------------
// Original header (ot_v41_segtree5):
// ot_v41_segtree5: ot_v41_segtree3 with the decide stage split in two (DS-V4.1 ROM q-pair SS closure, owner decision
// 2026-10-05: structural fix with priced extra cycles, after routes Z12 / Z13b / Z14 failed on the 80-slot held
// select (x_oh -> held[] -> add_a) and the 80-slot write fan-out (x_d -> held[]) at -35 to -44 ps).
//   x1 (read): per group of GS = NH / NG slots, the selected slot's held operand, error, have and above bits are
//       OR-reduced into registers (NG partials each); have / above / in-flight are taken from the NEXT state, i.e.
//       with the x2 event's update of this cycle applied, and a same-slot hold by the x2 event this cycle is
//       forwarded (its operand and error) instead of the stale held[] read.
//   x2 (decide): pair / promote / hold / top from those registers (an NG-input OR each), the held / have / herr /
//       in-flight updates in segtree3's slot-local / tree-local forms (have and infl are current at x2), the adder
//       operands, the outputs; the held writes take kept copies of the operand, one per slot group.
// Every event spends one cycle in each of e, x1, x2, so a tree level costs LAT + 4 cycles (segtree3: LAT + 3).
// Same events, same adds, same order per tree, so every output value is segtree3's; output TIMES differ (later,
// data-dependent).  QP_CHECK asserts every x1 partial against the direct reduction at x2, every cycle.
// ---------------------------------------------------------------------------
module ot_v41_segtree6 #(
    parameter integer NT = 4,
    parameter integer LV = 5,
    parameter integer QD = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    parameter integer EARLY = 0      // 1: a final node with nothing held above it and nothing of its tree in the
                                     //    adder leaves at once instead of being promoted (+0) level by level
) (
    input  wire                     clk,
    input  wire                     rst_n,
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
    reg [NT*LV-1:0] have, herr;
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
    // (2) registered count flags {qc == 0, qc == 1, qc == QD} and qr + 1, NQ kept copies of the flags (one per 8-bit
    // slice of the head value; copy 0 also loads the head's tree / final / error / position)
    localparam integer NQ = 4;
    reg  [QW-1:0] qr1;
    wire [QW:0]   qc_nx = qc + (in_v ? 1'b1 : 1'b0) - ((!sv && qc != 0) ? 1'b1 : 1'b0);
    wire [2:0]    fl_nx = {qc_nx == QD, qc_nx == 1, qc_nx == 0};
    wire [2:0]    fl [0:NQ-1];
    wire [NQ-1:0] svc;
    for (genvar g = 0; g < NQ; g = g + 1) begin : g_fl
        ot_v41_kreg #(.W(3), .AR(1), .RV(3'b001)) u_f (.clk(clk), .arst_n(rst_n), .d(fl_nx), .q(fl[g]));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_s (.clk(clk), .arst_n(rst_n), .d(sv_a), .q(svc[g]));
    end
    reg [NQ-1:0] uq, byp;
    always @* for (int c = 0; c < NQ; c++) begin
        uq[c]  = !svc[c] && !fl[c][0];                                       // use_q
        byp[c] = fl[c][0] || (fl[c][1] && !svc[c]) || (fl[c][2] && svc[c]);  // qr + use_q == qw
    end
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
    wire [PW-1:0] e_t = sv ? st[PW+LW+1 -: PW] : h_t;
    wire [LW-1:0] e_l = sv ? st[LW+1 -: LW] : {LW{1'b0}};
    wire        e_f = sv ? st[1] : h_f;
    wire        e_e = sv ? (st[0] | err != 2'd0) : h_e;
    wire [31:0] e_d = sv ? sum : h_v;
    localparam integer NH = NT * LV;
    reg [NH-1:0] e_oh, e_above;
    integer li, ti, hi;
    always @* begin
        e_oh = '0; e_above = '0;
        for (hi = 0; hi < NH; hi = hi + 1) begin
            if (hi / LV == e_t && hi % LV == e_l) e_oh[hi] = 1'b1;
            if (hi / LV == e_t && hi % LV > e_l) e_above[hi] = 1'b1;
        end
    end
    reg          x_v, x_f, x_e, x_add;
    reg [PW-1:0] x_t;
    reg [LW-1:0] x_l;
    reg [31:0]   x_d;
    reg [NH-1:0] x_oh, x_above;
    reg [NT-1:0] x_toh;
    reg [2:0]    x_pos;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= e_v;
    always @(posedge clk) begin
        x_t <= e_t; x_l <= e_l; x_f <= e_f; x_e <= e_e; x_d <= e_d; x_add <= sv;
        x_oh <= e_oh; x_above <= e_above;
        for (ti = 0; ti < NT; ti = ti + 1) x_toh[ti] <= e_t == ti;
        x_pos <= use_q ? h_p : tpos[e_t];
    end
    // STAGE 2a (x1) -- read into group partials (see the header)
    localparam integer IW = $clog2(LAT + 6);
    localparam integer NG = 4;
    localparam integer GS = (NH + NG - 1) / NG;
    reg [IW-1:0] infl [0:NT-1];
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
        if (y_fw) u_held = y_fd;
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
            ea_t = (EARLY != 0) && y_f && !hv_t && !ab_t && id_t;
            tp_t = y_l == LV[LW-1:0] || ea_t;
            t_inc[tj] = y_v && y_toh[tj] && !tp_t && (hv_t || y_f);
            t_dec[tj] = y_v && y_toh[tj] && y_add;
        end
        for (tj = 0; tj < NH; tj = tj + 1) begin
`ifdef QP_MUTANT_TREE
            s_hold[tj] = y_v && y_oh[tj] && !y_f;                         // negative control: ignores the held bit
`else
            s_hold[tj] = y_v && y_oh[tj] && !have[tj] && !y_f;
`endif
            s_pair[tj] = y_v && y_oh[tj] && have[tj];
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
            if (x_oh[gi]) r_hd[32*(gi / GS) +: 32] = r_hd[32*(gi / GS) +: 32] | held[gi];
        end
        for (gi = 0; gi < NT; gi = gi + 1)
            if (x_toh[gi]) r_infl = r_infl | (infl[gi] + (t_inc[gi] ? 1'b1 : 1'b0) - (t_dec[gi] ? 1'b1 : 1'b0));
    end
`ifdef ST_MUTANT_FW
    wire r_fw = 1'b0;                                                   // negative control: no same-slot forward
`else
    wire r_fw = hold && y_t == x_t && y_l == x_l;
`endif
    always @(posedge clk or negedge rst_n) if (!rst_n) y_v <= 1'b0; else y_v <= x_v;
    always @(posedge clk) begin
        y_t <= x_t; y_l <= x_l; y_f <= x_f; y_e <= x_e; y_d <= x_d; y_add <= x_add;
        y_oh <= x_oh; y_above <= x_above; y_toh <= x_toh; y_pos <= x_pos;
        y_hv <= r_hv; y_ab <= r_ab; y_he <= r_he; y_hd <= r_hd; y_infl <= r_infl;
        y_fw <= r_fw; y_fd <= y_d; y_fe <= y_e;
    end
    // kept copies of the x2 operand for the held writes, one per slot group
    wire [31:0] y_dc [0:NG-1];
    for (genvar g = 0; g < NG; g = g + 1) begin : g_dc
        ot_v41_kreg #(.W(32)) u_d (.clk(clk), .arst_n(1'b1), .d(x_d), .q(y_dc[g]));
    end
    wire [PW-1:0] out_t = y_t;
    // (1) adder-operand stage: decision and candidates registered, the select from NZ kept copies of z_pair
    localparam integer NZ = 4;
    reg [31:0] z_h, z_d;
    reg        z_v;
    always @(posedge clk) begin z_h <= u_held; z_d <= y_d; end
    always @(posedge clk or negedge rst_n) if (!rst_n) z_v <= 1'b0; else z_v <= pair | promote;
    wire [NZ-1:0] z_pair;
    for (genvar g = 0; g < NZ; g = g + 1) begin : g_zp
`ifdef ST6_MUTANT_Z
        ot_v41_kreg #(.W(1)) u_p (.clk(clk), .arst_n(1'b1), .d(g == 1 ? promote : pair), .q(z_pair[g]));   // negative control
`else
        ot_v41_kreg #(.W(1)) u_p (.clk(clk), .arst_n(1'b1), .d(pair), .q(z_pair[g]));
`endif
    end
    reg [31:0] add_a, add_b;
    reg        add_v;
    always @(posedge clk) begin
        for (int b = 0; b < 32; b++) begin
            add_a[b] <= z_pair[b / (32 / (NZ / 2))] ? z_h[b] : z_d[b];
            add_b[b] <= z_pair[NZ / 2 + b / (32 / (NZ / 2))] ? z_d[b] : 1'b0;
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) add_v <= 1'b0; else add_v <= z_v;
    ot_v41_fadd #(.CUT(CUT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(add_v), .a(add_a), .b(add_b),
                                     .y(sum_a), .err(err_a), .valid_out(sv_a));
    ot_hdc_delay #(.W(PW + LW + 2), .D(LAT + 2)) u_t (.clk(clk), .rst_n(rst_n),
        .d({y_t, y_l + 1'b1, y_f, y_e | (pair && u_herr)}), .q(st_a));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qr1 <= 1; qw <= 0; qc <= 0; have <= '0; herr <= '0; ov <= 1'b0; oerr <= 1'b0; fault <= 1'b0;
            for (ti = 0; ti < NT; ti = ti + 1) infl[ti] <= '0;
        end else begin
            if (in_v) qw <= qw + 1'b1;
            if (use_q) begin qr <= qr + 1'b1; qr1 <= qr1 + 1'b1; end
            qc <= qc + (in_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (in_v && qc == QD && !use_q) fault <= 1'b1;
            if (y_v && y_l == LV[LW-1:0] && !y_f) fault <= 1'b1;    // more base nodes than 2^LV: not the root
            for (ti = 0; ti < NT; ti = ti + 1)
                infl[ti] <= infl[ti] + (t_inc[ti] ? 1'b1 : 1'b0) - (t_dec[ti] ? 1'b1 : 1'b0);
            have <= have_nx;
            herr <= (herr & ~s_hold) | (y_e ? s_hold : '0);
            ov <= y_v && top;
            oerr <= y_v && top && y_e;
        end
    end
    always @(posedge clk) begin
        if (in_v) begin qv[qw] <= in_val; qt[qw] <= in_tree; qf[qw] <= in_final; qe[qw] <= in_err; qp[qw] <= in_pos; end
        if (use_q) tpos[h_t] <= h_p;
        opos <= y_pos;
        for (int c = 0; c < NQ; c++) begin           // (2) slice c of the head registers on flag copy c
            if (byp[c]) begin
                for (int b = c * 8; b < c * 8 + 8; b++) h_v[b] <= in_val[b];
                if (c == 0) begin h_t <= in_tree; h_f <= in_final; h_e <= in_err; h_p <= in_pos; end
            end else begin
`ifdef ST6_MUTANT_Q
                for (int b = c * 8; b < c * 8 + 8; b++) h_v[b] <= qv[qr][b];   // negative control: the pop's advance ignored
`else
                for (int b = c * 8; b < c * 8 + 8; b++) h_v[b] <= uq[c] ? qv[qr1][b] : qv[qr][b];
`endif
                if (c == 0) begin
                    h_t <= uq[c] ? qt[qr1] : qt[qr]; h_f <= uq[c] ? qf[qr1] : qf[qr];
                    h_e <= uq[c] ? qe[qr1] : qe[qr]; h_p <= uq[c] ? qp[qr1] : qp[qr];
                end
            end
        end
        for (hi = 0; hi < NH; hi = hi + 1) if (s_hold[hi]) held[hi] <= y_dc[hi / GS];
        oval <= y_d;
        otree <= y_t;
    end
`ifdef QP_CHECK
    always @(negedge clk) if (rst_n) for (int c = 0; c < NQ; c++)
        if (byp[c] !== (qr + (use_q ? 1'b1 : 1'b0) == qw) || uq[c] !== use_q || qr1 !== qr + 1'b1)
            begin $display("QP_CHECK FAIL segtree6 head flags %m %t", $time); $fatal(1); end
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
