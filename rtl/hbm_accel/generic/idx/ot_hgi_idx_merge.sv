`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.MERGE (proposed G20, hgi-takeover 2026-10-09; review_queue/hgi-die-gaps.md round 5 T1): the exact k-way
// merge behind COLL.TOPK_MERGE.  The program gathers every rank's local selection into VM (two exact COLL.ALL_GATHERs:
// values, ids; G runs of n), each run already sorted by the merge key (a local IDX.TOPK does that), and this engine emits
// the first k elements of the merged order -- exactly the golden lexsort (hgi_sim ds_native.topk_merge).
//
//   A  VM FP32  G rows of n values (row stride A.stride)        key 0 (param[12] = 0): larger value first, -0 = +0,
//   B  VM U32   G rows of n ids    (row stride B.stride)          NaN after every number, equal values -> lower id
//   O  VM U32   k merged ids                                    key 1 (param[12] = 1): lower id first (values ride along)
//   R  VM FP32  k merged values (optional)
//   param [11:0] k (1 .. 2,048), [12] key; G = A.m (1 .. 128).
// A run whose next element is better than the one it just gave is unsorted input: fault (fail-closed, never a silent
// wrong order).  Fewer than k elements in all runs: O / R hold all of them.
// Microarchitecture: one head {value, id} per run; a registered tournament tree (7 levels) whose path is re-evaluated
// level by level after a head changes; VM fast path: up to 4 requests outstanding, in-order responses (a head refill
// issues its value read and its id read back to back, each through its own one-sector cache; results leave through two
// sector packers as masked 8-word writes).
module ot_hgi_idx_merge #(
    parameter integer GMAX = 128,
    parameter integer MUT = 0          // bench mutant: 1 ties resolve to the HIGHER id
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [11:0]   k,
    input  wire          key_id,
    input  wire [7:0]    g,            // runs
    input  wire [19:0]   n,            // run length
    input  wire [17:0]   a_base, b_base, o_base, r_base,
    input  wire [17:0]   a_str, b_str,
    input  wire          has_r,
    output reg           done,
    output reg           fault,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr
);
    localparam integer LG = $clog2(GMAX);
    // ---------------------------------------------------------------- key order
    function automatic [31:0] okey(input [31:0] v);
        okey = (v[30:0] == 31'd0) ? 32'h8000_0000 : (v[31] ? ~v : (v | 32'h8000_0000));
    endfunction
    function automatic is_nan(input [31:0] v); is_nan = (v[30:23] == 8'hFF) && (v[22:0] != 23'd0); endfunction
    function automatic better(input av, input [31:0] a, input [31:0] ai, input bv, input [31:0] b, input [31:0] bi, input kid);
        reg lo;
        begin
            lo = (MUT == 1) ? (ai > bi) : (ai < bi);
            if (!bv) better = av;
            else if (!av) better = 1'b0;
            else if (kid) better = lo;
            else if (is_nan(a) != is_nan(b)) better = is_nan(b);
            else if (is_nan(a)) better = lo;
            else if (okey(a) != okey(b)) better = okey(a) > okey(b);
            else better = lo;
        end
    endfunction
    // ---------------------------------------------------------------- heads and tree
    reg [31:0] hv [0:GMAX-1]; reg [31:0] hi [0:GMAX-1]; reg [GMAX-1:0] hok; reg [19:0] hpos [0:GMAX-1];
    reg [LG-1:0] node [1:GMAX-1];            // node j winner (leaf index); children 2j, 2j+1; leaves GMAX .. 2 GMAX - 1
    function automatic [LG-1:0] child_win(input integer c);   // winner of child c (node or leaf)
        child_win = (c >= GMAX) ? LG'(c - GMAX) : node[c];
    endfunction
    // ---------------------------------------------------------------- VM cache, packers
    reg [2:0] ocnt; reg vq_out, iq_out; reg [14:0] vq_sec, iq_sec;
    reg cv_ok, ci_ok; reg [14:0] cv_sec, ci_sec; reg [255:0] cv_dat, ci_dat;
    wire vm_pend = ocnt != 3'd0;     // anything in flight (FLUSH waits for zero)
    reg iss;                          // a request issued this cycle
    reg [17:0] pk_a [0:1]; reg [255:0] pk_d [0:1]; reg [7:0] pk_m [0:1]; reg [14:0] pk_s [0:1]; reg [1:0] pk_full;
    // ---------------------------------------------------------------- lookahead: head + next per run
    reg [31:0] xv [0:GMAX-1]; reg [31:0] xi [0:GMAX-1]; reg [GMAX-1:0] xok;
    // fetch queue of runs that need a head / next (each run at most once in it)
    reg [7:0] fq [0:GMAX-1]; reg [LG:0] fq_h, fq_t, fq_n; reg [GMAX-1:0] inq;
    reg fe_busy; reg [7:0] fr;
    wire [17:0] fa_v = a_base + fr * a_str + hpos[fr];
    wire [17:0] fa_i = b_base + fr * b_str + hpos[fr];
    // ---------------------------------------------------------------- control
    localparam S_IDLE = 4'd0, S_INIT = 4'd1, S_WAITH = 4'd2, S_BUILD = 4'd3, S_POP = 4'd4, S_STALL = 4'd5,
               S_PATH = 4'd7, S_FLUSH = 4'd8;
    reg [3:0] st;
    reg [7:0] r;                             // init: next run to enqueue; stall: the run waiting for its head
    reg [LG:0] bj;                           // build: node index (descending)
    reg [LG-1:0] lj;                         // path: current node
    reg [11:0] nout;
    reg [31:0] pv, pi; reg [31:0] nv, ni;    // popped element; a fetched element (blocking temps)
    wire [LG-1:0] top = node[1];
    reg [LG-1:0] wl, wr; integer i;
    wire pk_ok = !pk_full[0] && !(has_r && pk_full[1]);
    reg wp_v; reg wp; reg push_q; reg [7:0] push_r;
    always @* begin wp_v = |pk_full; wp = pk_full[0] ? 1'b0 : 1'b1; end
    reg [7:0] nheads;                        // init: runs whose head has arrived
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; vmq <= 338'd0; ocnt <= 3'd0; vq_out <= 1'b0; iq_out <= 1'b0;
            cv_ok <= 1'b0; ci_ok <= 1'b0; pk_full <= 2'd0; hok <= '0; xok <= '0; inq <= '0; fe_busy <= 1'b0;
            fq_h <= '0; fq_t <= '0; fq_n <= '0; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq[337] <= 1'b0; iss = 1'b0; push_q = 1'b0;
            // responses arrive in request order; the tag says which cache (value / id) or a write echo
            if (vmr[273]) begin
                if (vmr[272:257] == 16'h0920) begin cv_ok <= 1'b1; cv_sec <= vq_sec; cv_dat <= vmr[255:0]; vq_out <= 1'b0; end
                if (vmr[272:257] == 16'h0921) begin ci_ok <= 1'b1; ci_sec <= iq_sec; ci_dat <= vmr[255:0]; iq_out <= 1'b0; end
            end
            // ---- fetch engine: fills run fr's head (when empty) then its next, one element at a time
            if (st != S_IDLE && st != S_FLUSH) begin
                if (!fe_busy) begin
                    if (fq_n != 0) begin fe_busy <= 1'b1; fr <= fq[fq_h]; fq_h <= (fq_h == GMAX - 1) ? '0 : fq_h + 1'b1; end
                end else if (cv_ok && cv_sec == fa_v[17:3] && ci_ok && ci_sec == fa_i[17:3] && !vq_out && !iq_out) begin
                    nv = cv_dat[fa_v[2:0] * 32 +: 32]; ni = ci_dat[fa_i[2:0] * 32 +: 32];
                    hpos[fr] <= hpos[fr] + 20'd1;
                    if (!hok[fr]) begin
                        hv[fr] <= nv; hi[fr] <= ni; hok[fr] <= 1'b1;
                        // a head refilled after a stall must not beat the element its run just gave
                        if (st == S_STALL && fr == r && better(1'b1, nv, ni, 1'b1, pv, pi, key_id)) begin st <= S_IDLE; fault <= 1'b1; end
                        if (st == S_INIT || st == S_WAITH) nheads <= nheads + 8'd1;
                        if (hpos[fr] + 20'd1 == n) begin fe_busy <= 1'b0; inq[fr] <= 1'b0; end   // else go on with next
                    end else begin
                        xv[fr] <= nv; xi[fr] <= ni; xok[fr] <= 1'b1;
                        // sortedness: the next may not beat the head
                        if (better(1'b1, nv, ni, 1'b1, hv[fr], hi[fr], key_id)) begin st <= S_IDLE; fault <= 1'b1; end
                        fe_busy <= 1'b0; inq[fr] <= 1'b0;
                    end
                end else if (ocnt < 3'd4 && !wp_v) begin
                    if (!(cv_ok && cv_sec == fa_v[17:3]) && !vq_out) begin
                        iss = 1'b1; vq_out <= 1'b1; vq_sec <= fa_v[17:3]; cv_ok <= 1'b0;
                        vmq <= {1'b1, 1'b0, {12'd0, fa_v[17:3], 5'd0}, 256'd0, 32'd0, 16'h0920};
                    end else if (!(ci_ok && ci_sec == fa_i[17:3]) && !iq_out) begin
                        iss = 1'b1; iq_out <= 1'b1; iq_sec <= fa_i[17:3]; ci_ok <= 1'b0;
                        vmq <= {1'b1, 1'b0, {12'd0, fa_i[17:3], 5'd0}, 256'd0, 32'd0, 16'h0921};
                    end
                end
            end
            case (st)
                S_IDLE: if (go) begin
                    if (k == 12'd0 || k > 12'd2048 || g == 8'd0 || g > GMAX || n == 20'd0) fault <= 1'b1;
                    else begin
                        st <= S_INIT; r <= 8'd0; hok <= '0; xok <= '0; inq <= '0; nout <= 12'd0; nheads <= 8'd0;
                        cv_ok <= 1'b0; ci_ok <= 1'b0; fe_busy <= 1'b0; fq_h <= '0; fq_t <= '0; fq_n <= '0;
                        for (i = 0; i < GMAX; i = i + 1) hpos[i] <= 20'd0;
                        pk_a[0] <= o_base; pk_a[1] <= r_base; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0;
                    end
                end
                // ---- enqueue every run once (head, then its next), wait for all heads
                S_INIT: begin
                    push_q = 1'b1; push_r = r;
                    if (r + 8'd1 == g) st <= S_WAITH; else r <= r + 8'd1;
                end
                S_WAITH: if (nheads == g) begin st <= S_BUILD; bj <= (LG+1)'(GMAX - 1); end
                // ---- build the tree bottom-up, one node a cycle
                S_BUILD: begin
                    wl = child_win(2 * bj); wr = child_win(2 * bj + 1);
                    node[bj] <= better(hok[wr], hv[wr], hi[wr], hok[wl], hv[wl], hi[wl], key_id) ? wr : wl;
                    if (bj == 1) st <= S_POP; else bj <= bj - 1;
                end
                // ---- re-evaluate the changed leaf's path, one level a cycle
                S_PATH: begin
                    wl = child_win(2 * lj); wr = child_win(2 * lj + 1);
                    node[lj] <= better(hok[wr], hv[wr], hi[wr], hok[wl], hv[wl], hi[wl], key_id) ? wr : wl;
                    if (lj == 1) st <= S_POP; else lj <= lj >> 1;
                end
                // ---- emit the winner; its next (already fetched) becomes its head
                S_POP: if (pk_ok) begin
                    if (!hok[top] || nout == k) st <= S_FLUSH;
                    else begin
                        pk_d[0][pk_a[0][2:0] * 32 +: 32] <= hi[top]; pk_m[0][pk_a[0][2:0]] <= 1'b1; pk_s[0] <= pk_a[0][17:3];
                        pk_a[0] <= pk_a[0] + 18'd1; if (pk_a[0][2:0] == 3'd7) pk_full[0] <= 1'b1;
                        if (has_r) begin
                            pk_d[1][pk_a[1][2:0] * 32 +: 32] <= hv[top]; pk_m[1][pk_a[1][2:0]] <= 1'b1; pk_s[1] <= pk_a[1][17:3];
                            pk_a[1] <= pk_a[1] + 18'd1; if (pk_a[1][2:0] == 3'd7) pk_full[1] <= 1'b1;
                        end
                        nout <= nout + 12'd1; pv <= hv[top]; pi <= hi[top]; r <= {{(8-LG){1'b0}}, top};
                        if (xok[top]) begin
                            hv[top] <= xv[top]; hi[top] <= xi[top]; xok[top] <= 1'b0;
                            if (hpos[top] != n && !inq[top]) begin push_q = 1'b1; push_r = {{(8-LG){1'b0}}, top}; end
                            st <= S_PATH; lj <= LG'((GMAX + top) >> 1);
                        end else if (hpos[top] == n && !(fe_busy && fr == {{(8-LG){1'b0}}, top})) begin
                            hok[top] <= 1'b0; st <= S_PATH; lj <= LG'((GMAX + top) >> 1);     // run exhausted
                        end else begin
                            hok[top] <= 1'b0; st <= S_STALL;                                   // next still in flight
                            if (!inq[top]) begin push_q = 1'b1; push_r = {{(8-LG){1'b0}}, top}; end
                        end
                    end
                end
                S_STALL: if (hok[r[LG-1:0]]) begin st <= S_PATH; lj <= LG'((GMAX + r) >> 1); end
                    else if (xok[r[LG-1:0]]) begin
                        // the fetch in flight at the pop landed as a 'next' (the head was still valid then): promote it
                        hv[r[LG-1:0]] <= xv[r[LG-1:0]]; hi[r[LG-1:0]] <= xi[r[LG-1:0]]; hok[r[LG-1:0]] <= 1'b1;
                        xok[r[LG-1:0]] <= 1'b0;
                        if (hpos[r[LG-1:0]] != n && !inq[r[LG-1:0]] && !(fe_busy && fr == r)) begin push_q = 1'b1; push_r = r; end
                        st <= S_PATH; lj <= LG'((GMAX + r) >> 1);
                    end
                S_FLUSH: begin
                    if (pk_m[0] != 8'd0) pk_full[0] <= 1'b1;
                    if (has_r && pk_m[1] != 8'd0) pk_full[1] <= 1'b1;
                    if (!wp_v && ocnt == 3'd0 && pk_m[0] == 8'd0 && (!has_r || pk_m[1] == 8'd0)) begin st <= S_IDLE; done <= 1'b1; end
                end
                default: st <= S_IDLE;
            endcase
            // ---- fetch queue push (one a cycle)
            if (push_q) begin
                fq[fq_t] <= push_r; fq_t <= (fq_t == GMAX - 1) ? '0 : fq_t + 1'b1; inq[push_r[LG-1:0]] <= 1'b1;
            end
            if (st == S_IDLE) fq_n <= '0;
            else fq_n <= fq_n + {{LG{1'b0}}, push_q} - {{LG{1'b0}}, (st != S_FLUSH && !fe_busy && fq_n != 0)};
            // ---- packer writes
            if (wp_v && !iss && ocnt < 3'd4) begin
                iss = 1'b1;
                vmq <= {1'b1, 1'b1, {12'd0, pk_s[wp], 5'd0}, pk_d[wp],
                        {{4{pk_m[wp][7]}}, {4{pk_m[wp][6]}}, {4{pk_m[wp][5]}}, {4{pk_m[wp][4]}},
                         {4{pk_m[wp][3]}}, {4{pk_m[wp][2]}}, {4{pk_m[wp][1]}}, {4{pk_m[wp][0]}}}, 16'h0922};
                pk_full[wp] <= 1'b0; pk_m[wp] <= 8'd0;
            end
            ocnt <= ocnt + {2'd0, iss} - {2'd0, vmr[273]};
        end
    end
endmodule
`default_nettype wire
