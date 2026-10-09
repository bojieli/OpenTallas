`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SM record adapter (hgi-adapters, 2026-10-09).  Unit 1 (SM.MATVEC) of the normative sequencer dispatch
// (ot_hgi_seq v1.0: d_hdr, effective d_desc A / B / O, d_n) onto the EXISTING per-SM command ports of the die's 32 SM
// elements (ot_hbm_accel_smh / sm_v: start / start_ready, op_rows, op_c, op_g, op_gs, op_fmt, op_xb, d_valid / d_ready,
// d_base, d_lines, arrive / release_in, fault: the die's control_leaf W_CTL + W_DESC buses).  Decode + handshake only.
//
// SM LAYOUT RULE (spec 10.3 item "SM layout rule", pinned here for the adapter; max rows per SM = ceil(M / 32) as the
// even split, so the latency is the same): the weight operand B (HBM, row-major: row r at B.base + r * B.stride, K =
// B's effective n elements, M = B.m rows) is cut into 32 CONTIGUOUS row blocks of Q = ceil(M / 32) rows: SM s takes
// rows [s Q, min((s + 1) Q, M)) (none if s Q >= M).  Per SM s with rows R_s > 0:
//   op_fmt = param[1:0] (0 BF16, 1 FP8 block-dot, 2 FP4 block-dot, 3 INT8: the smh encoding, B.fmt must agree);
//   op_c = 8 (IL k-steps a group), op_g = ceil(K / (8 W)), W = weights a line-lane group (BF16 64 x 8 = 512 K a group,
//   FP8 1,024, FP4 2,048, INT8 512: tools/dshbm_matched_sm_seq.gen_op Gn), so a row is LPR = 8 op_g lines (INT8: 4 op_g,
//   one line = two BF16 beats of codes); op_gs = 1 (group-slot issue); op_rows = R_s; op_xb = 0 (single-buffered x);
//   d_base / d_lines in LINE units (the native SM descriptor: dshbm_expert_workgroup_descriptor d_base_unit = line):
//   line bytes LB = 136 (the 1,088-b DS line) or 160 (the INT8 transport line), B.stride must be LPR x LB (rows dense
//   in lines) and B.base a multiple of LB; line0 = B.base / LB (iterative divide, 2 bits an edge, under the x load);
//   d_base = line0 + s Q LPR, d_lines = R_s LPR.
// Positions (G18, hbm-forks: no SM port): P = param[4:2] + 1 slots ride the NC = 8 independent x columns; the x load
//   carries P rows of A, the result publication takes the first P columns.  A.m and O.m must equal P when P > 1.
// Service ports (peers on the die, decode-level handshakes): x load (A from VM / STREAM into every active SM's x store
//   at fragment 0: {A base, K, P, A.stride, A.space, fmt}) and result publication (O: {O base, O.stride, O.space, M, Q,
//   P}); both are issued at decode; the SMs start only after x_done (the x store must hold the fragment before start).
// Retire: every active SM's arrive toggled AND pub_done (the unit's real completion); then the adapter releases the
//   SMs (release_in := arrive: the record is the barrier).  Any SM fault, x / pub fault, or decode refusal retires the
//   record with rec_fault and halts (sticky until rst_n).
// Refusals: unit != 1 / op != 0; A, B or O absent; B not HBM, A / O not VM / STREAM; B.fmt != param fmt; B inner
//   stride not 1 or ibcast; K != effective n of A; K or M = 0; FP8 / FP4 K not a multiple of 32; op_g > 255; Q > 4095;
//   P > 1 with A.m or O.m != P; B.stride != LPR x LB; B.base not a multiple of LB (the divide's remainder, fault at E21).
// Latency: accept E0, decode E1 (x load + publication issued), products by radix-16 iterative Horner E2-E6, per-SM
//   fields E7-E9; the SMs start at max(E10, x_done + 1).  The x load of K elements takes >= ceil(K / 64) beats, so the
//   added edges on the record path are the 2 of the station (E0, E1) whenever K >= 512.
// DS lockstep identity: hgi_en = 0 (static strap) connects the legacy per-SM buses straight to the SM ports, no flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_record #(
    parameter integer NSM = 32,
    parameter integer MUT_ROWS = 0,       // mutant: an even floor split (M >> 5 rows a SM) instead of the ceil blocks
    parameter integer MUT_EARLY = 0,      // mutant: retire when the SMs start
    parameter integer LEGACY = 1          // 1: static legacy pass-through mux; 0: the routed adapter (records only)
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               hgi_en,
    // record (unit 1)
    input  wire               rec_v,
    output wire               rec_rdy,
    input  wire [127:0]       rec_hdr,
    input  wire [255:0]       rec_a, rec_b, rec_o,
    input  wire [20:0]        rec_n_a, rec_n_b,
    output reg                rec_done,
    output reg                rec_fault,
    output wire               halted,
    // x load (to the VM / STREAM x multicast root)
    output reg                x_v,
    input  wire               x_rdy,
    output reg  [39:0]        x_base,
    output reg  [20:0]        x_n,
    output reg  [3:0]         x_p,
    output reg  [31:0]        x_stride,
    output reg  [1:0]         x_space,
    output reg  [1:0]         x_fmt,
    input  wire               x_done,
    input  wire               x_fault,
    // result publication (to O)
    output reg                pub_v,
    input  wire               pub_rdy,
    output reg  [39:0]        pub_base,
    output reg  [31:0]        pub_stride,
    output reg  [1:0]         pub_space,
    output reg  [19:0]        pub_m,
    output reg  [12:0]        pub_q,
    output reg  [3:0]         pub_p,
    input  wire               pub_done,
    input  wire               pub_fault,
    // legacy per-SM buses (DS control path): {release_in, d_lines 24, d_base 32, d_valid, op_xb 7, op_fmt 2, op_gs,
    // op_g 8, op_c 16, op_rows 13, start} = 106 b a SM; returns {fault, arrive, d_ready, start_ready} = 4 b a SM
    input  wire [NSM*106-1:0] lg_cmd,
    output wire [NSM*4-1:0]   lg_ret,
    // SM element ports
    output wire [NSM*106-1:0] sm_cmd,
    input  wire [NSM*4-1:0]   sm_ret
);
    localparam integer CW = 106;
    // ---- registered reset: rst_n lands in a 2-flop synchroniser; every flop below resets from rst_i (recovery from
    //      one flop, the GX7 RSTR pattern; the die's reset release is multicycle)
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rst_i = rs[1];
    // ---- station
    reg          raw_v, dec_ok, busy, halt_q, s1_v, rdy_r;
    reg  [127:0] hdr_q;
    reg  [255:0] a_q, b_q, o_q;
    reg  [20:0]  na_q, nb_q;
    reg  [NSM*4-1:0] ret_q;
    always @(posedge clk) ret_q <= sm_ret;
    reg in_xd, in_xf, in_pd, in_pf;
    always @(posedge clk) begin in_xd <= x_done; in_xf <= x_fault; in_pd <= pub_done; in_pf <= pub_fault; end
    assign halted = halt_q;
    wire   hen = LEGACY ? hgi_en : 1'b1;
    assign rec_rdy = hen && rdy_r;                          // registered (busy -> rec_rdy was a reg -> out path)

    // ---- decode, two edges: E1 copies the pin flops into the stage-1 registers with the count-derived fields
    //      (g, Q, LPR, LB) and the header checks; E2 completes the checks (stride product) and starts the record
    reg  [127:0] h1; reg [255:0] a1, b1, o1; reg [20:0] na1, nb1; reg [7:0] g1; reg [15:0] q1; reg [10:0] lpr1;
    reg  [7:0] lb1; reg bad1;
    wire [6:0]  opnd = hdr_q[99:93];
    wire [1:0]  pf = hdr_q[65:64];
    wire [3:0]  pp = {1'b0, hdr_q[68:66]} + 4'd1;
    wire [1:0]  pf1 = h1[65:64];
    wire [3:0]  pp1 = {1'b0, h1[68:66]} + 4'd1;
    wire [2:0]  bfmt = b_q[4:2];
    wire [2:0]  want = (pf == 2'd0) ? 3'd1 : (pf == 2'd1) ? 3'd2 : (pf == 2'd2) ? 3'd3 : 3'd4;
    wire [3:0]  lw8 = (pf == 2'd1) ? 4'd10 : (pf == 2'd2) ? 4'd11 : 4'd9;        // log2(8 W)
    wire [7:0]  lby = (pf == 2'd3) ? 8'd160 : 8'd136;                              // line bytes
    wire [10:0] lpr_d = (pf == 2'd3) ? {1'b0, g_full[7:0], 2'b00} : {g_full[7:0], 3'b000};
    wire [20:0] km1 = nb_q - 21'd1;
    wire [20:0] g_full = (km1 >> lw8) + 21'd1;                                       // ceil(K / 8W)
    wire [19:0] mm = b_q[87:68];
    localparam integer LNSM = $clog2(NSM);                                         // NSM a power of two
    wire [15:0] q_full = MUT_ROWS ? (mm >> LNSM) : (mm + NSM - 1) >> LNSM;           // Q = ceil(M / NSM)
    wire bad0 = (hdr_q[127:124] != 4'd1) || (hdr_q[123:118] != 6'd0) || !opnd[0] || !opnd[1] || !opnd[4] ||
               (b_q[1:0] != 2'd0) || (a_q[1:0] != 2'd1 && a_q[1:0] != 2'd2) || (o_q[1:0] != 2'd1 && o_q[1:0] != 2'd2) ||
               (bfmt != want) || b_q[5] || (b_q[135:120] > 16'd1) || (na_q != nb_q) || (nb_q == 21'd0) ||
               (mm == 20'd0) || (g_full > 21'd255) || (q_full > 16'd4095) ||
               ((pf == 2'd1 || pf == 2'd2) && (|nb_q[4:0])) ||
               (pp > 4'd1 && (a_q[87:68] != {16'd0, pp} || o_q[87:68] != {16'd0, pp}));
    wire bad = bad1 || (b1[119:88] != {13'd0, lpr1} * {24'd0, lb1});          // E2

    // ---- products: QS = Q * B.stride, LQ = Q * LPR, ML = M * LPR (radix-16 iterative Horner, 5 digits, E2-E6)
    reg  [19:0] q_r; reg [7:0] g_r; reg [10:0] lpr_r; reg [19:0] m_r; reg [39:0] base_r; reg [31:0] str_r;
    reg  [1:0]  fmt_r;
    reg  [7:0]  lby_r; reg [39:0] dv_n, dv_q; reg [8:0] dv_r; reg [5:0] dv_k; reg dv_chk;    // line0 = B.base / LB (radix 4)
    reg  [44:0] qs; reg [23:0] lq; reg [30:0] ml;
    reg  [2:0]  dig;                     // radix-16 digits left (5: Q and M are <= 20 b)
    reg         prod_v, pd_seen;
    // per-SM fields (2 register stages)
    reg  [NSM*45-1:0] sqs; reg [NSM*31-1:0] slq; reg [NSM*17-1:0] sq;
    reg  [NSM-1:0]    act;
    reg  [NSM*13-1:0] rows_s; reg [NSM*32-1:0] dbase_s; reg [NSM*24-1:0] dl_s;
    reg  [19:0] q_sh, m_sh;
    reg  [1:0]  fld_ph; reg fb; reg [NSM*20-1:0] rdf; reg [NSM*31-1:0] ldf;
    reg         go_ok, xs_done, started, pub_sent, x_sent;
    reg  [NSM-1:0] st_pend, d_pend, arr_want, arr_seen;
    reg  [NSM-1:0] rel;                  // release_in a SM (the adapter echoes arrive at retire)
    integer s;
    // ---- outputs: per-SM command words
    // registered command words (one flop a bit per SM: no reg -> out fanout); start / d_valid are the pend bits of the
    // next state, and a handshake completes on the REGISTERED start / d_valid with the SM's ready
    reg [NSM*CW-1:0] cmd_h;
    reg [NSM-1:0] st_n, d_n;
    always @* begin
        for (s = 0; s < NSM; s = s + 1) begin
            st_n[s] = st_pend[s] && !(cmd_h[s*CW] && sm_ret[s*4 + 0]);
            d_n[s]  = d_pend[s] && !(cmd_h[s*CW + 48] && sm_ret[s*4 + 1]);
        end
    end
    integer s2;
    always @(posedge clk)                                    // datapath flops: no reset tree (start / d_valid are gated
        for (s2 = 0; s2 < NSM; s2 = s2 + 1)                  //  by the registered reset rst_i, synchronously)
            cmd_h[s2*CW +: CW] <= {rel[s2], dl_s[s2*24 +: 24], dbase_s[s2*32 +: 32], d_n[s2] & go_ok & rst_i, 7'd0,
                                   fmt_r, 1'b1, g_r, 16'd8, rows_s[s2*13 +: 13], st_n[s2] & go_ok & rst_i};
    assign sm_cmd = hen ? cmd_h : lg_cmd;
    assign lg_ret = hen ? {NSM*4{1'b0}} : sm_ret;

    reg all_arr;
    always @* begin
        all_arr = 1'b1;
        for (s = 0; s < NSM; s = s + 1) if (arr_want[s] && !arr_seen[s]) all_arr = 1'b0;
    end
    reg any_fault;
    always @* begin
        any_fault = 1'b0;
        for (s = 0; s < NSM; s = s + 1) if (act[s] && ret_q[s*4 + 3]) any_fault = 1'b1;
    end

    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            fb <= 1'b0; raw_v <= 1'b0; s1_v <= 1'b0; rdy_r <= 1'b0; bad1 <= 1'b0; busy <= 1'b0; halt_q <= 1'b0; dv_chk <= 1'b0; dv_k <= 6'd0; rec_done <= 1'b0; rec_fault <= 1'b0; prod_v <= 1'b0;
            x_v <= 1'b0; pub_v <= 1'b0; go_ok <= 1'b0; xs_done <= 1'b0; started <= 1'b0; pub_sent <= 1'b0;
            x_sent <= 1'b0; st_pend <= 0; d_pend <= 0; arr_want <= 0; arr_seen <= 0; rel <= 0; act <= 0; fld_ph <= 0;
            dig <= 0; hdr_q <= 0; a_q <= 0; b_q <= 0; o_q <= 0; na_q <= 0; nb_q <= 0; dec_ok <= 1'b0;
            rows_s <= 0; dbase_s <= 0; dl_s <= 0; g_r <= 0; fmt_r <= 0;
            x_base <= 0; x_n <= 0; x_p <= 0; x_stride <= 0; x_space <= 0; x_fmt <= 0;
            pub_base <= 0; pub_stride <= 0; pub_space <= 0; pub_m <= 0; pub_q <= 0; pub_p <= 0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0;
            hdr_q <= rec_hdr; a_q <= rec_a; b_q <= rec_b; o_q <= rec_o; na_q <= rec_n_a; nb_q <= rec_n_b;   // pin flops
            if (rec_v && rec_rdy) raw_v <= 1'b1;
            rdy_r <= hen && !raw_v && !s1_v && !busy && !halt_q && !(rec_v && rec_rdy);
            // E1: copy the pin flops, count-derived fields, header checks
            if (raw_v) begin
                raw_v <= 1'b0; s1_v <= 1'b1; h1 <= hdr_q; a1 <= a_q; b1 <= b_q; o1 <= o_q; na1 <= na_q; nb1 <= nb_q;
                g1 <= g_full[7:0]; q1 <= q_full; lpr1 <= lpr_d; lb1 <= lby; bad1 <= bad0;
            end
            // E2: the stride check, then issue the x load + publication and start the products
            if (s1_v) begin
                s1_v <= 1'b0;
                if (bad) begin rec_fault <= 1'b1; halt_q <= 1'b1; end
                else begin
                    busy <= 1'b1; xs_done <= 1'b0; started <= 1'b0; go_ok <= 1'b0; fld_ph <= 2'd0;
                    q_r <= {4'd0, q1}; q_sh <= {4'd0, q1}; m_sh <= b1[87:68]; g_r <= g1; lpr_r <= lpr1; lby_r <= lb1; dv_n <= b1[47:8]; dv_q <= 40'd0; dv_r <= 9'd0; dv_k <= 6'd20; dv_chk <= 1'b1; m_r <= b1[87:68];
                    base_r <= b1[47:8]; str_r <= b1[119:88]; fmt_r <= pf1;
                    qs <= 45'd0; lq <= 24'd0; ml <= 31'd0; dig <= 3'd5; prod_v <= 1'b0; pd_seen <= 1'b0;
                    x_v <= 1'b1; x_base <= a1[47:8]; x_n <= na1; x_p <= pp1; x_stride <= a1[119:88];
                    x_space <= a1[1:0]; x_fmt <= pf1;
                    pub_v <= 1'b1; pub_base <= o1[47:8]; pub_stride <= o1[119:88]; pub_space <= o1[1:0]; pub_m <= b1[87:68];
                    pub_q <= q1[12:0]; pub_p <= pp1;
                    arr_seen <= 0; arr_want <= 0; st_pend <= 0; d_pend <= 0;
                end
            end
            if (x_v && x_rdy) x_v <= 1'b0;
            if (pub_v && pub_rdy) pub_v <= 1'b0;
            // products: Q is 13 b = 4 radix-16 digits, high digit first; M * LPR by 5 digits of M
            if (busy && dig != 3'd0) begin
                dig <= dig - 3'd1;
                qs <= (qs << 4) + str_r * q_sh[19:16];           // top digit of a shifting copy: no indexed select
                lq <= (lq << 4) + lpr_r * q_sh[19:16];
                ml <= (ml << 4) + lpr_r * m_sh[19:16];
                q_sh <= q_sh << 4; m_sh <= m_sh << 4;
                if (dig == 3'd1) prod_v <= 1'b1;
            end
            if (busy && in_pd) pd_seen <= 1'b1;
            if (busy && dv_k != 6'd0) begin                        // restoring divide, 2 quotient bits an edge
                dv_k <= dv_k - 6'd1;
                begin : g_div
                    reg [9:0] r1, r2; reg q1, q2;
                    r1 = {dv_r[8:0], dv_n[39]}; q1 = (r1 >= {2'd0, lby_r}); if (q1) r1 = r1 - {2'd0, lby_r};
                    r2 = {r1[8:0], dv_n[38]};   q2 = (r2 >= {2'd0, lby_r}); if (q2) r2 = r2 - {2'd0, lby_r};
                    dv_r <= r2[8:0]; dv_n <= dv_n << 2; dv_q <= {dv_q[37:0], q1, q2};
                end
            end
            if (prod_v && fld_ph == 2'd0 && dv_k == 6'd0) begin
                for (s = 0; s < NSM; s = s + 1) begin
                    sqs[s*45 +: 45] <= qs * s;
                    slq[s*31 +: 31] <= {7'd0, lq} * s;
                    sq[s*17 +: 17] <= q_r[16:0] * s;
                end
                fld_ph <= 2'd1;
            end
            if (fld_ph == 2'd1 && !fb) begin                    // per-SM fields, stage A: the differences
                for (s = 0; s < NSM; s = s + 1) begin
                    act[s] <= ({3'd0, m_r} > {3'd0, sq[s*17 +: 17]});
                    rdf[s*20 +: 20] <= m_r - sq[s*17 +: 17];
                    ldf[s*31 +: 31] <= ml - slq[s*31 +: 31];
                    dbase_s[s*32 +: 32] <= dv_q[31:0] + {1'b0, slq[s*31 +: 31]};
                end
                fb <= 1'b1;
            end
            if (fld_ph == 2'd1 && fb) begin                     // stage B: clamp to Q / Q LPR
                for (s = 0; s < NSM; s = s + 1) begin
                    rows_s[s*13 +: 13] <= act[s] ? ((rdf[s*20 +: 20] > q_r) ? q_r[12:0] : rdf[s*20 +: 13]) : 13'd0;
                    dl_s[s*24 +: 24] <= act[s] ? ((ldf[s*31 +: 31] > {7'd0, lq}) ? lq : ldf[s*31 +: 24]) : 24'd0;
                end
                fb <= 1'b0; fld_ph <= 2'd2;
            end
            if (fld_ph == 2'd2) begin
                fld_ph <= 2'd3; st_pend <= act; d_pend <= act; arr_want <= act;
            end
            if (busy && in_xd) xs_done <= 1'b1;
            if (fld_ph == 2'd3 && xs_done && !started) begin go_ok <= 1'b1; started <= 1'b1;
                if (MUT_EARLY) begin rec_done <= 1'b1; busy <= 1'b0; fld_ph <= 2'd0; prod_v <= 1'b0; end
            end
            if (go_ok) begin
                for (s = 0; s < NSM; s = s + 1) begin
                    if (st_pend[s] && cmd_h[s*CW] && sm_ret[s*4 + 0]) st_pend[s] <= 1'b0;
                    if (d_pend[s] && cmd_h[s*CW + 48] && sm_ret[s*4 + 1]) d_pend[s] <= 1'b0;
                    if (arr_want[s] && ret_q[s*4 + 2] != rel[s]) arr_seen[s] <= 1'b1;
                end
                if (st_pend == 0 && d_pend == 0) go_ok <= 1'b0;
            end else if (started) begin
                for (s = 0; s < NSM; s = s + 1)
                    if (arr_want[s] && ret_q[s*4 + 2] != rel[s]) arr_seen[s] <= 1'b1;
            end
            if (busy && dv_chk && dv_k == 6'd0 && dv_r != 9'd0) begin            // B.base not a multiple of LB
                rec_fault <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; go_ok <= 1'b0; dv_chk <= 1'b0;
            end else if (busy && (any_fault || in_xf || in_pf)) begin
                rec_fault <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; go_ok <= 1'b0;
            end else if (busy && started && !go_ok && all_arr && pd_seen && st_pend == 0 && d_pend == 0) begin
                rec_done <= 1'b1; busy <= 1'b0; fld_ph <= 2'd0; prod_v <= 1'b0; started <= 1'b0;
                for (s = 0; s < NSM; s = s + 1) if (arr_want[s]) rel[s] <= ret_q[s*4 + 2];
                arr_want <= 0; act <= 0;
            end
        end
    end
endmodule
`default_nettype wire
