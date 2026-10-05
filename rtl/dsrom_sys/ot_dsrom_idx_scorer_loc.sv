`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Index-scorer LOCATION for the DeepSeek-V4.1 ROM data-loading path
// (coordinator decision 2026-10-03, pricing branch claude/dsrom-nearhbm-20261003
// @ 723243a4a: the 21.7 mm2 index scorer fails the S58 die-area margin in the
// hub and fits beside the HBM service strips; attention stays in the hub).
//
// The golden's selection (tools/hdc_golden_v41.py topk_lowest_index and
// Model.index_select: `sorted(topk_lowest_index(s, min(topk, n)))`) is the k
// largest BF16 scores, ties to the LOWER position, returned in ascending
// position order.  That is a strict total order
//     a before b  <=>  key(a) > key(b)  or  (key(a) == key(b) and pos(a) < pos(b))
// with key = the score as a number (+0 == -0; -inf allowed).  For any strict
// total order the global top-k is contained in the union of every shard's
// local top-k, and equals the top-k of that union -- so scoring per HBM stack
// and merging is exact (class A) whatever the sharding.  NaN (absent from the
// golden's scores, max(score, 0) * w with finite w) is ordered last, as numpy's
// lexsort places it.
//
//   ot_dsrom_idx_stack_topk  one scorer's selector: streams (score, pos) of its
//                            shard, keeps the local top-K in rank order (insertion
//                            list), sends it to the hub in rank order, receives
//                            the global threshold, and re-emits its members of the
//                            global selection in ascending position order;
//   ot_dsrom_idx_topk_merge  hub: NS-way rank merge to the K-th element (the
//                            threshold), then NS-way ascending-position merge of
//                            the stacks' re-emitted members; query identity (qid)
//                            must agree across stacks (latched fault otherwise);
//   ot_dsrom_idx_scorer_loc  IDX_SCORER_LOC = 0: one selector in the hub over all
//                            keys (the stacks' key streams are serialised into it
//                            one key a cycle); 1: one selector per HBM stack beside
//                            its service strip, each scoring its own shard in
//                            parallel, merged in the hub.  Same output interface.
// ---------------------------------------------------------------------------
module ot_dsrom_idx_stack_topk #(
    parameter integer K  = 16,
    parameter integer PW = 20,
    parameter integer QW = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,          // new query: clears the list
    input  wire [QW-1:0] qid,
    input  wire          in_v,
    input  wire [15:0]   in_score,       // BF16
    input  wire [PW-1:0] in_pos,
    input  wire          in_last,        // last key of this shard (an empty shard sends in_last with in_v=0)
    // rank-order list to the hub
    output wire          rk_v,
    input  wire          rk_ready,
    output wire [16:0]   rk_key,
    output wire [PW-1:0] rk_pos,
    output wire          rk_last,        // last (or only marker when empty: rk_empty)
    output wire          rk_empty,
    output wire [QW-1:0] rk_qid,
    // global threshold from the hub (all = fewer than K keys in total: everything selected)
    input  wire          thr_v,
    input  wire          thr_all,
    input  wire [16:0]   thr_key,
    input  wire [PW-1:0] thr_pos,
    // members of the global selection, ascending position
    output wire          ps_v,
    input  wire          ps_ready,
    output wire [PW-1:0] ps_pos,
    output wire          ps_last,
    output wire          ps_empty,
    output wire [QW-1:0] ps_qid
);
    localparam integer CB = $clog2(K + 1);
    function automatic [16:0] okey(input [15:0] b);
        reg [15:0] c;
        begin
            c = (b == 16'h8000) ? 16'h0000 : b;                       // -0 == +0
            if (c[14:7] == 8'hFF && c[6:0] != 0) okey = 17'd0;        // NaN last
            else okey = {1'b1, c[15] ? ~c : {1'b1, c[14:0]}};
        end
    endfunction
    function automatic prec(input [16:0] ka, input [PW-1:0] pa, input [16:0] kb, input [PW-1:0] pb);
        `ifdef DSROM_IDX_MUTANT_TIE
        prec = (ka > kb) || (ka == kb && pa > pb);
        `else
        prec = (ka > kb) || (ka == kb && pa < pb);
        `endif
    endfunction

    reg [16:0]   lk [0:K-1];
    reg [PW-1:0] lp [0:K-1];
    reg [CB-1:0] n;
    reg [PW-1:0] sp [0:K-1];           // position-ordered members
    reg [CB-1:0] sn;
    reg [QW-1:0] q;
    localparam [2:0] S_IN = 0, S_RK = 1, S_THR = 2, S_SEL = 3, S_PS = 4, S_IDLE = 5;
    reg [2:0] st;
    reg [CB-1:0] ri, si, pi;
    reg rk_mark, ps_mark;               // empty-list marker sent
    wire [16:0] nk = okey(in_score);

    // rank stream
    assign rk_v     = (st == S_RK) && (ri < n || (n == 0 && !rk_mark));
    assign rk_key   = lk[ri];
    assign rk_pos   = lp[ri];
    assign rk_empty = (n == 0);
    assign rk_last  = (n == 0) || (ri == n - 1);
    assign rk_qid   = q;
    // position stream
    assign ps_v     = (st == S_PS) && (pi < sn || (sn == 0 && !ps_mark));
    assign ps_pos   = sp[pi];
    assign ps_empty = (sn == 0);
    assign ps_last  = (sn == 0) || (pi == sn - 1);
    assign ps_qid   = q;

    integer j;
    reg [CB-1:0] at;
    reg sel_i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; n <= 0; sn <= 0; ri <= 0; si <= 0; pi <= 0; q <= 0; rk_mark <= 0; ps_mark <= 0;
        end else if (start) begin
            st <= S_IN; n <= 0; sn <= 0; ri <= 0; si <= 0; pi <= 0; q <= qid; rk_mark <= 0; ps_mark <= 0;
        end else case (st)
            S_IN: begin
                if (in_v) begin
                    at = 0;
                    for (j = 0; j < K; j = j + 1)
                        if (j < n && prec(lk[j], lp[j], nk, in_pos)) at = at + 1;
                    if (at < K) begin
                        for (j = K - 1; j > 0; j = j - 1)
                            if (j > at) begin lk[j] <= lk[j-1]; lp[j] <= lp[j-1]; end
                        lk[at] <= nk; lp[at] <= in_pos;
                        if (n < K) n <= n + 1'b1;
                    end
                end
                if (in_last) st <= S_RK;
            end
            // the hub may close the threshold before this stack's whole list was read
            S_RK: if (thr_v) begin st <= S_SEL; si <= 0; end
                  else if (rk_v && rk_ready) begin
                if (n == 0) begin rk_mark <= 1'b1; st <= S_THR; end
                else begin ri <= ri + 1'b1; if (ri == n - 1) st <= S_THR; end
            end
            S_THR: if (thr_v) begin st <= S_SEL; si <= 0; end
            S_SEL: begin
                // one local member a cycle into the position-ordered list
                if (si < n) begin
                    sel_i = thr_all || !prec(thr_key, thr_pos, lk[si], lp[si]);   // lk[si] at or before thr
                    if (sel_i) begin
                        at = 0;
                        for (j = 0; j < K; j = j + 1) if (j < sn && sp[j] < lp[si]) at = at + 1;
                        for (j = K - 1; j > 0; j = j - 1) if (j > at) sp[j] <= sp[j-1];
                        sp[at] <= lp[si];
                        sn <= sn + 1'b1;
                        si <= si + 1'b1;
                    end else si <= n;                 // rank order: everything after is worse
                end else begin st <= S_PS; pi <= 0; end
            end
            S_PS: if (ps_v && ps_ready) begin
                if (sn == 0) begin ps_mark <= 1'b1; st <= S_IDLE; end
                else begin pi <= pi + 1'b1; if (pi == sn - 1) st <= S_IDLE; end
            end
            default: ;
        endcase
    end
endmodule

module ot_dsrom_idx_topk_merge #(
    parameter integer NS = 4,
    parameter integer K  = 16,
    parameter integer PW = 20,
    parameter integer QW = 8
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             start,
    input  wire [QW-1:0]    qid,
    input  wire [NS-1:0]    rk_v,
    output reg  [NS-1:0]    rk_ready,
    input  wire [NS*17-1:0] rk_key,
    input  wire [NS*PW-1:0] rk_pos,
    input  wire [NS-1:0]    rk_last,
    input  wire [NS-1:0]    rk_empty,
    input  wire [NS*QW-1:0] rk_qid,
    output reg              thr_v,
    output reg              thr_all,
    output reg  [16:0]      thr_key,
    output reg  [PW-1:0]    thr_pos,
    input  wire [NS-1:0]    ps_v,
    output reg  [NS-1:0]    ps_ready,
    input  wire [NS*PW-1:0] ps_pos,
    input  wire [NS-1:0]    ps_last,
    input  wire [NS-1:0]    ps_empty,
    input  wire [NS*QW-1:0] ps_qid,
    output reg              sel_v,
    input  wire             sel_ready,
    output reg  [PW-1:0]    sel_pos,
    output reg              sel_last,
    output reg              fault,
    output reg  [31:0]      st_cycles       // start -> last selected id accepted
);
    localparam integer CB = $clog2(K + 1);
    function automatic prec(input [16:0] ka, input [PW-1:0] pa, input [16:0] kb, input [PW-1:0] pb);
        prec = (ka > kb) || (ka == kb && pa < pb);
    endfunction
    localparam [2:0] M_IDLE = 0, M_RK = 1, M_THR = 2, M_PS = 3, M_DONE = 4;
    reg [2:0] st;
    reg [NS-1:0] rdone, pdone;
    reg [CB-1:0] taken;
    reg [QW-1:0] q;
    reg [PW-1:0] last_out;
    reg first_out;
    integer s, b;
    reg found;
    always @(*) begin
        rk_ready = 0; ps_ready = 0; b = 0; found = 1'b0;
        if (st == M_RK) begin
            for (s = 0; s < NS; s = s + 1)
                if (!rdone[s] && rk_v[s] && rk_empty[s]) begin rk_ready[s] = 1'b1; end
            // only merge when every not-done stack has its head valid (rank order across stacks)
            if (rk_ready == 0) begin
                found = 1'b1;
                for (s = 0; s < NS; s = s + 1) if (!rdone[s] && !rk_v[s]) found = 1'b0;
                if (found && rdone != {NS{1'b1}}) begin
                    b = -1;
                    for (s = 0; s < NS; s = s + 1)
                        if (!rdone[s] && (b < 0 || prec(rk_key[s*17 +: 17], rk_pos[s*PW +: PW],
                                                            rk_key[b*17 +: 17], rk_pos[b*PW +: PW]))) b = s;
                    if (b >= 0) rk_ready[b] = 1'b1;
                end
            end
        end else if (st == M_PS && (!sel_v || sel_ready)) begin
            for (s = 0; s < NS; s = s + 1)
                if (!pdone[s] && ps_v[s] && ps_empty[s]) ps_ready[s] = 1'b1;
            if (ps_ready == 0) begin
                found = 1'b1;
                for (s = 0; s < NS; s = s + 1) if (!pdone[s] && !ps_v[s]) found = 1'b0;
                if (found && pdone != {NS{1'b1}}) begin
                    b = -1;
                    for (s = 0; s < NS; s = s + 1)
                        if (!pdone[s] && (b < 0 || ps_pos[s*PW +: PW] < ps_pos[b*PW +: PW])) b = s;
                    if (b >= 0) ps_ready[b] = 1'b1;
                end
            end
        end
    end
    integer t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= M_IDLE; rdone <= 0; pdone <= 0; taken <= 0; q <= 0; thr_v <= 0; thr_all <= 0; thr_key <= 0;
            thr_pos <= 0; sel_v <= 0; sel_pos <= 0; sel_last <= 0; fault <= 0; st_cycles <= 0; first_out <= 1;
            last_out <= 0;
        end else begin
            if (st != M_IDLE && st != M_DONE) st_cycles <= st_cycles + 1;
            if (sel_v && sel_ready) begin
                sel_v <= 1'b0;
                if (sel_last) st <= M_DONE;
            end
            if (start) begin
                st <= M_RK; rdone <= 0; pdone <= 0; taken <= 0; q <= qid; thr_v <= 0; thr_all <= 0;
                st_cycles <= 0; first_out <= 1; sel_v <= 0;
            end else case (st)
                M_RK: begin
                    for (t = 0; t < NS; t = t + 1) if (rk_ready[t]) begin
                        if (rk_qid[t*QW +: QW] != q) fault <= 1'b1;
                        if (rk_last[t]) rdone[t] <= 1'b1;
                    end
                    if (|(rk_ready & ~rk_empty)) begin
                        taken <= taken + 1'b1;
                        if (taken == K - 1) begin
                            thr_key <= rk_key[b*17 +: 17]; thr_pos <= rk_pos[b*PW +: PW];
                            thr_v <= 1'b1; thr_all <= 1'b0; st <= M_THR;
                        end
                    end
                    if (!(|(rk_ready & ~rk_empty) && taken == K - 1) &&
                        (rdone | (rk_ready & rk_last)) == {NS{1'b1}}) begin
                        thr_v <= 1'b1; thr_all <= 1'b1; st <= M_THR;   // K or fewer keys in total
                    end
                end
                M_THR: begin st <= M_PS; end      // stacks drain their remaining rank entries below
                M_PS: begin
                    for (t = 0; t < NS; t = t + 1) if (ps_ready[t]) begin
                        if (ps_qid[t*QW +: QW] != q) fault <= 1'b1;
                        if (ps_last[t]) pdone[t] <= 1'b1;
                        if (!ps_empty[t]) begin
                            if (!first_out && ps_pos[t*PW +: PW] <= last_out) fault <= 1'b1;
                            first_out <= 1'b0; last_out <= ps_pos[t*PW +: PW];
                            sel_v <= 1'b1; sel_pos <= ps_pos[t*PW +: PW];
                            sel_last <= ((pdone | (ps_ready & ps_last)) == {NS{1'b1}});
                        end else if ((pdone | (ps_ready & ps_last)) == {NS{1'b1}}) begin
                            // the final stream to finish was empty: mark the last emitted id by a
                            // zero-length close (sel_last on an already-sent id is not possible), so
                            // empty stacks are ordered first by the empty-marker priority above
                            st <= M_DONE;
                        end
                    end
                end
                default: ;
            endcase
        end
    end
endmodule

module ot_dsrom_idx_scorer_loc #(
    parameter integer IDX_SCORER_LOC = 0,   // 0 hub, 1 per-HBM-stack shoreline
    parameter integer NS = 4,
    parameter integer K  = 16,
    parameter integer PW = 20,
    parameter integer QW = 8
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             start,
    input  wire [QW-1:0]    qid,
    // NS key streams, one per HBM stack shard (score, position)
    input  wire [NS-1:0]    k_v,
    output wire [NS-1:0]    k_ready,
    input  wire [NS*16-1:0] k_score,
    input  wire [NS*PW-1:0] k_pos,
    input  wire [NS-1:0]    k_last,         // per shard; an empty shard asserts k_last with k_v = 0
    output wire             sel_v,
    input  wire             sel_ready,
    output wire [PW-1:0]    sel_pos,
    output wire             sel_last,
    output wire             fault,
    output wire [31:0]      st_cycles
);
    localparam integer NSEL = IDX_SCORER_LOC ? NS : 1;
    wire [NSEL-1:0] rk_v, rk_r, rk_l, rk_e, ps_v, ps_r, ps_l, ps_e;
    wire [NSEL*17-1:0] rk_k; wire [NSEL*PW-1:0] rk_p, ps_p; wire [NSEL*QW-1:0] rk_q, ps_q;
    wire thr_v, thr_all; wire [16:0] thr_k; wire [PW-1:0] thr_p;
    // the merge starts one cycle after the selectors so its state is clean when ranks arrive
    genvar g;
    generate if (IDX_SCORER_LOC) begin : g_stack
        assign k_ready = {NS{1'b1}};
        for (g = 0; g < NS; g = g + 1) begin : g_s
            ot_dsrom_idx_stack_topk #(.K(K), .PW(PW), .QW(QW)) u_sel (
                .clk(clk), .rst_n(rst_n), .start(start), .qid(qid),
                .in_v(k_v[g]), .in_score(k_score[g*16 +: 16]), .in_pos(k_pos[g*PW +: PW]), .in_last(k_last[g]),
                .rk_v(rk_v[g]), .rk_ready(rk_r[g]), .rk_key(rk_k[g*17 +: 17]), .rk_pos(rk_p[g*PW +: PW]),
                .rk_last(rk_l[g]), .rk_empty(rk_e[g]), .rk_qid(rk_q[g*QW +: QW]),
                .thr_v(thr_v), .thr_all(thr_all), .thr_key(thr_k), .thr_pos(thr_p),
                .ps_v(ps_v[g]), .ps_ready(ps_r[g]), .ps_pos(ps_p[g*PW +: PW]), .ps_last(ps_l[g]),
                .ps_empty(ps_e[g]), .ps_qid(ps_q[g*QW +: QW]));
        end
    end else begin : g_hub
        // the hub scorer takes one key a cycle: the stacks' streams are served in stack order
        reg [$clog2(NS+1)-1:0] cur;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) cur <= 0;
            else if (start) cur <= 0;
            else if (cur < NS && k_last[cur] && (k_v[cur] || 1'b1) && k_ready[cur]) cur <= cur + 1'b1;
        for (g = 0; g < NS; g = g + 1) begin : g_r
            assign k_ready[g] = (cur == g);
        end
        wire in_v = (cur < NS) && k_v[cur];
        wire in_last = (cur == NS - 1) && k_last[NS-1];
        ot_dsrom_idx_stack_topk #(.K(K), .PW(PW), .QW(QW)) u_sel (
            .clk(clk), .rst_n(rst_n), .start(start), .qid(qid),
            .in_v(in_v), .in_score(k_score[cur*16 +: 16]), .in_pos(k_pos[cur*PW +: PW]), .in_last(in_last),
            .rk_v(rk_v[0]), .rk_ready(rk_r[0]), .rk_key(rk_k), .rk_pos(rk_p), .rk_last(rk_l[0]),
            .rk_empty(rk_e[0]), .rk_qid(rk_q),
            .thr_v(thr_v), .thr_all(thr_all), .thr_key(thr_k), .thr_pos(thr_p),
            .ps_v(ps_v[0]), .ps_ready(ps_r[0]), .ps_pos(ps_p), .ps_last(ps_l[0]), .ps_empty(ps_e[0]),
            .ps_qid(ps_q));
    end endgenerate
    reg start_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) start_q <= 0; else start_q <= start;
    ot_dsrom_idx_topk_merge #(.NS(NSEL), .K(K), .PW(PW), .QW(QW)) u_merge (
        .clk(clk), .rst_n(rst_n), .start(start), .qid(qid),
        .rk_v(rk_v), .rk_ready(rk_r), .rk_key(rk_k), .rk_pos(rk_p), .rk_last(rk_l), .rk_empty(rk_e), .rk_qid(rk_q),
        .thr_v(thr_v), .thr_all(thr_all), .thr_key(thr_k), .thr_pos(thr_p),
        .ps_v(ps_v), .ps_ready(ps_r), .ps_pos(ps_p), .ps_last(ps_l), .ps_empty(ps_e), .ps_qid(ps_q),
        .sel_v(sel_v), .sel_ready(sel_ready), .sel_pos(sel_pos), .sel_last(sel_last), .fault(fault),
        .st_cycles(st_cycles));
endmodule
