`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_ret_root_p -- PIPELINED S81 region root (CLAUDE S81-PH gather, 2026-10-06).
//
// Same function as the W10 ot_v41_ret_root (rtl/v41rom/ot_v41_ret.sv; D-entry pairing buffer, QD-entry input queue,
// FP32 sibling adds, complete rows out) restructured for 1.2 GHz with margin.  The W10 root decides every candidate in
// ONE cycle (queue head mux -> norm -> D sibling compares -> priority chain -> parent / buffer update): root_m1
// -4.36 ns.  Measured on the way here (tile_m1 post-place, route SDC): two norm iterations per stage -388 ps, the
// prefix-OR priority decision loop -308 ps, D tag compares at S1 -249 ps, queue write gated by the pop -174 ps.
//   P   input: norm(i_t), ONE of norm's 5 iterations per registered stage (norm is idempotent: the W10 root applies it
//       at the queue head instead; same tag).  The parent tag is normalised the same way in the adder's delay line.
//   Q   input queue = QD-entry flop memory (every input word is written; a full queue is a fault) + registered head
//       (kept copies); the head mux is pointer-addressed only
//   S1  candidate = adder result (priority, as W10) else queue head (NC kept copies).  The buffer keeps, per slot,
//       the KEY of its partial = the tag its sibling must carry ({row, pos, lo ^ 2^k, k, nseg}), so a sibling test is
//       one 32-bit equality.  Match m = valid & key == candidate (a slot inserted by the previous decision is
//       compared through its pending write register); forward flag sp = key(previous candidate) == candidate.
//   S2  decision from registers only: hit = sp & previous inserted ? that slot : m (one-hot); free slot F = a
//       register (lowest free slot of the previous cycle's state, minus the slot it inserted).  Add (remove hit),
//       insert (at F), complete (row out) or fault (no free slot).  Valid bits update here; key/data one cycle later.
//   S3  add operands: one-hot AND-OR read of the hit slot's data, left = lower lo (W10 rule), parent tag (depends
//       only on the candidate: siblings differ in lo bit k), error OR.
//   ADD ot_fp32_add_rne_deep (SPLIT 7, bit-identical to the qualified ot_fp32_add_rne_pipe, LAT 8); tag and valid on a
//       local delay line (norm iterations in stages 0..4, last stage replicated: kept copies drive the S1 compares).
// v3 (tile_m2 post-CTS, route SDC: free slot -542, s2_m compares -275, deep add s2->s3 -162 ripple, h_d -224, fault
// multi-match -307): the free slot comes from a FREE LIST (init counter, then a FIFO of freed slot indices, two-entry
// prefetch), never a 128-bit priority in the decision loop (a freed slot is allocatable ~3 cycles after its add, so
// "buffer full" can fault up to 4 entries early); the S1 candidate is a REGISTER per compare group (chosen one
// cycle ahead from registers: the adder delay line or the two-entry queue head prefetch), the slot inserted by the
// previous decision is compared once against its pending write key (s2_pend) instead of a per-slot mux; the
// multiple-match fault is a two-stage group count; the adder uses kept Kogge-Stone adds (KS 1).
// Arithmetic and pairing are the W10 ones (siblings are unique; IEEE add commutes bit for bit): every row's value is
// identical, rows of a root may leave in another order.  Deviations, all in malformed streams only (a duplicate
// partial tag: two buffer entries or two candidates siblings of the same partial): W10 pairs with the lowest slot,
// this root raises fault (fail closed; checked one cycle later off the decision loop).  A slot freed by an add
// becomes allocatable one cycle later (W10: at once), so "buffer full" can fault one cycle early at D - 1 entries.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_ret_root_p #(
    parameter integer D  = 128,
    parameter integer QD = 128,
    parameter integer NC = 16                // kept candidate / write-key copies (each serves D/NC slots)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [2:0]  r_pos,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         fault
);
    // ot_v41_ret_pkg functions, local (yosys-native synthesis keeps the generator's [0:0] port names)
    function automatic complete(input [31:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction
    // sibling(a, b) of ot_v41_ret_pkg  <=>  key(a) == b
    function automatic [31:0] key(input [31:0] a);
        key = {a[31:13], a[12:8] ^ (5'd1 << a[7:5]), a[7:5], a[4:0]};
    endfunction
    // one iteration of ot_v41_ret_pkg::norm (which is exactly 5 of these in sequence)
    function automatic [31:0] norm_step(input [31:0] t);
        reg [18:0] row; reg [4:0] lo, n; reg [2:0] kk;
        begin
            {row, lo, kk, n} = t;
            if (!(lo == 5'd0 && (6'd1 << kk) >= {1'b0, n}) && lo[kk] == 1'b0 && ({1'b0, lo} + (6'd1 << kk)) >= {1'b0, n})
                kk = kk + 3'd1;
            norm_step = {row, lo, kk, n};
        end
    endfunction
    function automatic [D-1:0] lowest(input [D-1:0] x);   // lowest set bit, prefix-OR
        reg [D-1:0] p; integer s, j;
        begin
            p = x;
            for (s = 1; s < D; s = s * 2)
                for (j = D - 1; j >= s; j = j - 1) p[j] = p[j] | p[j - s];
            lowest = x & ~{p[D-2:0], 1'b0};
        end
    endfunction
    localparam integer QW = $clog2(QD);
    localparam integer LAT = 8;              // ot_fp32_add_rne_deep SPLIT 3'b111
    localparam integer SG = D / NC;          // slots per copy
    localparam integer NP = 5;               // input norm stages
    integer k, c;

    // ------------------------------------------------------------ P: normalised input (one norm iteration a stage)
    reg [NP-1:0] p_v; reg [31:0] p_t [0:NP-1]; reg [31:0] p_d [0:NP-1]; reg [NP-1:0] p_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) p_v <= {NP{1'b0}}; else p_v <= {p_v[NP-2:0], i_v};
    always @(posedge clk) begin
        p_t[0] <= norm_step(i_t); p_d[0] <= i_d; p_e[0] <= i_e;
        for (c = 1; c < NP; c = c + 1) begin p_t[c] <= norm_step(p_t[c-1]); p_d[c] <= p_d[c-1]; p_e[c] <= p_e[c-1]; end
    end
    wire n_v = p_v[NP-1]; wire [31:0] n_t = p_t[NP-1], n_d = p_d[NP-1]; wire n_e = p_e[NP-1];

    // ------------------------------------------------------------ adder return (tag / valid delay line)
    reg [LAT-2:0] dv;
    reg [33*(LAT-1)-1:0] dtg;
    (* keep *) reg [NC-1:0] sv_c;
    reg st_e;
    reg sv;
    wire [31:0] sum; wire [1:0] err; wire sv_add;
    reg add; reg [31:0] add_a, add_b; reg [32:0] tag_in;
    wire [31:0] dtg_last = dtg[33*(LAT-2) + 1 +: 32];

    // ------------------------------------------------------------ queue: memory + registered two-level read + head
    // v4 (tile_m3 post-route -83 at the 128-entry head mux into pq_*): the memory read is a two-level REGISTERED read
    // (R1: 16 groups x 8:1 at the kept read pointer copies, R2: 16:1), landing in a PFD-entry prefetch FIFO; reads are
    // issued against a credit counter (prefetch entries + reads in flight <= PFD), from registers only.  H / P as v3.
    localparam integer NQ = 5;
    localparam integer QG = QD / 8;          // read groups of 8 entries
    localparam integer QGW = (QG > 1) ? $clog2(QG) : 1;
    localparam integer PFD = 4;              // prefetch entries (covers the 3-cycle issue -> pop loop)
    reg [64:0] qm [0:QD-1];                  // {e, d32, t32}
    reg [QW-1:0] qw;
    (* keep *) reg [QW-1:0] qr_c [0:NQ-1];
    reg [QW:0] mc; reg mc_nz;
    (* keep *) reg [NC-1:0] hv_c;
    reg hv; reg [31:0] h_d; reg h_e; reg [31:0] h_t;
    reg pv; reg [31:0] pq_t, pq_d; reg pq_e;
    reg [2:0] cr;                            // prefetch entries + reads in flight (0 .. PFD)
    reg r1_v, r2_v; reg [QGW-1:0] r1_hi;
    reg [64:0] r1_g [0:QG-1];
    reg [64:0] r2_w;
    reg [64:0] pf [0:PFD-1];
    reg [1:0] pf_wp, pf_rp; reg [2:0] pf_n; reg pf_nz;
    wire take = !hv || !sv;                  // H is free or popped (W10: use_q = !sv && queue not empty)
    wire p_free = !pv || take;
    wire pf_pop = p_free && pf_nz;
    wire rd_go = mc_nz && (cr < PFD);        // registers only
    wire q_full = mc == QD;
    wire wr_mem = n_v;                       // a word into a full queue overwrites and faults (fail closed)
    wire [QW:0] mc_n = mc + (wr_mem ? 1'b1 : 1'b0) - (rd_go ? 1'b1 : 1'b0);
    wire [2:0] pf_n_n = pf_n + (r2_v ? 3'd1 : 3'd0) - (pf_pop ? 3'd1 : 3'd0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            qw <= 0; mc <= 0; mc_nz <= 1'b0; hv <= 1'b0; hv_c <= {NC{1'b0}}; pv <= 1'b0;
            for (c = 0; c < NQ; c = c + 1) qr_c[c] <= 0;
            cr <= 3'd0; r1_v <= 1'b0; r2_v <= 1'b0; pf_wp <= 2'd0; pf_rp <= 2'd0; pf_n <= 3'd0; pf_nz <= 1'b0;
        end else begin
            if (wr_mem) qw <= qw + 1'b1;
            if (rd_go) for (c = 0; c < NQ; c = c + 1) qr_c[c] <= qr_c[c] + 1'b1;
            mc <= mc_n; mc_nz <= mc_n != 0;
            cr <= cr + (rd_go ? 3'd1 : 3'd0) - (pf_pop ? 3'd1 : 3'd0);
            r1_v <= rd_go; r2_v <= r1_v;
            if (r2_v) pf_wp <= pf_wp + 2'd1;
            if (pf_pop) pf_rp <= pf_rp + 2'd1;
            pf_n <= pf_n_n; pf_nz <= pf_n_n != 0;
            if (take) begin hv <= pv; hv_c <= {NC{pv}}; end
            if (p_free) pv <= pf_nz;
        end
    integer gq;
    always @(posedge clk) begin
        if (wr_mem) qm[qw] <= {n_e, n_d, n_t};
        // R1: per group, entry (group * 8 + low pointer bits); the NQ kept pointer copies split the 65 bits
        for (gq = 0; gq < QG; gq = gq + 1)
            for (c = 0; c < NQ; c = c + 1)
                r1_g[gq][13*c +: 13] <= qm[gq * 8 + qr_c[c][2:0]][13*c +: 13];
        r1_hi <= qr_c[0][QW-1:3];
        r2_w <= r1_g[r1_hi];
        if (r2_v) pf[pf_wp] <= r2_w;
        if (take) begin h_t <= pq_t; h_d <= pq_d; h_e <= pq_e; end
        if (pf_pop) begin pq_t <= pf[pf_rp][31:0]; pq_d <= pf[pf_rp][63:32]; pq_e <= pf[pf_rp][64]; end
    end

    // ------------------------------------------------------------ buffer: valid, key, data, error
    reg [D-1:0] bv;
    reg [31:0] bk [0:D-1];
    reg [31:0] bd [0:D-1];
    reg [D-1:0] be;

    // ------------------------------------------------------------ S1: candidate (registered per group), compares
    // cand_c = this cycle's candidate tag: the adder result's tag when sv, else the queue head; chosen one cycle
    // ahead from registers (sv next = dv[LAT-2], head next = take ? P : H)
    (* keep *) reg [31:0] cand_c [0:NC-1];
    always @(posedge clk)
        for (c = 0; c < NC; c = c + 1)
            cand_c[c] <= dv[LAT-2] ? dtg_last : ((!hv_c[c] || !sv_c[c]) ? pq_t : h_t);
    wire        x_v = sv || hv;
    wire [31:0] x_d = sv ? sum : h_d;
    wire        x_e = sv ? (st_e | err != 2'd0) : h_e;
    wire [31:0] x_t0 = cand_c[0];
    reg [D-1:0] ins_r;                       // slot inserted by the previous decision (one-hot)
    reg ins_any;
    (* keep *) reg [31:0] w_k_c [0:NC-1];   // its key / data / error, kept copies (written into the slot now)
    (* keep *) reg [31:0] w_d_c [0:NC-1];
    (* keep *) reg [NC-1:0] w_e_c;
    reg [D-1:0] m1;
    always @* begin                          // the pending slot's bk is stale: masked, matched by s2_pend
        for (k = 0; k < D; k = k + 1)
            m1[k] = bv[k] && !ins_r[k] && (bk[k] == cand_c[k / SG]);
    end
    reg s2_v, s2_cmp, s2_sp, s2_e, s2_pend; reg [31:0] s2_d, s2_t, s2_k;
    reg [D-1:0] s2_m, s2_ins;
    always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= x_v;
    always @(posedge clk) begin
        s2_t <= x_t0; s2_k <= key(x_t0); s2_d <= x_d; s2_e <= x_e;
        s2_cmp <= complete(x_t0);
        s2_sp <= s2_v && s2_k == x_t0;       // the candidate is the sibling of the one now deciding
        s2_pend <= ins_any && w_k_c[0] == x_t0;   // ... of the one the previous decision inserted
        s2_ins <= ins_r;
        s2_m <= m1;
    end

    // ------------------------------------------------------------ free list (init counter, FIFO, 2-entry prefetch)
    localparam integer AW = $clog2(D);
    // v4 (tile_m3 -46..-63 on fl_rp / ic / fr_r / nb_i / fl_n: the v3 A <- B <- source take chain rode on dec_ins):
    // two one-hot free slots FA0 / FA1 (ping-pong: the decision uses FA[fsel]; an insert clears it and flips fsel),
    // refilled from a registered encoded head H (init counter or free-list FIFO) when a register says one is empty;
    // nothing between dec_ins and the free-list pointers.  Prefetched free slots: FA0, FA1, H (3).
    reg [D-1:0] fa0, fa1; reg [1:0] fa_v; reg fsel;
    wire [D-1:0] fr_r = fsel ? fa1 : fa0;   // free slot for this decision (one-hot)
    wire fr_any = fa_v[fsel];
    reg nb_v; reg [AW-1:0] nb_i;             // H: prefetched next free slot (encoded)
    reg [AW:0] ic;                           // init allocation counter 0 .. D
    reg [AW-1:0] flm [0:D-1];
    reg [AW-1:0] fl_wp, fl_rp; reg [AW:0] fl_n; reg fl_nz;
    reg fp_v; reg [AW-1:0] fp_i;             // freed slot index (encoded one cycle after the add's removal)

    // ------------------------------------------------------------ S2: decision (registers in, one-hot out)
`ifdef S81PH_MUT_NOFWD
    wire fwd = 1'b0;                                               // MUTANT: no forwarding of the previous insert
`else
    wire fwd = s2_sp && ins_any;
`endif
    wire [D-1:0] hit_oh = fwd ? ins_r : (s2_pend ? s2_ins : s2_m);
    wire hit_any = fwd || s2_pend || (|s2_m);
    wire live = s2_v && !s2_cmp;
    wire dec_add = live && hit_any;
    wire dec_ins = live && !hit_any && fr_any;
    wire rf_need = !fa_v[0] || !fa_v[1];     // registers only
    wire rf_x = fa_v[0];                     // refill FA1 only when FA0 is valid
    wire a_take = nb_v && rf_need;
    wire b_free = !nb_v || a_take;
    wire src_init = !ic[AW];
    wire src_v = src_init || fl_nz;
    wire [AW-1:0] src_i = src_init ? ic[AW-1:0] : flm[fl_rp];
    wire src_pop = b_free && src_v;
    wire fl_pop = src_pop && !src_init;
    wire [AW:0] fl_n_n = fl_n + (fp_v ? 1'b1 : 1'b0) - (fl_pop ? 1'b1 : 1'b0);
    wire [2:0] s2_kk = s2_t[7:5];
    wire [4:0] s2_lo = s2_t[12:8];
    wire [31:0] s2_par = {s2_t[31:13], s2_lo & ~(5'd1 << s2_kk), s2_kk + 3'd1, s2_t[4:0]};   // normalised in the delay line
    wire s2_right = s2_lo[s2_kk];            // candidate is the right sibling: buffer word is the left operand
    reg a3_v, a3_right, a3_e; reg [31:0] a3_d, a3_t; reg [D-1:0] a3_oh;
    reg [D-1:0] rm_r, e_m; reg rm_any; reg e_dup;
    localparam integer NG = D / 8;
    reg [NG-1:0] g_any, g_two; reg e_chk;
    function automatic two_or_more(input [D-1:0] x);   // x zero-extended: x & (x - 1) != 0 <=> two or more set
        two_or_more = |(x & (x - 1'b1));
    endfunction
    integer g;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            bv <= {D{1'b0}}; ins_r <= {D{1'b0}}; ins_any <= 1'b0; fa_v <= 2'b00; fsel <= 1'b0;
            nb_v <= 1'b0; ic <= 0; fl_wp <= 0; fl_rp <= 0; fl_n <= 0; fl_nz <= 1'b0; fp_v <= 1'b0; rm_any <= 1'b0;
            a3_v <= 1'b0; r_v <= 1'b0; fault <= 1'b0; rm_r <= {D{1'b0}}; e_m <= {D{1'b0}}; e_dup <= 1'b0;
            g_any <= {NG{1'b0}}; g_two <= {NG{1'b0}}; e_chk <= 1'b0;
        end else begin
            a3_v <= dec_add;
            ins_r <= dec_ins ? fr_r : {D{1'b0}};
            ins_any <= dec_ins;
            bv <= (bv & ~(dec_add ? hit_oh : {D{1'b0}})) | (dec_ins ? fr_r : {D{1'b0}});
            begin : fa_upd
                reg [1:0] nv;
                nv = fa_v;
                if (dec_ins) nv[fsel] = 1'b0;
                if (a_take) nv[rf_x] = 1'b1;
                fa_v <= nv;
                if (!nv[fsel] && nv[!fsel]) fsel <= !fsel;
            end
            if (b_free) begin nb_v <= src_v; nb_i <= src_i; end
            if (src_pop && src_init) ic <= ic + 1'b1;
            if (fl_pop) fl_rp <= fl_rp + 1'b1;
            if (fp_v) fl_wp <= fl_wp + 1'b1;
            fl_n <= fl_n_n; fl_nz <= fl_n_n != 0;
            rm_r <= dec_add ? hit_oh : {D{1'b0}};
            rm_any <= dec_add;
            fp_v <= rm_any;
            r_v <= s2_v && s2_cmp;
            // malformed-stream checks, off the loop: a match on the slot the previous add removed, forwarding and a
            // buffer match at once, more than one buffer match (two-stage group count)
            e_dup <= live && ((|(s2_m & rm_r)) || ((fwd || s2_pend) && (|s2_m)) || (fwd && s2_pend));
            e_m <= live ? (s2_m | (s2_pend ? s2_ins : {D{1'b0}})) : {D{1'b0}};
            for (g = 0; g < NG; g = g + 1) begin
                g_any[g] <= |e_m[8*g +: 8];
                g_two[g] <= two_or_more({{(D-8){1'b0}}, e_m[8*g +: 8]});
            end
            e_chk <= 1'b1;
            if (n_v && q_full) fault <= 1'b1;
            if (live && !hit_any && !fr_any) fault <= 1'b1;
            if (e_dup || (|g_two) || two_or_more({{(D-NG){1'b0}}, g_any})) fault <= 1'b1;
        end
    always @(posedge clk)
        if (a_take) begin
            if (rf_x) for (k = 0; k < D; k = k + 1) fa1[k] <= nb_i == k[AW-1:0];
            else      for (k = 0; k < D; k = k + 1) fa0[k] <= nb_i == k[AW-1:0];
        end
    always @(posedge clk) begin
        fp_i <= {AW{1'b0}};
        for (k = 0; k < D; k = k + 1) if (rm_r[k]) fp_i <= k[AW-1:0];
        if (fp_v) flm[fl_wp] <= fp_i;
    end
    always @(posedge clk) begin
        for (k = 0; k < D; k = k + 1)
            if (ins_r[k]) begin bk[k] <= w_k_c[k / SG]; bd[k] <= w_d_c[k / SG]; be[k] <= w_e_c[k / SG]; end
        for (c = 0; c < NC; c = c + 1) begin w_k_c[c] <= s2_k; w_d_c[c] <= s2_d; w_e_c[c] <= s2_e; end
        a3_oh <= hit_oh; a3_d <= s2_d; a3_e <= s2_e; a3_t <= s2_par; a3_right <= s2_right;
        r_row <= s2_t[28:13]; r_pos <= s2_t[31:29]; r_fp32 <= s2_d; r_e <= s2_e;
        r_bf16 <= ({1'b0, s2_d} + 33'h7FFF + {32'd0, s2_d[16]}) >> 16;
    end

    // ------------------------------------------------------------ S3 / S4: operands
    // v4 (tile_m3 -82 on add_a / add_b: one 128-way AND-OR): two registered OR levels, S3 = 16 groups of D/16, S4 =
    // the 16 group words (+1 add cycle)
    localparam integer OG = 16, OS = D / OG;
    reg [31:0] o1_d [0:OG-1]; reg [OG-1:0] o1_e;
    reg a4_v, a4_right, a4_e; reg [31:0] a4_d, a4_t;
    integer og;
    always @(posedge clk) begin
        for (og = 0; og < OG; og = og + 1) begin : g_o1
            reg [31:0] bs; reg es;
            bs = 32'd0; es = 1'b0;
            for (k = og * OS; k < (og + 1) * OS; k = k + 1) begin
                bs = bs | ({32{a3_oh[k]}} & bd[k]);
                es = es | (a3_oh[k] & be[k]);
            end
            o1_d[og] <= bs; o1_e[og] <= es;
        end
        a4_d <= a3_d; a4_t <= a3_t; a4_right <= a3_right; a4_e <= a3_e;
    end
    reg [31:0] b_sel; reg e_sel;
    always @* begin
        b_sel = 32'd0;
        for (og = 0; og < OG; og = og + 1) b_sel = b_sel | o1_d[og];
        e_sel = |o1_e;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin a4_v <= 1'b0; add <= 1'b0; end else begin a4_v <= a3_v; add <= a4_v; end
    always @(posedge clk) begin
        if (a4_v) begin
            if (a4_right) begin add_a <= b_sel; add_b <= a4_d; end
            else begin add_a <= a4_d; add_b <= b_sel; end
        end
        tag_in <= {a4_t, e_sel | a4_e};
    end
    ot_fp32_add_rne_deep #(.SPLIT(3'b111), .KS(1)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(add_a), .b(add_b),
        .y(sum), .err(err), .valid_out(sv_add));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dv <= 0; sv_c <= {NC{1'b0}}; sv <= 1'b0; end
        else begin
            dv <= {dv[LAT-3:0], add};
            sv_c <= {NC{dv[LAT-2]}}; sv <= dv[LAT-2];
        end
    always @(posedge clk) begin
        // delay line stage j < 5 applies norm iteration j to the parent tag (5 iterations = norm)
        for (c = 0; c < LAT - 1; c = c + 1)
            if (c < 5) dtg[33*c +: 33] <= {norm_step(c == 0 ? tag_in[32:1] : dtg[33*(c-1) + 1 +: 32]),
                                           (c == 0) ? tag_in[0] : dtg[33*(c-1)]};
            else dtg[33*c +: 33] <= dtg[33*(c-1) +: 33];
        st_e <= dtg[33*(LAT-2)];
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && sv_add !== sv) $error("ot_s81ph_ret_root_p: adder latency != %0d", LAT);
    initial if (D % NC != 0 || D < 2) $fatal(1, "ot_s81ph_ret_root_p: D %% NC");
`endif
endmodule
