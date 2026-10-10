`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.MERGE (G20, hgi-takeover 2026-10-09): the exact k-way merge behind COLL.TOPK_MERGE.  The program gathers
// every rank's local selection into VM (values, ids; G runs of n), each run already sorted by the merge key, and this
// engine emits the first k elements of the merged order -- exactly the golden lexsort (hgi_sim ds_native.topk_merge).
//
//   A  VM FP32  G rows of n values (row stride A.stride)        key 0 (param[12] = 0): larger value first, -0 = +0,
//   B  VM U32   G rows of n ids    (row stride B.stride)          NaN after every number, equal values -> lower id
//   O  VM U32   k merged ids                                    key 1 (param[12] = 1): lower id first (values ride along)
//   R  VM FP32  k merged values (optional)
//   param [11:0] k (1 .. 2,048), [12] key; G = A.m (1 .. 128).
// A run whose next element is better than the one before it is unsorted input: fault (fail-closed).  Fewer than k
// elements in all runs: O / R hold all of them.
//
// RATE REDESIGN (coordinator 2026-10-09 ~22:30, hbm-sim reprice: 9 merges a DS token at ~12k cycles): ~1 output a
// cycle.  The earlier engine re-evaluated one tournament path a level a cycle after every pop (~12 cycles an output).
//   * MERGE TREE OF FIFOS: GMAX - 1 two-input nodes (a balanced binary tree over the runs), each with a 2-entry output
//     FIFO.  A node moves its better child head into its FIFO whenever its FIFO has room (registered count < 2) and
//     both children have a head or are exhausted: every level works every cycle, so the root delivers 1 element a
//     cycle once the leaves are primed (latency log2 GMAX).  All decisions read registered state (no ripple up the
//     tree); a pop and a push may hit a FIFO in the same cycle.
//   * LEAVES: per run a head / next / after-next register FIFO, refilled from a per-run 2-sector RING (the value ring and the id
//     ring: 2 x GMAX sector words each = one 256 x 256 1R1W macro each at GMAX 128), one element a cycle (read port
//     shared by all runs, registered read: a run that wins every cycle is refilled every cycle).  Runs that miss their
//     head are refilled first.
//   * VM FAST PATH: whole 8-word sectors, up to 4 requests outstanding, in-order responses.  Per run and stream the
//     ring holds the sector of the next element and the one after it (prefetch); sectors land whole, so A and B rows
//     may start at any word.  The urgent sectors (the next element's) go before prefetches, the output sector writes
//     (two packers, O and R) before both.
//   * sortedness: every element loaded into a run's head / next is checked against the run's previous element.
// Bench: tb_hgi_idx_merge (tools/hgi_idx_merge_vectors.py), MUT 1 ties to the higher id, MUT 2 no sortedness check,
// MUT 3 a node FIFO accepts a push when full (drops an element): all must FAIL.
module ot_hgi_idx_merge #(
    parameter integer GMAX = 128,
    parameter integer MUT = 0
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
    localparam integer NB = GMAX / 2;            // bottom nodes NB .. GMAX-1 take leaves
    // ---------------------------------------------------------------- key order
    function automatic [31:0] okey(input [31:0] v);
        okey = (v[30:0] == 31'd0) ? 32'h8000_0000 : (v[31] ? ~v : (v | 32'h8000_0000));
    endfunction
    function automatic is_nan(input [31:0] v); is_nan = (v[30:23] == 8'hFF) && (v[22:0] != 23'd0); endfunction
    function automatic better(input [31:0] a, input [31:0] ai, input [31:0] b, input [31:0] bi, input kid);
        reg lo;
        begin
            lo = (MUT == 1) ? (ai > bi) : (ai < bi);
            if (kid) better = lo;
            else if (is_nan(a) != is_nan(b)) better = is_nan(b);
            else if (is_nan(a)) better = lo;
            else if (okey(a) != okey(b)) better = okey(a) > okey(b);
            else better = lo;
        end
    endfunction
    // ---------------------------------------------------------------- latched command
    reg [11:0] kq; reg kid; reg [7:0] gq; reg [19:0] nq; reg [17:0] ab, bb, as_, bs_; reg hr;
    localparam S_IDLE = 2'd0, S_RUN = 2'd1, S_FLUSH = 2'd2, S_FAULT = 2'd3;
    reg [1:0] st;
    reg rgo_q; reg [7:0] rsel_q; reg [2:0] la_q, lb_q; reg [255:0] rdv, rdi;    // refill read in flight
    // ---------------------------------------------------------------- per-run state
    reg [31:0] hv [0:GMAX-1]; reg [31:0] hi [0:GMAX-1];     // head
    reg [31:0] xv [0:GMAX-1]; reg [31:0] xi [0:GMAX-1];     // next
    reg [31:0] yv [0:GMAX-1]; reg [31:0] yi [0:GMAX-1];     // after next (a run winning every cycle: refill latency 2)
    reg [31:0] tv [0:GMAX-1]; reg [31:0] ti [0:GMAX-1];     // previous element loaded (sortedness)
    reg [GMAX-1:0] hok, xok, yok, tok, infl;
    reg [19:0] cc [0:GMAX-1];                                  // elements taken from the ring
    reg [17:0] fv [0:GMAX-1]; reg [17:0] fi [0:GMAX-1];       // sectors requested (row-relative), per stream
    reg [17:0] lv [0:GMAX-1]; reg [17:0] li [0:GMAX-1];       // sectors landed
    // rings (1R1W: one write a cycle from the VM response, one registered read a cycle for a refill)
    reg [255:0] rv [0:2*GMAX-1]; reg [255:0] ri [0:2*GMAX-1];
    // row word offsets within the first sector: (base + r * stride) mod 8
    function automatic [2:0] off(input [17:0] base, input [17:0] str, input integer r);
        off = base[2:0] + 3'(r) * str[2:0];
    endfunction
    // ---------------------------------------------------------------- tree
    reg [31:0] q0v [1:GMAX-1]; reg [31:0] q0i [1:GMAX-1]; reg [31:0] q1v [1:GMAX-1]; reg [31:0] q1i [1:GMAX-1];
    reg [1:0] qc [1:GMAX-1]; reg [GMAX-1:1] ndn;
    wire [GMAX-1:0] ldn;                                       // leaf exhausted
    genvar gr;
    generate for (gr = 0; gr < GMAX; gr = gr + 1) begin : g_ldn
        assign ldn[gr] = (gr >= gq) || (cc[gr] == nq && !hok[gr] && !xok[gr] && !yok[gr] && !infl[gr]);
    end endgenerate
    reg [GMAX-1:1] popl, popr, push; reg [31:0] pv [1:GMAX-1]; reg [31:0] pi [1:GMAX-1];
    reg [GMAX-1:0] lpop;
    reg rpop;                                                  // root FIFO popped by the output stage
    integer j, a, b, c;
    reg lvld, rvld, ldon, rdon; reg [31:0] lav, lai, rav, rai;
    always @* begin
        popl = '0; popr = '0; push = '0; lpop = '0;
        for (j = 1; j < GMAX; j = j + 1) begin
            pv[j] = 32'd0; pi[j] = 32'd0;
            if (j >= NB) begin
                a = 2 * j - GMAX; b = a + 1;
                lvld = hok[a]; lav = hv[a]; lai = hi[a]; ldon = ldn[a];
                rvld = hok[b]; rav = hv[b]; rai = hi[b]; rdon = ldn[b];
            end else begin
                a = 2 * j; b = 2 * j + 1;
                lvld = qc[a] != 2'd0; lav = q0v[a]; lai = q0i[a]; ldon = ndn[a];
                rvld = qc[b] != 2'd0; rav = q0v[b]; rai = q0i[b]; rdon = ndn[b];
            end
            if (st == S_RUN && (qc[j] < 2'd2 || MUT == 3) && (lvld || ldon) && (rvld || rdon) && (lvld || rvld)) begin
                push[j] = 1'b1;
                if (lvld && (!rvld || !better(rav, rai, lav, lai, kid))) begin popl[j] = 1'b1; pv[j] = lav; pi[j] = lai; end
                else begin popr[j] = 1'b1; pv[j] = rav; pi[j] = rai; end
            end
            if (j >= NB) begin lpop[2 * j - GMAX] = popl[j]; lpop[2 * j - GMAX + 1] = popr[j]; end
        end
    end
    function automatic cpop(input integer ch);          // child node ch popped by its parent this cycle
        cpop = (ch == 1) ? rpop : (ch[0] ? popr[ch >> 1] : popl[ch >> 1]);
    endfunction
    // ---------------------------------------------------------------- output packers (O ids, R values)
    reg [17:0] pk_a [0:1]; reg [255:0] pk_d [0:1]; reg [7:0] pk_m [0:1]; reg [14:0] pk_s [0:1]; reg [1:0] pk_full;
    wire pk_ok = !pk_full[0] && !(hr && pk_full[1]);
    reg [11:0] nout;
    always @* rpop = (st == S_RUN) && pk_ok && qc[1] != 2'd0 && nout != kq;
    // ---------------------------------------------------------------- refill selection (one run a cycle)
    reg [GMAX-1:0] can, urg; reg [7:0] rsel; reg rgo;
    reg [19:0] e_; reg [20:0] pa, pb; reg [2:0] oa, ob;
    always @* begin
        can = '0; urg = '0;
        for (j = 0; j < GMAX; j = j + 1) begin
            oa = off(ab, as_, j); ob = off(bb, bs_, j);
            pa = {1'b0, cc[j]} + oa; pb = {1'b0, cc[j]} + ob;
            if (st == S_RUN && j < gq && cc[j] != nq && (pa[20:3] < {3'd0, lv[j]}) && (pb[20:3] < {3'd0, li[j]}) &&
                ({1'b0, hok[j]} + {1'b0, xok[j]} + {1'b0, yok[j]} + {1'b0, infl[j]} < 2'd3)) begin
                can[j] = 1'b1; urg[j] = !hok[j] && !infl[j];
            end
        end
        rgo = |can; rsel = 8'd0;
        for (j = GMAX - 1; j >= 0; j = j - 1) if (urg[j] || (!(|urg) && can[j])) rsel = 8'(j);
    end
    // ---------------------------------------------------------------- VM request selection
    // per run / stream: next sector to fetch fv / fi (row-relative); allowed when it is at most one past the sector
    // of the next element taken from the ring, and inside the row
    reg [GMAX-1:0] nva_u, nva_p, nvb_u, nvb_p;
    reg [20:0] lastw;
    always @* begin
        nva_u = '0; nva_p = '0; nvb_u = '0; nvb_p = '0;
        for (j = 0; j < GMAX; j = j + 1) begin
            oa = off(ab, as_, j); ob = off(bb, bs_, j);
            pa = {1'b0, cc[j]} + oa; pb = {1'b0, cc[j]} + ob;
            if (st == S_RUN && j < gq && nout != kq) begin
                lastw = {1'b0, nq} - 21'd1 + oa;
                if ({3'd0, fv[j]} <= lastw[20:3] && {3'd0, fv[j]} <= pa[20:3] + 21'd1 && cc[j] != nq) begin
                    if ({3'd0, fv[j]} == pa[20:3]) nva_u[j] = 1'b1; else nva_p[j] = 1'b1;
                end
                lastw = {1'b0, nq} - 21'd1 + ob;
                if ({3'd0, fi[j]} <= lastw[20:3] && {3'd0, fi[j]} <= pb[20:3] + 21'd1 && cc[j] != nq) begin
                    if ({3'd0, fi[j]} == pb[20:3]) nvb_u[j] = 1'b1; else nvb_p[j] = 1'b1;
                end
            end
        end
    end
    function automatic [8:0] ffs(input [GMAX-1:0] m);       // {found, index}
        integer t; begin ffs = 9'd0; for (t = GMAX - 1; t >= 0; t = t - 1) if (m[t]) ffs = {1'b1, 8'(t)}; end
    endfunction
    // tag FIFO of requests in flight: {kind 2 (0 A, 1 B, 2 write), run 8, slot 1}
    reg [10:0] tq [0:3]; reg [1:0] tq_h, tq_t; reg [2:0] ocnt;
    reg iss; reg [10:0] itag; reg [8:0] fsel; reg [17:0] rb_;
    integer r_;
    // ---------------------------------------------------------------- sequential
    reg [31:0] nvx, nix; reg sortf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; vmq <= 338'd0; ocnt <= 3'd0; tq_h <= 2'd0; tq_t <= 2'd0;
            pk_full <= 2'd0; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0; rgo_q <= 1'b0;
            hok <= '0; xok <= '0; yok <= '0; tok <= '0; infl <= '0; ndn <= '0; gq <= 8'd0; nq <= 20'd0; kq <= 12'd0;
            for (j = 1; j < GMAX; j = j + 1) qc[j] <= 2'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq[337] <= 1'b0; iss = 1'b0; sortf = 1'b0;
            // ---- responses (in order): land a sector in its ring, or a write echo
            if (vmr[273]) begin
                r_ = tq[tq_h][8:1];
                if (tq[tq_h][10:9] == 2'd0) begin rv[2 * r_ + tq[tq_h][0]] <= vmr[255:0]; lv[r_] <= lv[r_] + 18'd1; end
                if (tq[tq_h][10:9] == 2'd1) begin ri[2 * r_ + tq[tq_h][0]] <= vmr[255:0]; li[r_] <= li[r_] + 18'd1; end
                tq_h <= tq_h + 2'd1;
            end
            // ---- leaves: pop by the bottom node, then the landing refill (issued last cycle)
            for (j = 0; j < GMAX; j = j + 1) begin : leaf
                reg h_, x_, y_; reg [31:0] hv_, hi_, xv_, xi_, yv_, yi_;
                h_ = hok[j]; x_ = xok[j]; y_ = yok[j]; hv_ = hv[j]; hi_ = hi[j]; xv_ = xv[j]; xi_ = xi[j]; yv_ = yv[j]; yi_ = yi[j];
                if (lpop[j]) begin h_ = x_; hv_ = xv_; hi_ = xi_; x_ = y_; xv_ = yv_; xi_ = yi_; y_ = 1'b0; end
                if (rgo_q && rsel_q == 8'(j)) begin
                    nvx = rdv[la_q * 32 +: 32]; nix = rdi[lb_q * 32 +: 32];
                    if (tok[j] && MUT != 2 && better(nvx, nix, tv[j], ti[j], kid)) sortf = 1'b1;
                    tv[j] <= nvx; ti[j] <= nix; tok[j] <= 1'b1;
                    if (!h_) begin h_ = 1'b1; hv_ = nvx; hi_ = nix; end
                    else if (!x_) begin x_ = 1'b1; xv_ = nvx; xi_ = nix; end
                    else begin y_ = 1'b1; yv_ = nvx; yi_ = nix; end
                    infl[j] <= 1'b0;
                end
                hok[j] <= h_; xok[j] <= x_; yok[j] <= y_; hv[j] <= hv_; hi[j] <= hi_; xv[j] <= xv_; xi[j] <= xi_;
                yv[j] <= yv_; yi[j] <= yi_;
            end
            // ---- refill read (registered ring read; lands next cycle)
            rgo_q <= rgo; rsel_q <= rsel;
            if (rgo) begin
                pa = {1'b0, cc[rsel]} + off(ab, as_, rsel); pb = {1'b0, cc[rsel]} + off(bb, bs_, rsel);
                rdv <= rv[2 * rsel + pa[3]]; rdi <= ri[2 * rsel + pb[3]]; la_q <= pa[2:0]; lb_q <= pb[2:0];
                cc[rsel] <= cc[rsel] + 20'd1; infl[rsel] <= 1'b1;
            end
            // ---- tree FIFOs
            for (j = 1; j < GMAX; j = j + 1) begin : node
                reg [1:0] c_; reg [31:0] a0v, a0i, a1v, a1i;
                c_ = qc[j]; a0v = q0v[j]; a0i = q0i[j]; a1v = q1v[j]; a1i = q1i[j];
                if (cpop(j)) begin a0v = a1v; a0i = a1i; c_ = c_ - 2'd1; end
                if (push[j]) begin
                    if (c_ == 2'd0) begin a0v = pv[j]; a0i = pi[j]; end else begin a1v = pv[j]; a1i = pi[j]; end
                    if (c_ != 2'd2) c_ = c_ + 2'd1;          // MUT 3: a push into a full FIFO is lost
                end
                qc[j] <= c_; q0v[j] <= a0v; q0i[j] <= a0i; q1v[j] <= a1v; q1i[j] <= a1i;
                if (j >= NB) ndn[j] <= ldn[2 * j - GMAX] && ldn[2 * j - GMAX + 1] && c_ == 2'd0 && !push[j];
                else ndn[j] <= ndn[2 * j] && ndn[2 * j + 1] && c_ == 2'd0 && !push[j];
            end
            // ---- output stage
            if (rpop) begin
                pk_d[0][pk_a[0][2:0] * 32 +: 32] <= q0i[1]; pk_m[0][pk_a[0][2:0]] <= 1'b1; pk_s[0] <= pk_a[0][17:3];
                pk_a[0] <= pk_a[0] + 18'd1; if (pk_a[0][2:0] == 3'd7) pk_full[0] <= 1'b1;
                if (hr) begin
                    pk_d[1][pk_a[1][2:0] * 32 +: 32] <= q0v[1]; pk_m[1][pk_a[1][2:0]] <= 1'b1; pk_s[1] <= pk_a[1][17:3];
                    pk_a[1] <= pk_a[1] + 18'd1; if (pk_a[1][2:0] == 3'd7) pk_full[1] <= 1'b1;
                end
                nout <= nout + 12'd1;
            end
            // ---- VM requests: packer writes, then urgent A / B sectors, then prefetches
            if (ocnt < 3'd4) begin
                if (|pk_full) begin : wr
                    reg w; w = pk_full[0] ? 1'b0 : 1'b1;
                    iss = 1'b1; itag = {2'd2, 8'd0, 1'b0};
                    vmq <= {1'b1, 1'b1, {12'd0, pk_s[w], 5'd0}, pk_d[w],
                            {{4{pk_m[w][7]}}, {4{pk_m[w][6]}}, {4{pk_m[w][5]}}, {4{pk_m[w][4]}},
                             {4{pk_m[w][3]}}, {4{pk_m[w][2]}}, {4{pk_m[w][1]}}, {4{pk_m[w][0]}}}, 16'h0922};
                    pk_full[w] <= 1'b0; pk_m[w] <= 8'd0;
                end else begin
                    fsel = ffs(nva_u); itag = {2'd0, fsel[7:0], 1'b0};
                    if (!fsel[8]) begin fsel = ffs(nvb_u); itag = {2'd1, fsel[7:0], 1'b0}; end
                    if (!fsel[8]) begin fsel = ffs(nva_p); itag = {2'd0, fsel[7:0], 1'b0}; end
                    if (!fsel[8]) begin fsel = ffs(nvb_p); itag = {2'd1, fsel[7:0], 1'b0}; end
                    if (fsel[8]) begin
                        iss = 1'b1;
                        if (itag[10:9] == 2'd0) begin
                            rb_ = ab + fsel[7:0] * as_;
                            itag[0] = fv[fsel[7:0]][0];
                            vmq <= {1'b1, 1'b0, {12'd0, 15'(rb_[17:3] + fv[fsel[7:0]][14:0]), 5'd0}, 256'd0, 32'd0, 16'h0920};
                            fv[fsel[7:0]] <= fv[fsel[7:0]] + 18'd1;
                        end else begin
                            rb_ = bb + fsel[7:0] * bs_;
                            itag[0] = fi[fsel[7:0]][0];
                            vmq <= {1'b1, 1'b0, {12'd0, 15'(rb_[17:3] + fi[fsel[7:0]][14:0]), 5'd0}, 256'd0, 32'd0, 16'h0921};
                            fi[fsel[7:0]] <= fi[fsel[7:0]] + 18'd1;
                        end
                    end
                end
                if (iss) begin tq[tq_t] <= itag; tq_t <= tq_t + 2'd1; end
            end
            ocnt <= ocnt + {2'd0, iss} - {2'd0, vmr[273]};
            // ---- control
            case (st)
                S_IDLE: if (go) begin
                    if (k == 12'd0 || k > 12'd2048 || g == 8'd0 || g > GMAX || n == 20'd0) fault <= 1'b1;
                    else begin
                        st <= S_RUN; kq <= k; kid <= key_id; gq <= g; nq <= n; ab <= a_base; bb <= b_base;
                        as_ <= a_str; bs_ <= b_str; hr <= has_r; nout <= 12'd0;
                        hok <= '0; xok <= '0; yok <= '0; tok <= '0; infl <= '0; ndn <= '0; rgo_q <= 1'b0;
                        for (j = 0; j < GMAX; j = j + 1) begin cc[j] <= 20'd0; fv[j] <= 18'd0; fi[j] <= 18'd0; lv[j] <= 18'd0; li[j] <= 18'd0; end
                        for (j = 1; j < GMAX; j = j + 1) qc[j] <= 2'd0;
                        pk_a[0] <= o_base; pk_a[1] <= r_base; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0; pk_full <= 2'd0;
                    end
                end
                S_RUN: begin
                    if (sortf) st <= S_FAULT;
                    else if (nout == kq || (ndn[1] && qc[1] == 2'd0)) st <= S_FLUSH;
                end
                S_FLUSH: begin
                    if (pk_m[0] != 8'd0 && !pk_full[0]) pk_full[0] <= 1'b1;
                    if (hr && pk_m[1] != 8'd0 && !pk_full[1]) pk_full[1] <= 1'b1;
                    if (!(|pk_full) && ocnt == 3'd0 && !iss && pk_m[0] == 8'd0 && (!hr || pk_m[1] == 8'd0)) begin
                        st <= S_IDLE; done <= 1'b1;
                    end
                end
                S_FAULT: if (ocnt == 3'd0 && !iss) begin st <= S_IDLE; fault <= 1'b1; end
            endcase
        end
    end
endmodule
`default_nettype wire
