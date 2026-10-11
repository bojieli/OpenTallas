`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_tkm (hgi-1010/k 2026-10-10): the hardware COLL.TOPK_MERGE merge sink on the collective gather bypass.
//
// Semantics (tools/hgi_sim/machine.py u_coll_topk_merge, spec 6.7): every rank q of the group contributes n (value FP32,
// id U32) pairs; the result is the group's top k by descending value, -0 = +0, ties to the lower id (the golden
// lexsort((id, -value)), stable in concatenation order: rank q, then index j); O = those ids in ASCENDING id order
// (equal ids by the value order), R = their values (original bits, -0 kept).  k > G n takes all G n.  A NaN value faults.
//
// Transport (ot_hgi_coll_ep TKM = 1): flit f of rank q carries elements 8f .. 8f + 7: words 0..7 = values (the A sector
// f), words 8..15 = ids (the B sector f); pf = ceil(n / 8) flits a rank, multicast unchanged on the exact gather bypass.
// The sink takes the endpoint's delivery lanes behind per-lane credits (del_permit / del_reserve, as ot_hgi_coll_rgx_sink)
// so a busy merge back-pressures the switch instead of dropping.
//
// Element: E = {v, okey(value), ~id, ~q, ~j, nz} (84 bits).  The VALUE KEY {v, okey, ~id, ~q, ~j} (83 bits, larger is
// better) is a strict total order equal to the golden order; the ID KEY {v, ~id, okey, ~q, ~j} orders the output.
//
// Datapath:
//   decode (2 edges a lane): q = src - gbase, f = gi - q pf, j = 8 f + s, valid j < n, NaN check, E -> per-lane FIFO
//            (CAP 64, credits returned on pop);
//   filter / select: a lane head's elements are survivors iff key > tau; up to W = 4 survivors a cycle are taken over
//            the four lane heads (32 elements: a head whose survivors are all taken pops, so sparse survivors run at
//            the full 32 elements a cycle);
//   entry sort: the <= 4 survivors -> one block sorted by the value key (rank sort, 2 edges);
//   SYSTOLIC MERGE ARRAY: C = KMAX / 4 cells of 4 sorted elements.  A cell holding block X that receives a block Y
//            from above keeps the top 4 of X u Y and passes the bottom 4 down (merge path: 16 comparators); the last
//            cell drops its bottom.  Invariant: every element that passed cell c is <= every element cell c holds
//            then or later, so (a) position p = 4c + s holds an element with >= p + 1 elements >= it in the array
//            (tau = the element at position nout - 1 is an exact lower bound of the k-th key: anything below it can
//            never be selected), (b) a dropped element has KMAX >= k better elements, and (c) once no block is in
//            flight above cell ceil(nout / 4) the array's first nout positions are the exact top-nout, sorted.
//   ID PHASE: positions >= nout invalidated, every block rank-sorted by the id key, then ceil(nout / 4) rounds of
//            odd-even transposition (block merge-split between neighbours, the same merge network: the lower cell
//            keeps the bottom 4 and returns the top 4 to the upper cell) sort the selection by id;
//   OUTPUT: the array shifts up 4 cells an edge: 16 ids -> one O line (VM, 16 words), 16 values -> one R line.
// Fault (sticky until rst_n): NaN, a flit from outside the group / past pf, more than G pf flits, a credit underflow,
// a FIFO overflow.  MUT (bench mutants): 1 ties to the HIGHER id, 2 the 4th survivor of a select cycle is dropped,
// 3 a reservation does not consume a credit (FIFO overflow under back-pressure), 4 no id phase (O in value order).
module ot_hgi_coll_tkm #(
    parameter integer KMAX = 2048,
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,          // one edge: configuration below valid
    input  wire [11:0]          cfg_n,          // this rank's n (informational: validity is the sender's pad marker)
    input  wire [12:0]          cfg_k,          // k: O.n must equal min(k, elements received)
    input  wire [7:0]           cfg_g,          // group size
    input  wire [7:0]           cfg_gbase,      // the group's first rank (flit src - gbase = q)
    input  wire [15:0]          cfg_pf,         // ceil(n / 8)
    input  wire [12:0]          cfg_nout,       // O.n = min(k, the group's elements), 1 .. KMAX
    input  wire [39:0]          cfg_obase,      // O: VM word address (16-word aligned)
    input  wire [39:0]          cfg_rbase,      // R: VM word address (16-word aligned)
    input  wire                 cfg_has_r,
    input  wire [DEL-1:0]       del_reserve,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output reg                  w_v,
    output reg  [39:0]          w_addr,
    output reg  [15:0]          w_mask,
    output reg  [FW-1:0]        w_data,
    input  wire                 w_rdy,
    output wire                 busy,
    output reg                  done,           // one edge: every output line accepted
    output reg                  fault,
    output reg  [31:0]          stat_cycles,    // start -> done
    output reg  [31:0]          stat_ins,       // blocks inserted
    output reg  [31:0]          stat_surv       // survivors taken
);
    localparam integer W  = 4;
    localparam integer C  = KMAX / W;
    localparam integer EW = 84;
    localparam integer KW = 83;
    localparam integer CB = $clog2(C + 1);
    localparam integer QW = 8 * EW;            // FIFO word: 8 elements
    // ---------------------------------------------------------------- element helpers
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [KW-1:0] vkey(input [EW-1:0] e);
        vkey = e[EW-1:1];
    endfunction
    function automatic [KW-1:0] ikey(input [EW-1:0] e);
        ikey = {e[83], e[50:19], e[82:51], e[18:1]};
    endfunction
    function automatic [KW-1:0] mkey(input [EW-1:0] e, input idm);
        mkey = idm ? ikey(e) : vkey(e);
    endfunction
    // ---------------------------------------------------------------- configuration
    reg [11:0] n_q; reg [7:0] g_q, gb_q; reg [15:0] pf_q; reg [12:0] nout_q; reg [39:0] ob_q, rb_q; reg hr_q;
    reg [23:0] tot_q;                          // G pf flits expected
    reg [CB-1:0] cact_q;                       // ceil(nout / 4) active cells
    reg [CB-1:0] tc_q; reg [1:0] ts_q;         // tau position (nout - 1) -> cell, slot
    // ---------------------------------------------------------------- phases
    localparam [3:0] P_IDLE = 4'd0, P_INS = 4'd1, P_DRAIN = 4'd2, P_INV = 4'd3, P_RS = 4'd4, P_OETS = 4'd5,
                     P_OUT = 4'd6, P_FLUSH = 4'd7, P_DONE = 4'd8;
    reg [3:0] ph;
    assign busy = (ph != P_IDLE);
    // ---------------------------------------------------------------- delivery credits + decode + FIFO
    reg [7:0] cr [0:DEL-1];
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_perm
        assign del_permit[l] = (cr[l] != 8'd0) && (ph == P_INS);     // flops only (no start -> permit path)
    end
    reg [DEL-1:0] d1_v, d2_v;
    reg [7:0] d1_q [0:DEL-1]; reg [15:0] d1_gi [0:DEL-1]; reg [FW-1:0] d1_d [0:DEL-1];
    reg [23:0] d1_qpf [0:DEL-1];
    reg [QW-1:0] d2_e [0:DEL-1];
    wire [DEL-1:0] fe, fo; wire [QW-1:0] fd [0:DEL-1]; wire [6:0] fcnt [0:DEL-1];
    reg [DEL-1:0] fpop, fpop_q;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_fifo
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(QW), .AW(6)) u_q (.clk(clk), .rst_n(rst_n), .push(d2_v[l]),
            .din(d2_e[l]), .pop(fpop[l]), .empty(fe[l]), .dout(fd[l]), .ovf(fo[l]), .count(fcnt[l]));
    end
    reg [23:0] rcv;                            // flits received (decoded)
    reg [18:0] nel;                            // valid (non-pad) elements received
    reg [12:0] k_q;
    reg [7:0]  occ [0:DEL-1];                  // FIFO occupancy (pushed - popped; the sfifo count misses its pipeline)
    // ---------------------------------------------------------------- tau
    reg [KW-1:0] tau;
    // ---------------------------------------------------------------- staging (3 a lane) + select
    reg [EW-1:0] st_e [0:DEL-1][0:2][0:7];
    reg [7:0]    st_m [0:DEL-1][0:2];
    reg [1:0]    st_n [0:DEL-1];
    reg [DEL-1:0] ld_v;
    reg [EW-1:0] ld_e [0:DEL-1][0:7];
    reg [7:0]    ld_m [0:DEL-1];
    reg [7:0]    dn [0:DEL-1];                 // survivors of the head already taken
    // entry pipeline
    reg          e1_v; reg [EW-1:0] e1 [0:3];
    reg          e2_v; reg [EW-1:0] e2 [0:3]; reg [5:0] e2_ge;   // pairwise compares for the rank sort
    // ---------------------------------------------------------------- the array
    reg [EW-1:0] X [0:C-1][0:3];
    // the entry block, rank-sorted, registered once per group of BG positions (broadcast fanout replicated at the flops)
    localparam integer BG = 32, NB = (KMAX + BG - 1) / BG, P = KMAX;
    reg [EW-1:0] bk [0:NB-1][0:3];
    reg          bv;
    reg [CB:0]   rnd;                          // OETS rounds done
    reg          par;                          // OETS parity: 0 pairs (2i, 2i+1), 1 pairs (2i+1, 2i+2)
    // merge network outputs, per cell
    reg [EW-1:0] mt [0:C-1][0:3];
    reg [EW-1:0] mb [0:C-1][0:3];
    wire idm = (ph == P_RS) || (ph == P_OETS);
    integer c, s, a, b, l, i;
    always @* begin : merge
        reg [EW-1:0] A_ [0:3]; reg [EW-1:0] B_ [0:3];
        reg ge [0:3][0:3];
        reg [2:0] ra [0:3]; reg [2:0] rb [0:3];
        reg [EW-1:0] m [0:7];
        for (c = 0; c < C; c = c + 1) begin
            for (s = 0; s < 4; s = s + 1) begin
                A_[s] = X[c][s];
                B_[s] = (c > 0) ? X[(c > 0) ? c - 1 : 0][s] : {EW{1'b0}};     // OETS: the cell above
            end
            for (a = 0; a < 4; a = a + 1) for (b = 0; b < 4; b = b + 1)
                ge[a][b] = (mkey(A_[a], idm) >= mkey(B_[b], idm));
            for (a = 0; a < 4; a = a + 1) begin
                ra[a] = 3'(a);
                for (b = 0; b < 4; b = b + 1) if (!ge[a][b]) ra[a] = ra[a] + 3'd1;
            end
            for (b = 0; b < 4; b = b + 1) begin
                rb[b] = 3'(b);
                for (a = 0; a < 4; a = a + 1) if (ge[a][b]) rb[b] = rb[b] + 3'd1;
            end
            for (i = 0; i < 8; i = i + 1) begin
                m[i] = {EW{1'b0}};
                for (a = 0; a < 4; a = a + 1) if (ra[a] == 3'(i)) m[i] = m[i] | A_[a];
                for (b = 0; b < 4; b = b + 1) if (rb[b] == 3'(i)) m[i] = m[i] | B_[b];
            end
            for (s = 0; s < 4; s = s + 1) begin mt[c][s] = m[s]; mb[c][s] = m[4 + s]; end
        end
    end
    // rank sort of a block by the id key (P_RS)
    function automatic [4*EW-1:0] rsort(input [4*EW-1:0] blk);
        reg [EW-1:0] e_ [0:3]; reg [1:0] r_ [0:3]; reg [4*EW-1:0] o_;
        begin
            for (integer x = 0; x < 4; x = x + 1) e_[x] = blk[EW*x +: EW];
            for (integer x = 0; x < 4; x = x + 1) begin
                r_[x] = 2'd0;
                for (integer y = 0; y < 4; y = y + 1)
                    if (y != x && (ikey(e_[y]) > ikey(e_[x]) || (ikey(e_[y]) == ikey(e_[x]) && y < x))) r_[x] = r_[x] + 2'd1;
            end
            o_ = '0;
            for (integer x = 0; x < 4; x = x + 1) o_[EW*r_[x] +: EW] = o_[EW*r_[x] +: EW] | e_[x];
            rsort = o_;
        end
    endfunction
    // lower cell of an OETS round
    function automatic lowc(input integer cc, input pp);
        lowc = (cc >= 1) && ((cc & 1) == (pp ? 0 : 1));
    endfunction
    // ---------------------------------------------------------------- tau tap (gated OR tree, registered every 16:1)
    localparam integer NG = (C + 15) / 16;
    reg [KW-1:0] tau_a [0:NG-1];
    reg [KW-1:0] tau_b;
    always @(posedge clk) begin : tg
        reg [KW-1:0] o_;
        for (integer g = 0; g < NG; g = g + 1) begin
            o_ = '0;
            for (integer x = 0; x < 16; x = x + 1)
                if (g * 16 + x < C && CB'(g * 16 + x) == tc_q) o_ = o_ | vkey(X[(g * 16 + x < C) ? g * 16 + x : 0][ts_q]);
            tau_a[g] <= o_;
        end
    end
    always @* begin : tor
        tau_b = '0;
        for (integer g = 0; g < NG; g = g + 1) tau_b = tau_b | tau_a[g];
    end
    // ---------------------------------------------------------------- output packer
    reg [12:0] outn;                           // elements shifted out
    reg [12:0] wrn;                            // elements written (O lines)
    reg [8:0]  line;                           // output line index
    // ---------------------------------------------------------------- main sequential
    // BROADCAST INSERTION (one rank-sorted block of 4 a cycle, settled the same edge): position p of the array (A_p =
    // X[p / 4][p % 4], sorted by the value key, larger first) moves to p + c_p, c_p = the block elements greater than A_p
    // (monotone in p); position q takes A_{q-i} when c_{q-i} = i (i = 0 .. 4), else block element j where
    // c_{q-j} > j and c_{q-j-1} <= j.  Positions >= KMAX fall off (the smallest: KMAX >= k better ones remain).
    reg [2:0] cp [0:P-1];
    reg [EW-1:0] ins [0:P-1];
    always @* begin : bcins
        for (integer p_ = 0; p_ < P; p_ = p_ + 1) begin
            cp[p_] = 3'd0;
            for (integer j = 0; j < 4; j = j + 1)
                if (vkey(bk[p_ / BG][j]) > vkey(X[p_ / 4][p_ % 4])) cp[p_] = cp[p_] + 3'd1;
        end
        for (integer q = 0; q < P; q = q + 1) begin
            ins[q] = {EW{1'b0}};
            for (integer i = 0; i <= 4; i = i + 1)
                if (q - i >= 0 && cp[(q - i >= 0) ? q - i : 0] == 3'(i)) ins[q] = ins[q] | X[((q - i >= 0) ? q - i : 0) / 4][((q - i >= 0) ? q - i : 0) % 4];
            for (integer j = 0; j < 4; j = j + 1)
                if (q - j >= 0 && cp[(q - j >= 0) ? q - j : 0] > 3'(j) && (q - j - 1 < 0 || cp[(q - j - 1 >= 0) ? q - j - 1 : 0] <= 3'(j)))
                    ins[q] = ins[q] | bk[q / BG][j];
        end
    end
    // output step: one 16-element line an edge (the array shifts up 4 cells); O line (+ R line) into a 4-line queue that
    // the write port drains one line an edge; a step needs room for its lines
    reg [FW-1:0] lq_d [0:3]; reg [39:0] lq_a [0:3]; reg [15:0] lq_m [0:3]; reg [2:0] lq_n; reg [1:0] lq_h, lq_t;
    wire lq_pop = (lq_n != 3'd0) && (!w_v || w_rdy);
    wire pgo = (ph == P_OUT) && (outn < nout_q) && ({1'b0, lq_n} - {3'd0, lq_pop} + (hr_q ? 4'd2 : 4'd1) <= 4'd4);
    // select (combinational over the registered staging heads)
    reg [EW-1:0] sel_e [0:3]; reg [2:0] sel_n; reg [7:0] sel_take [0:DEL-1]; reg [DEL-1:0] sel_pop;
    always @* begin : selc
        integer r_, idx;
        reg [7:0] hm;
        r_ = 0;
        for (s = 0; s < 4; s = s + 1) sel_e[s] = {EW{1'b0}};
        for (l = 0; l < DEL; l = l + 1) begin
            sel_take[l] = 8'd0;
            hm = (st_n[l] != 2'd0) ? (st_m[l][0] & ~dn[l]) : 8'd0;
            for (i = 0; i < 8; i = i + 1) if (hm[i]) begin
                if (r_ < 4) begin if (!(MUT == 2 && r_ == 3)) sel_e[r_] = st_e[l][0][i]; sel_take[l][i] = 1'b1; end
                r_ = r_ + 1;
            end
            sel_pop[l] = (st_n[l] != 2'd0) && ((hm & ~sel_take[l]) == 8'd0);
        end
        sel_n = (r_ > 4) ? 3'd4 : 3'(r_);
    end
    wire ins_live = (ph == P_INS);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= P_IDLE; fault <= 1'b0; done <= 1'b0; w_v <= 1'b0; w_addr <= 40'd0; w_mask <= 16'd0; w_data <= '0;
            stat_cycles <= 32'd0; stat_ins <= 32'd0; stat_surv <= 32'd0;
            n_q <= 12'd1; k_q <= 13'd1; nel <= 19'd0; g_q <= 8'd1; gb_q <= 8'd0; pf_q <= 16'd1; nout_q <= 13'd1; ob_q <= 40'd0; rb_q <= 40'd0; hr_q <= 1'b0;
            tot_q <= 24'd0; cact_q <= '0; tc_q <= '0; ts_q <= 2'd0; rcv <= 24'd0; tau <= '0;
            d1_v <= '0; d2_v <= '0; fpop_q <= '0; ld_v <= '0; e1_v <= 1'b0; e2_v <= 1'b0;
            rnd <= '0; par <= 1'b0; outn <= 13'd0; wrn <= 13'd0; line <= 9'd0; lq_n <= 3'd0; lq_h <= 2'd0; lq_t <= 2'd0;
            for (l = 0; l < DEL; l = l + 1) begin cr[l] <= 8'(CAP); st_n[l] <= 2'd0; dn[l] <= 8'd0; occ[l] <= 8'd0; end
            bv <= 1'b0;
        end else begin
            done <= 1'b0;
            if (busy) stat_cycles <= stat_cycles + 32'd1;
            fpop_q <= fpop;
            tot_q <= 24'(g_q) * 24'(pf_q);           // from the registered configuration (no input -> multiplier path)
            // ---- credits: reserve at dispatch, return one edge after a FIFO pop
            for (l = 0; l < DEL; l = l + 1) begin
                cr[l] <= cr[l] - ((MUT == 3) ? 8'd0 : 8'(del_reserve[l])) + 8'(fpop_q[l]);
                if (del_reserve[l] && cr[l] == 8'd0) fault <= 1'b1;
                if (fo[l]) fault <= 1'b1;
                occ[l] <= occ[l] + 8'(d2_v[l]) - 8'(fpop[l]);
            end
            // ---- decode
            for (l = 0; l < DEL; l = l + 1) begin
                d1_v[l] <= del_valid[l];
                d1_q[l] <= del_flit[l*PWT + FW + 16 +: 8] - gb_q;
                d1_gi[l] <= del_flit[l*PWT + FW +: 16];
                d1_d[l] <= del_flit[l*PWT +: FW];
                d1_qpf[l] <= 24'(8'(del_flit[l*PWT + FW + 16 +: 8] - gb_q)) * 24'(pf_q);
                if (del_valid[l] && !del_flit[l*PWT + PWT - 1]) fault <= 1'b1;
                d2_v[l] <= d1_v[l];
                begin : dec
                    reg [23:0] f_; reg [31:0] vv, id_; reg [23:0] j_; reg [EW-1:0] e_;
                    f_ = 24'(d1_gi[l]) - d1_qpf[l];
                    if (d1_v[l] && (d1_q[l] >= g_q || f_ >= 24'(pf_q))) fault <= 1'b1;
                    for (s = 0; s < 8; s = s + 1) begin
                        vv = d1_d[l][32*s +: 32]; id_ = d1_d[l][32*(8+s) +: 32];
                        j_ = {f_[20:0], 3'(s)};
                        e_ = {1'b1, okey(vv), (MUT == 1) ? id_ : ~id_, ~d1_q[l][6:0], ~j_[10:0], (vv == 32'h8000_0000)};
                        if (vv == 32'hFFFF_FFFF) e_ = {EW{1'b0}};                       // the sender's pad slot
                        else if (d1_v[l] && vv[30:23] == 8'hFF && vv[22:0] != 23'd0) fault <= 1'b1;
                        d2_e[l][EW*s +: EW] <= e_;
                    end
                end
            end
            if (ph == P_INS) begin : cnt
                reg [18:0] a_;
                a_ = nel;
                for (l = 0; l < DEL; l = l + 1) if (d2_v[l]) for (s = 0; s < 8; s = s + 1) a_ = a_ + 19'(d2_e[l][EW*s + EW - 1]);
                nel <= a_;
            end
            if (ph == P_INS) rcv <= rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3]);
            if ((rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3])) > tot_q && ph == P_INS) fault <= 1'b1;
            // ---- tau (2 edges behind the array)
            tau <= tau_b;
            // ---- staging: land (mask against tau), then slots; select consumes slot 0
            for (l = 0; l < DEL; l = l + 1) begin
                ld_v[l] <= fpop[l];
                for (s = 0; s < 8; s = s + 1) begin
                    ld_e[l][s] <= fd[l][EW*s +: EW];
                    ld_m[l][s] <= fd[l][EW*s + EW - 1] && (vkey(fd[l][EW*s +: EW]) > tau);
                end
                begin : stg
                    reg [1:0] n_;
                    n_ = st_n[l];
                    if (sel_pop[l] && ins_live) begin
                        st_e[l][0] <= st_e[l][1]; st_m[l][0] <= st_m[l][1];
                        st_e[l][1] <= st_e[l][2]; st_m[l][1] <= st_m[l][2];
                        n_ = n_ - 2'd1; dn[l] <= 8'd0;
                    end else if (ins_live) dn[l] <= dn[l] | sel_take[l];
                    if (ld_v[l]) begin
                        // the new entry lands at index n_ (after this edge's shift)
                        if (n_ == 2'd0) begin st_e[l][0] <= ld_e[l]; st_m[l][0] <= ld_m[l]; end
                        else if (n_ == 2'd1) begin st_e[l][1] <= ld_e[l]; st_m[l][1] <= ld_m[l]; end
                        else begin st_e[l][2] <= ld_e[l]; st_m[l][2] <= ld_m[l]; end
                        n_ = n_ + 2'd1;
                    end
                    st_n[l] <= n_;
                end
            end
            // ---- entry: select -> e1 -> (compares) e2 -> rank-sorted block -> broadcast insertion
            e1_v <= ins_live && (sel_n != 3'd0);
            for (s = 0; s < 4; s = s + 1) e1[s] <= sel_e[s];
            if (ins_live && sel_n != 3'd0) stat_surv <= stat_surv + 32'(sel_n);
            e2_v <= e1_v;
            for (s = 0; s < 4; s = s + 1) e2[s] <= e1[s];
            e2_ge[0] <= vkey(e1[0]) >= vkey(e1[1]); e2_ge[1] <= vkey(e1[0]) >= vkey(e1[2]); e2_ge[2] <= vkey(e1[0]) >= vkey(e1[3]);
            e2_ge[3] <= vkey(e1[1]) >= vkey(e1[2]); e2_ge[4] <= vkey(e1[1]) >= vkey(e1[3]); e2_ge[5] <= vkey(e1[2]) >= vkey(e1[3]);
            // ---- the array (X / bk: reset-free data flops in their own block below)
            if (ph == P_INS || ph == P_DRAIN) begin
                bv <= e2_v;
                if (e2_v) stat_ins <= stat_ins + 32'd1;
            end
            // ---- output (P_OUT): cells 0 .. 3 -> one O line (+ one R line) an edge
            begin : pk
                reg [2:0] n_; reg [1:0] t_; reg [12:0] cnt_; reg [FW-1:0] od_, rd_; reg [15:0] m_;
                n_ = lq_n; t_ = lq_t;
                if (lq_pop) begin
                    w_v <= 1'b1; w_addr <= lq_a[lq_h]; w_mask <= lq_m[lq_h]; w_data <= lq_d[lq_h];
                    lq_h <= lq_h + 2'd1; n_ = n_ - 3'd1;
                end else if (w_v && w_rdy) w_v <= 1'b0;
                if (pgo) begin
                    cnt_ = ((nout_q - outn) >= 13'd16) ? 13'd16 : (nout_q - outn);
                    m_ = (cnt_ == 13'd16) ? 16'hFFFF : 16'((17'd1 << cnt_[4:0]) - 17'd1);
                    for (i = 0; i < 16; i = i + 1) begin
                        od_[32*i +: 32] = (13'(i) < cnt_) ? ((MUT == 1) ? X[i / 4][i % 4][50:19] : ~X[i / 4][i % 4][50:19]) : 32'd0;
                        rd_[32*i +: 32] = (13'(i) < cnt_) ? unkey(X[i / 4][i % 4][82:51], X[i / 4][i % 4][0]) : 32'd0;
                    end
                    lq_d[t_] <= od_; lq_a[t_] <= ob_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 2'd1; n_ = n_ + 3'd1;
                    if (hr_q) begin lq_d[t_] <= rd_; lq_a[t_] <= rb_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 2'd1; n_ = n_ + 3'd1; end
                    line <= line + 9'd1; outn <= outn + cnt_;
                end
                lq_n <= n_; lq_t <= t_;
            end
            // ---- phase control
            case (ph)
                P_IDLE: if (start) begin
                    n_q <= cfg_n; k_q <= cfg_k; nel <= 19'd0; g_q <= cfg_g; gb_q <= cfg_gbase; pf_q <= cfg_pf; nout_q <= cfg_nout;
                    ob_q <= cfg_obase; rb_q <= cfg_rbase; hr_q <= cfg_has_r;
                    rcv <= 24'd0;
                    cact_q <= CB'((cfg_nout + 13'd3) >> 2);
                    begin : tp
                        reg [12:0] p_;
                        p_ = cfg_nout - 13'd1;
                        tc_q <= CB'(p_ >> 2); ts_q <= p_[1:0];
                    end
                    bv <= 1'b0;
                    stat_ins <= 32'd0; stat_surv <= 32'd0; stat_cycles <= 32'd0;
                    outn <= 13'd0; wrn <= 13'd0; line <= 9'd0; rnd <= '0; par <= 1'b0;
                    ph <= P_INS;
                end
                P_INS: if (rcv == tot_q && d1_v == '0 && d2_v == '0 && occ[0] == 8'd0 && occ[1] == 8'd0 && occ[2] == 8'd0 && occ[3] == 8'd0 && ld_v == '0 &&
                           st_n[0] == 2'd0 && st_n[1] == 2'd0 && st_n[2] == 2'd0 && st_n[3] == 2'd0)
                    ph <= P_DRAIN;
                P_DRAIN: if (!e1_v && !e2_v && !bv) begin
                    ph <= P_INV;
                    // O.n must be min(k, the group's elements): a record whose O.n disagrees faults (E_RANGE)
                    if (19'(nout_q) != ((19'(k_q) < nel) ? 19'(k_q) : nel)) fault <= 1'b1;
                end
                P_INV: ph <= (MUT == 4) ? P_OUT : P_RS;
                P_RS: begin ph <= P_OETS; rnd <= '0; par <= 1'b0; end
                P_OETS: begin
                    par <= ~par; rnd <= rnd + 1'b1;
                    if (rnd + 1'b1 >= (CB+1)'(cact_q)) ph <= P_OUT;
                end
                P_OUT: if (outn == nout_q && lq_n == 3'd0) ph <= P_FLUSH;
                P_FLUSH: if (!w_v) begin ph <= P_IDLE; done <= 1'b1; end
                default: ph <= P_IDLE;
            endcase
        end
    end
    // ---------------------------------------------------------------- the array: reset-free data flops (cleared at start)
    always @(posedge clk) begin : arr_b
        integer c, s;
        if (ph == P_IDLE) begin
            if (start) for (c = 0; c < C; c = c + 1) for (s = 0; s < 4; s = s + 1) X[c][s] <= {EW{1'b0}};
        end else begin
            case (ph)
                P_INS, P_DRAIN: begin
                    begin : entry
                        reg [1:0] r0, r1, r2, r3;
                        r0 = 2'(!e2_ge[0]) + 2'(!e2_ge[1]) + 2'(!e2_ge[2]);
                        r1 = 2'(e2_ge[0]) + 2'(!e2_ge[3]) + 2'(!e2_ge[4]);
                        r2 = 2'(e2_ge[1]) + 2'(e2_ge[3]) + 2'(!e2_ge[5]);
                        r3 = 2'(e2_ge[2]) + 2'(e2_ge[4]) + 2'(e2_ge[5]);
                        for (integer g = 0; g < NB; g = g + 1)
                            for (s = 0; s < 4; s = s + 1)
                                bk[g][s] <= ((r0 == 2'(s)) ? e2[0] : {EW{1'b0}}) | ((r1 == 2'(s)) ? e2[1] : {EW{1'b0}}) |
                                            ((r2 == 2'(s)) ? e2[2] : {EW{1'b0}}) | ((r3 == 2'(s)) ? e2[3] : {EW{1'b0}});
                    end
                    if (bv) for (c = 0; c < C; c = c + 1) for (s = 0; s < 4; s = s + 1) X[c][s] <= ins[c * 4 + s];
                end
                P_INV: begin
                    for (c = 0; c < C; c = c + 1) for (s = 0; s < 4; s = s + 1)
                        if (13'(c * 4 + s) >= nout_q) X[c][s] <= {EW{1'b0}};
                end
                P_RS: begin
                    for (c = 0; c < C; c = c + 1) begin : rs
                        reg [4*EW-1:0] o_;
                        o_ = rsort({X[c][3], X[c][2], X[c][1], X[c][0]});
                        for (s = 0; s < 4; s = s + 1) X[c][s] <= o_[EW*s +: EW];
                    end
                end
                P_OETS: begin
                    for (c = 0; c < C; c = c + 1) begin
                        if (lowc(c, par)) for (s = 0; s < 4; s = s + 1) X[c][s] <= mb[c][s];
                        else if (c + 1 < C && lowc(c + 1, par)) for (s = 0; s < 4; s = s + 1) X[c][s] <= mt[(c + 1 < C) ? c + 1 : c][s];
                    end
                end
                P_OUT: if (pgo) begin
                    for (c = 0; c < C; c = c + 1) for (s = 0; s < 4; s = s + 1) X[c][s] <= (c + 4 < C) ? X[(c + 4 < C) ? c + 4 : c][s] : {EW{1'b0}};
                end
                default: ;
            endcase
        end
    end
    // FIFO pop into the landing register: room counted on registered state (3 slots + landing)
    always @* for (integer l2 = 0; l2 < DEL; l2 = l2 + 1)
        fpop[l2] = !fe[l2] && (ph == P_INS) && ({1'b0, st_n[l2]} + 3'(ld_v[l2]) < 3'd3);
endmodule
`default_nettype wire
