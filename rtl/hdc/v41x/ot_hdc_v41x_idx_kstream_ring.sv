`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_kstream_ring -- one stack's index-key stream over a RING of
// super-blocks (the quarter-per-stack layout, W11).
//
// Identical to ot_hdc_v41x_idx_kstream_range (same key layout, address map,
// generators, ROB, drain and datapath ot_hdc_v41x_idx_kdata; that module is
// left untouched) except that a scan may consist of TWO segments: segment 1
// is a legacy range (cmd_base, cmd_skip, cmd_nkeys) that ends at the ring's
// last, possibly partial, super-block; segment 2 (cmd_base2, cmd_nkeys2, skip
// 0) continues at the ring's first super-block.  The relative block index,
// ROB entries and tags run on across the wrap; only the absolute block (and so
// the address and the pseudo-channel fold) jumps.  cmd_nkeys2 = 0 is a legacy
// one-segment scan.  Beats are emitted from segment 1's first super-block
// start (keys before cmd_skip carry no data; the consumer drops them).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kctl_ring #(
    parameter integer NPC  = 32,
    parameter integer WB   = 32,        // ROB depth in blocks (power of two)
    parameter integer GA   = 24,        // request lookahead in blocks (< WB)
    parameter integer AW   = 24,        // sector address bits
    parameter integer HW   = 20,        // block counter bits
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 cmd_v,
    input  wire [HW-1:0]        cmd_base,     // first block (absolute)
    input  wire [9:0]           cmd_skip,     // keys before the wanted range in the first superblock
    input  wire [HW+9:0]        cmd_nkeys,
    input  wire [HW-1:0]        cmd_base2,    // second segment: first block (its skip is 0)
    input  wire [HW+9:0]        cmd_nkeys2,   // second segment keys (0: none)
    output reg                  busy,
    // HBM request ports, one per pseudo-channel (registered)
    output reg  [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output reg  [NPC*AW-1:0]    req_addr,
    output reg  [NPC*LENW-1:0]  req_len,
    output reg  [NPC*TAGW-1:0]  req_tag,
    // HBM responses (registered at the model): counted here, written to the ROB
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    // drain commands to the datapath (registered)
    output reg                  dr_scale,     // move block `dr_slot` to the scale buffer
    output reg                  dr_quarter,   // emit quarter `dr_q` of block `dr_slot`
    output reg  [$clog2(WB)-1:0] dr_slot,
    output reg  [1:0]           dr_q,
    output reg  [4:0]           dr_fold,      // column c is bank c ^ dr_fold
    output reg  [5:0]           dr_sidx,      // scale-buffer word of the quarter's 16 keys
    output reg  [4:0]           dr_nkeys,     // keys in the quarter (1..16)
    input  wire                 dr_ready      // the datapath can take a quarter this cycle
);
    // Every per-cycle decision reads registers only --
    //   * each generator prepares its next request one cycle ahead (address,
    //     length, block) and issues it the cycle its channel and the lookahead
    //     allow;
    //   * a response is registered, then counted (left: beats still to come per
    //     bank and ROB entry; cc: the entry's column is complete);
    //   * the drain reads the completion of the head entry and the next one per
    //     group of 8 banks from registers sampled a cycle earlier (a completion is
    //     seen one cycle late, never early: a bit is only cleared by the drain of
    //     its own entry).
    // W11 1.2 GHz form (cycle- and bit-identical at the ports to the compare form
    // it replaces, commit 7361f422): no wide compare sits on a decision path.
    //   * 'more' (block < nblk) and 'wrap next' (block + 1 == nblk1) of every
    //     generator and of the drain are registered flags kept by down-counters
    //     (left = nblk - block, l1 = nblk1 - 1 - block, both mod 2^HW);
    //   * the lookahead (nx_hi - d_hi) < GA is a registered flag kept from two
    //     running differences (eg = g_hi - d_hi, dl = nx_hi - d_hi, mod 2^HW);
    //   * a generator's next block's column, sector need and first-super-block
    //     lower bound are prepared one step ahead (registered);
    //   * the drain's head fold and the head/next completion per 8-bank group are
    //     registered (a quarter's 8 columns are the 8 banks b with
    //     b[4:3] == q ^ fold[4:3], so no 32-way permutation is needed);
    //   * the return-queue gate (tag - d_hi) mod 2^BW < WB compares the tag's
    //     entry bits against d_hi's and its upper bits against d_hi's upper
    //     bits and their registered increment.
    localparam integer SW = $clog2(WB);
    localparam integer BW = TAGW - 4; // high tag bits hold the first sector's offset in its 4-sector column
    localparam integer UW = BW - SW;  // tag bits above the ROB entry

    reg            run;
    reg [9:0]      first_skip;
    wire [HW+9:0] cmd_span=cmd_nkeys+{{HW{1'b0}},cmd_skip};
    // segment 2 follows segment 1's (possibly partial) last super-block
    reg [HW-1:0]   base2;
    reg [HW+9:0]   span2;
    reg [10:0]     m2;                         // sbkeys(span2)
    function automatic [HW-1:0] blocks(input [HW+9:0] span);
        blocks = 17 * (span >> 10) + ((span[9:0] != 0) ? (1 + ((span[9:0] + 10'd63) >> 6)) : 0);
    endfunction
    // The command's block counts are not computed in the command cycle.  They are built
    // over the first three run cycles (ph 1: each segment's count from registered pieces;
    // ph 2: their sum; ph 3: the counters load, less the blocks already stepped over), and
    // until then every flag comes from small-count tables filled in the command cycle by
    // cheap tests of the command fields (nblk == k, nblk1 == k for the first few k: a
    // counter moves at most one block a cycle, so it is below 3 before the load).  Exact
    // for every scan whose block counts fit the HW-bit block counter (every scan the
    // address space holds): then a segment of 1,024 keys or more has >= 17 blocks.
    function automatic [4:0] bsmall(input [9:0] lo);   // blocks of a partial super-block
        bsmall = (lo != 0) ? 5'(1 + ((11'(lo) + 11'd63) >> 6)) : 5'd0;
    endfunction
    wire [10:0]    c_lo = {1'b0, cmd_nkeys[9:0]} + {1'b0, cmd_skip};
    wire [10:0]    c_m = ((cmd_nkeys[HW+9:10] != 0) || c_lo[10]) ? 11'd1024 : c_lo;  // sbkeys(cmd_span)
    wire           c_hz1 = (cmd_nkeys[HW+9:10] == 0) && !c_lo[10];    // cmd_span < 1,024
    wire           c_hz2 = (cmd_nkeys2[HW+9:10] == 0);
    wire [4:0]     c_bs1 = bsmall(c_lo[9:0]), c_bs2 = bsmall(cmd_nkeys2[9:0]);
    wire [5:0]     c_bss = {1'b0, c_bs1} + {1'b0, c_bs2};
    wire           c_nz1 = (cmd_nkeys != 0) || (cmd_skip != 0);
    wire           c_more = c_nz1 || (cmd_nkeys2 != 0);
    reg [1:0]      ph;                         // 1..3: the counters are being built
    reg [3:1]      t_n;                        // t_n[k]: nblk == k
    reg [4:2]      t_1;                        // t_1[k]: nblk1 == k
    reg [HW-1:0]   r_hi1, r_hi2, r_b1, r_b2, r_n;
    reg [4:0]      r_sm1, r_sm2;
    // ph 3: the counters' values for a block index j (0..3) after this cycle
    wire [HW-1:0]  l_n [0:3];
    wire [HW-1:0]  l_1 [0:3];
    genvar gj;
    generate for (gj = 0; gj < 4; gj = gj + 1) begin : g_ld
        assign l_n[gj] = r_n - HW'(gj);
        assign l_1[gj] = r_b1 - HW'(gj + 1);
    end endgenerate

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction
    function automatic [10:0] sbkeys(input [HW+9:0] rem);
        sbkeys = (rem >= 1024) ? 11'd1024 : rem[10:0];
    endfunction
    // sbkeys(rem - 1024) without the subtraction
    function automatic [10:0] sbkeys_dec(input [HW+9:0] rem);
        sbkeys_dec = (rem[HW+9:10] != 1) ? 11'd1024 : {1'b0, rem[9:0]};
    endfunction
    // sectors a block needs: scale block ceil(m/8); code block b (1..16) 2 x keys
    // (code block b = t + 1 holds keys 64 t .. 64 t + 63, so both reduce to 5-bit compares of
    // the key count's / skip's 64-key index against t; equal to the arithmetic form for every
    // bidx and m / skip, checked exhaustively)
    function automatic [7:0] need(input [4:0] bidx, input [10:0] m);
        reg [4:0] t;
        begin
            t = bidx - 5'd1;
            if (bidx == 0) need = 8'((m + 11'd7) >> 3);
            else if (m[10:6] > t) need = 8'd128;
            else if (m[10:6] == t) need = {1'b0, m[5:0], 1'b0};
            else need = 8'd0;
        end
    endfunction
    function automatic [7:0] lower(input [4:0] bidx,input [9:0] skip);
        reg [4:0] t;
        begin
            t = bidx - 5'd1;
            if(bidx==0) lower={1'b0,skip[9:3]};
            else if ({1'b0, skip[9:6]} > t) lower = 8'd128;
            else if ({1'b0, skip[9:6]} == t && skip[5:0] != 0) lower = {1'b0, skip[5:0], 1'b0};
            else lower = 8'd0;
        end
    endfunction

    // -- per bank, per entry ---------------------------------------------------------
    reg [2:0]    left [0:NPC*WB-1];
    reg [WB-1:0] cc   [0:NPC-1];

    // -- generators: g_* is the next block to prepare; nx_* the prepared request -------
    reg [BW-1:0]   g_hi   [0:NPC-1];          // block (relative), low BW bits
    reg [BW-1:0]   g_hi1  [0:NPC-1];          // g_hi + 1
    reg [4:0]      g_bidx [0:NPC-1];
    reg [HW+9:0]   g_rem  [0:NPC-1];
    reg [10:0]     g_m    [0:NPC-1];          // sbkeys(g_rem)
    reg [HW-1:0]   g_abs  [0:NPC-1];
    reg [4:0]      g_col  [0:NPC-1];          // p ^ fold(g_abs)
    reg [7:0]      g_need [0:NPC-1];          // need(g_bidx, g_m)
    reg [7:0]      g_low  [0:NPC-1];          // first-super-block lower bound (0 elsewhere)
    reg [HW-1:0]   g_left [0:NPC-1];          // nblk - g_hi
    reg [HW-1:0]   g_l1   [0:NPC-1];          // nblk1 - 1 - g_hi
    reg [NPC-1:0]  g_more, g_wrapn, g_first, g_lo16;
    reg [HW-1:0]   eg     [0:NPC-1];          // g_hi - d_hi
    reg [HW-1:0]   dl     [0:NPC-1];          // nx_hi - d_hi
    reg [NPC-1:0]  ga_ok;                     // dl < GA
    reg [NPC-1:0]  nx_v;
    reg [BW-1:0]   nx_hi  [0:NPC-1];
    reg [2:0]      nx_len [0:NPC-1];
    reg [1:0]      nx_off [0:NPC-1];
    reg [AW-1:0]   nx_addr[0:NPC-1];

    // -- drain state ------------------------------------------------------------------
    reg [BW-1:0]   d_hi;                      // head block (relative), low BW bits
    reg [UW-1:0]   d_hu1;                     // d_hi[BW-1:SW] + 1
    reg [HW-1:0]   d_abs;                     // base + d_hi
    reg [4:0]      d_fold;                    // fold(d_abs)
    reg [4:0]      d_bidx;                    // block within its super-block (0 = scales)
    reg [HW+9:0]   d_rem;                     // keys from the head super-block's start
    reg [10:0]     d_m;                       // sbkeys(d_rem)
    reg [1:0]      d_q;
    reg [6:0]      d_kb;                      // keys of the head code block (0..64)
    reg [HW-1:0]   d_left, d_l1;              // nblk - d_hi, nblk1 - 1 - d_hi
    reg            d_more, d_wrapn;
    reg            adv;                       // the head moved at the last edge
    reg [3:0]      qa, qb;                    // per quarter q: its 8 banks (group q ^ fold[4:3]) complete
                                              // at cc[*][d_slot] (qa) / cc[*][d_slot + 1] (qb, permuted
                                              // with the next head's fold) as of last cycle; after a step
                                              // the head is last cycle's d_slot + 1: qb
    reg            all_a, all_b;              // all 32 banks complete, same two entries
    reg [3:0]      qz;                        // qz[q]: quarter q of the head block has no keys (d_kb <= 16 q)
    reg [3:0]      grp_a, grp_b;              // combinational: per 8-bank group, the two entries complete
    wire [SW-1:0]  d_slot = d_hi[SW-1:0];
    reg  [WB-1:0]  d_oh;                      // one-hot d_slot
    wire [WB-1:0]  d_oh1 = {d_oh[WB-2:0], d_oh[WB-1]};   // one-hot d_slot + 1
    wire [1:0]     d_qg = d_q ^ d_fold[4:3];  // the 8-bank group of quarter d_q
    integer b, c;
    wire           all_in = adv ? all_b : all_a;
    wire [3:0]     qsel = adv ? qb : qa;
    wire           q_in = qsel[d_q];
    wire [6:0]     d_qk = (d_kb > {d_q, 4'd0}) ? d_kb - {d_q, 4'd0} : 7'd0;   // keys left from this quarter
    wire           d_live = run && d_more;
    wire           do_scale = d_live && (d_bidx == 0) && all_in;
    wire           do_q = d_live && (d_bidx != 0) && q_in && (qz[d_q] || dr_ready);
    wire           d_step = do_scale || (do_q && d_q == 3);
    // keys of the code block after the head (the head's next d_bidx); a scale block
    // (n_bidx 0) has none, so the head's own d_m serves
    wire [4:0]     n_bidx = (d_bidx == 16) ? 5'd0 : d_bidx + 5'd1;
    wire [11:0]    n_off = {n_bidx - 5'd1, 6'd0};
    wire [6:0]     n_kb = (n_bidx == 0 || d_m <= n_off) ? 7'd0 : ((d_m - n_off >= 64) ? 7'd64 : d_m - n_off);
    reg  [HW-1:0]  d_abs1;                    // d_abs + 1
    reg  [HW-1:0]  b2p1;                      // base2 + 1
    reg  [4:0]     fb2;                       // fold(base2)
    reg  [HW+9:0]  r_span;                    // cmd_span, for the ph 1 load of g_rem / d_rem
    reg  [WB-1:0]  th;                        // th[i]: i < d_slot (the return gate's entry-bit compare)
    reg  [2:0]     lval [0:NPC-1];            // left[p][rr_s[p]] as of this cycle (read a cycle early)
    wire [BW-1:0]  d_hi1 = d_hi + 1'b1;
    wire [4:0]     d_fold_n = d_wrapn ? fb2 : fold(d_abs1);   // the head's fold after a step
    function automatic [3:0] qzof(input [6:0] kb);
        qzof = {kb <= 7'd48, kb <= 7'd32, kb <= 7'd16, kb == 7'd0};
    endfunction
    integer gb, gc2;
    always @* begin
        for (gb = 0; gb < 4; gb = gb + 1) begin
            grp_a[gb] = 1'b1;
            grp_b[gb] = 1'b1;
            for (gc2 = 0; gc2 < 8; gc2 = gc2 + 1) begin
                if ((cc[8 * gb + gc2] & d_oh) == 0) grp_a[gb] = 1'b0;
                if ((cc[8 * gb + gc2] & d_oh1) == 0) grp_b[gb] = 1'b0;
            end
        end
    end

    // a beat is taken only when its block has a ROB entry (within WB of the head):
    // (tag - d_hi) mod 2^BW < WB; otherwise its channel's return queue holds it and
    // that channel alone stops
    genvar gq;
    generate
        for (gq = 0; gq < NPC; gq = gq + 1) begin : g_rr
            wire [BW-1:0] t = rsp_tag[gq*TAGW +: BW];
            wire [WB-1:0] tdec = WB'(1) << t[SW-1:0];
            wire          bor = |(tdec & th);
            if (UW > 0) begin : g_u
                assign rsp_rdy[gq] = bor ? (t[BW-1:SW] == d_hu1) : (t[BW-1:SW] == d_hi[BW-1:SW]);
            end else begin : g_n
                assign rsp_rdy[gq] = 1'b1;
            end
        end
    endgenerate
    // registered responses
    reg [NPC-1:0]  rr_v;
    reg [SW-1:0]   rr_s [0:NPC-1];

    integer p, s;
    reg [4:0]    gc, nb;
    reg [7:0]    gn,glo;
    reg [8:0]    ge,lo_sec,hi_sec,col_sec;
    reg [2:0]    gl;
    reg [10:0]   nm;
    reg [HW-1:0] na;
    reg          iss, prep, nf;
    // issue and prepare decisions of every generator this cycle
    reg [NPC-1:0] iss_w, prep_w;
    integer pw;
    always @* for (pw = 0; pw < NPC; pw = pw + 1) begin
        iss_w[pw] = nx_v[pw] && (!req_v[pw] || req_rdy[pw]) && ga_ok[pw];
        prep_w[pw] = (!nx_v[pw] || iss_w[pw]) && g_more[pw];
    end
    // left[p][tag entry] read a cycle ahead of its count, with this edge's writes forwarded:
    // the issue (wins, as in the main block) and the counted response
    wire           run_upd = run;              // run implies busy, so no command is accepted then
    integer pl;
    always @(posedge clk)
        for (pl = 0; pl < NPC; pl = pl + 1) begin
            if (run_upd && iss_w[pl] && nx_hi[pl][SW-1:0] == rsp_tag[pl*TAGW +: SW]) lval[pl] <= nx_len[pl];
            else if (rr_v[pl] && rr_s[pl] == rsp_tag[pl*TAGW +: SW]) lval[pl] <= lval[pl] - 3'd1;
            else lval[pl] <= left[pl * WB + rsp_tag[pl*TAGW +: SW]];
        end
    // the generators' flags and counters (written only here)
    integer pf;
    always @(posedge clk) begin
        if (rst_n) begin
            // idle: the command-derived state tracks the command inputs every cycle, so the
            // edge that accepts a command loads it without cmd_v in its select (run implies
            // busy: the run branch never overlaps an accepted command)
            if (!busy) begin
                for (pf = 0; pf < NPC; pf = pf + 1) begin
                    g_more[pf] <= c_more; g_wrapn[pf] <= 1'b0;
                    g_first[pf] <= c_nz1; g_lo16[pf] <= 1'b1;
                    eg[pf] <= 0; dl[pf] <= 0; ga_ok[pf] <= 1'b1;
                end
            end else if (run) begin
                for (pf = 0; pf < NPC; pf = pf + 1) begin
                    // lookahead: dl' = nx_hi' - d_hi', eg' = g_hi' - d_hi'
                    // (the late selects pick among values precomputed from registers)
                    if (prep_w[pf]) begin
                        dl[pf] <= d_step ? eg[pf] - 1'b1 : eg[pf];
                        ga_ok[pf] <= d_step ? (eg[pf] != 0 && eg[pf] <= GA) : (eg[pf] < GA);
                    end else if (d_step) begin
                        dl[pf] <= dl[pf] - 1'b1;
                        ga_ok[pf] <= (dl[pf] != 0 && dl[pf] <= GA);
                    end
                    if (prep_w[pf] && !d_step) eg[pf] <= eg[pf] + 1'b1;
                    else if (!prep_w[pf] && d_step) eg[pf] <= eg[pf] - 1'b1;
                    if (prep_w[pf]) begin
                        if (ph != 0) begin
                            // block g_hi < 3: more = g_hi + 1 < nblk, wrap next = g_hi + 2 == nblk1
                            g_more[pf] <= !t_n[g_hi[pf][1:0] + 2'd1];
                            g_wrapn[pf] <= t_1[3'(g_hi[pf][1:0]) + 3'd2];
                        end else begin
                            g_more[pf] <= (g_left[pf] != 1);
                            g_wrapn[pf] <= (g_l1[pf] == 1);
                        end
                        g_left[pf] <= g_left[pf] - 1'b1;
                        g_l1[pf] <= g_l1[pf] - 1'b1;
                        g_first[pf] <= g_first[pf] && g_lo16[pf] && !g_wrapn[pf];
                        g_lo16[pf] <= g_lo16[pf] && (g_hi[pf][3:0] != 4'd15);
                    end
                    if (ph == 3) begin
                        g_left[pf] <= prep_w[pf] ? l_n[g_hi[pf][1:0] + 2'd1] : l_n[g_hi[pf][1:0]];
                        g_l1[pf] <= prep_w[pf] ? l_1[g_hi[pf][1:0] + 2'd1] : l_1[g_hi[pf][1:0]];
                    end
                end
            end
        end
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; ph <= 2'd0; req_v <= 0; nx_v <= 0; rr_v <= 0; adv <= 1'b0;
            dr_scale <= 1'b0; dr_quarter <= 1'b0;
            for (p = 0; p < NPC; p = p + 1) begin cc[p] <= 0; g_hi[p] <= 0; end
        end else begin
            dr_scale <= 1'b0;
            dr_quarter <= 1'b0;
            // quarter completion for the next cycle (one-hot entry select, AND-OR; quarter order)
            for (b = 0; b < 4; b = b + 1) begin
                qa[b] <= grp_a[b[1:0] ^ d_fold[4:3]];
                qb[b] <= grp_b[b[1:0] ^ d_fold_n[4:3]];
            end
            all_a <= &grp_a;
            all_b <= &grp_b;
            adv <= 1'b0;
            // responses: registered, then counted
            for (p = 0; p < NPC; p = p + 1) begin
                rr_v[p] <= rsp_v[p] && rsp_rdy[p];
                rr_s[p] <= rsp_tag[p*TAGW +: SW];
                if (rr_v[p]) begin
                    left[p * WB + rr_s[p]] <= lval[p] - 3'd1;
                    if (lval[p] == 3'd1) cc[p][rr_s[p]] <= 1'b1;
                end
            end
            if (!busy) begin
                if (cmd_v) begin
                    // (d_hi, th, d_hu1 set the return gate, an output: they move only on a command)
                    run <= 1'b1; busy <= 1'b1; ph <= 2'd1;
                    d_hi <= 0; d_oh <= WB'(1); th <= '0; d_hu1 <= 1;
                end
                first_skip<=cmd_skip;
                base2 <= cmd_base2; span2 <= cmd_nkeys2; m2 <= sbkeys(cmd_nkeys2);
                d_abs <= cmd_base; d_abs1 <= cmd_base + 1'b1; d_fold <= fold(cmd_base); d_bidx <= 0;
                r_span <= cmd_span; b2p1 <= cmd_base2 + 1'b1; fb2 <= fold(cmd_base2);
                d_m <= c_m; d_q <= 0; d_kb <= 0; qz <= 4'b1111;
                d_more <= c_more; d_wrapn <= 1'b0;
                t_n[1] <= c_hz1 && c_hz2 && c_bss == 1;
                t_n[2] <= c_hz1 && c_hz2 && c_bss == 2;
                t_n[3] <= c_hz1 && c_hz2 && c_bss == 3;
                t_1[2] <= c_hz1 && c_bs1 == 2;
                t_1[3] <= c_hz1 && c_bs1 == 3;
                t_1[4] <= c_hz1 && c_bs1 == 4;
                r_hi1 <= cmd_span[HW+9:10]; r_sm1 <= bsmall(cmd_span[9:0]);
                r_hi2 <= cmd_nkeys2[HW+9:10]; r_sm2 <= bsmall(cmd_nkeys2[9:0]);
                nx_v <= 0;
                for (p = 0; p < NPC; p = p + 1) begin
                    g_hi[p] <= 0; g_hi1[p] <= 1; g_abs[p] <= cmd_base; g_bidx[p] <= 0;
                    g_m[p] <= c_m; g_col[p] <= p[4:0] ^ fold(cmd_base);
                    g_need[p] <= need(5'd0, c_m);
                    g_low[p] <= c_nz1 ? lower(5'd0, cmd_skip) : 8'd0;
                end
            end else if (run) begin
                if (ph != 0) ph <= (ph == 3) ? 2'd0 : ph + 2'd1;
                if (ph == 1) begin
                    // no prep / step in the first run cycle moves g_rem / d_rem (block 0 is a scale block)
                    d_rem <= r_span;
                    for (p = 0; p < NPC; p = p + 1) g_rem[p] <= r_span;
                end
                if (ph == 1) begin r_b1 <= HW'(17) * r_hi1 + HW'(r_sm1); r_b2 <= HW'(17) * r_hi2 + HW'(r_sm2); end
                if (ph == 2) r_n <= r_b1 + r_b2;
                if (ph == 3) begin
                    d_left <= d_step ? l_n[d_hi[1:0] + 2'd1] : l_n[d_hi[1:0]];
                    d_l1 <= d_step ? l_1[d_hi[1:0] + 2'd1] : l_1[d_hi[1:0]];
                end
                for (p = 0; p < NPC; p = p + 1) begin
                    if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                    // issue the prepared request
                    iss = iss_w[p];
                    if (iss) begin
                        s = nx_hi[p] % WB;
                        left[p * WB + s] <= nx_len[p];
                        cc[p][s] <= (nx_len[p] == 3'd0);
                        if (nx_len[p] != 0) begin
                            req_v[p] <= 1'b1;
                            req_addr[p*AW +: AW] <= nx_addr[p];
                            req_len[p*LENW +: LENW] <= nx_len[p];
                            req_tag[p*TAGW +: TAGW] <= {nx_off[p],2'b00,nx_hi[p]};
                        end
                    end
                    // prepare the next one
                    prep = prep_w[p];
                    if (prep) begin
                        gc = g_col[p];
                        gn = g_need[p];
                        glo = g_low[p];
                        col_sec={2'b00,gc,2'b00};
                        lo_sec=({1'b0,glo}>col_sec) ? {1'b0,glo} : col_sec;
                        hi_sec=({1'b0,gn}<col_sec+4) ? {1'b0,gn} : col_sec+4;
                        ge=(hi_sec>lo_sec) ? hi_sec-lo_sec : 9'd0;
                        gl=ge[2:0];
                        nx_hi[p] <= g_hi[p];
                        nx_len[p] <= gl;
                        nx_off[p]<=2'(lo_sec-col_sec);
                        // lo_sec - col_sec < 4 whenever the length is nonzero, the only case
                        // the address leaves the unit
                        nx_addr[p] <= {g_abs[p], gc, 2'(lo_sec-col_sec)};
                        g_hi[p] <= g_hi1[p]; g_hi1[p] <= g_hi1[p] + 1'b1;
                        nf = g_first[p] && g_lo16[p] && !g_wrapn[p];
                        if (g_wrapn[p]) begin
                            // wrap: continue at the ring's first super-block
                            na = base2; nb = 5'd0; nm = m2;
                            g_rem[p] <= span2;
                        end else begin
                            na = g_abs[p] + 1'b1;
                            if (g_bidx[p] == 16) begin
                                nb = 5'd0; nm = sbkeys_dec(g_rem[p]);
                                g_rem[p] <= g_rem[p] - 1024;
                            end else begin
                                nb = g_bidx[p] + 5'd1; nm = g_m[p];
                            end
                        end
                        g_abs[p] <= na; g_bidx[p] <= nb; g_m[p] <= nm;
                        g_col[p] <= p[4:0] ^ fold(na);
                        g_need[p] <= need(nb, nm);
                        g_low[p] <= nf ? lower(nb, first_skip) : 8'd0;
                    end
                    nx_v[p] <= prep || (nx_v[p] && !iss);
                end
                // drain
                if (do_scale) begin
                    dr_scale <= 1'b1;
                    dr_slot <= d_slot;
                    dr_fold <= d_fold;
                    for (p = 0; p < NPC; p = p + 1) cc[p][d_slot] <= 1'b0;
                end else if (do_q) begin
                    if (d_qk != 0) begin
                        dr_quarter <= 1'b1;
                        dr_slot <= d_slot;
                        dr_q <= d_q;
                        dr_fold <= d_fold;
                        dr_sidx <= {d_bidx[3:0] - 4'd1, d_q};
                        dr_nkeys <= (d_qk >= 16) ? 5'd16 : d_qk[4:0];
                    end
                    for (p = 0; p < NPC; p = p + 1) if (p[4:3] == d_qg) cc[p][d_slot] <= 1'b0;
                    d_q <= d_q + 1;
                end
                if (d_step) begin
                    adv <= 1'b1;
                    d_hi <= d_hi1; d_oh <= d_oh1; th <= d_oh[WB-1] ? '0 : (th | d_oh);
                    d_hu1 <= d_hi1[BW-1:SW] + 1'b1;
                    if (ph != 0) begin
                        d_more <= !t_n[d_hi[1:0] + 2'd1];
                        d_wrapn <= t_1[3'(d_hi[1:0]) + 3'd2];
                    end else begin
                        d_more <= (d_left != 1);
                        d_wrapn <= (d_l1 == 1);
                        d_left <= d_left - 1'b1;
                        d_l1 <= d_l1 - 1'b1;
                    end
                    if (d_wrapn) begin
                        d_abs <= base2; d_abs1 <= b2p1; d_fold <= fb2; d_bidx <= 0; d_rem <= span2; d_m <= m2; d_kb <= 0; qz <= 4'b1111;
                    end else begin
                        d_abs <= d_abs1; d_abs1 <= d_abs1 + 1'b1;
                        d_fold <= fold(d_abs1);
                        d_bidx <= n_bidx;
                        d_kb <= n_kb; qz <= qzof(n_kb);
                        if (d_bidx == 16) begin
                            d_rem <= d_rem - 1024;
                            d_m <= sbkeys_dec(d_rem);
                        end
                    end
                end
                if (!d_live) run <= 1'b0;
            end else if (busy && !dr_quarter) busy <= 1'b0;
        end
    end
endmodule

// One stack's key stream: control + datapath.
module ot_hdc_v41x_idx_kstream_ring #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer GA   = 120,
    parameter integer AW   = 24,
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    // opt-in (W11 hardening): ROBM = 1 the ROB in SRAM macros with synchronous read
    // (ot_hdc_v41x_idx_kdata_m, ROB_XP pipeline stages); 0 the behavioural ot_hdc_v41x_idx_kdata
    parameter integer ROBM = 0,
    parameter integer ROB_MACRO = 1,
    parameter integer ROB_XP = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 cmd_v,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,
    input  wire [HW+9:0]        cmd_nkeys,
    input  wire [HW-1:0]        cmd_base2,
    input  wire [HW+9:0]        cmd_nkeys2,
    output wire                 busy,
    output wire [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output wire [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output wire [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    output wire                 o_valid,
    input  wire                 o_ready,
    output wire [15:0]          o_kv,
    output wire [16*544-1:0]    o_key,
    // activation counters (since reset): keys delivered, HBM beats taken
    output reg  [47:0]          cnt_keys_streamed,
    output reg  [47:0]          cnt_hbm_beats
);
    wire dr_scale, dr_quarter, dr_ready;
    wire [$clog2(WB)-1:0] dr_slot;
    wire [1:0] dr_q;
    wire [4:0] dr_fold, dr_nkeys;
    wire [5:0] dr_sidx;
    wire       kbusy, dbusy;
    assign busy = kbusy || o_valid || dbusy;
    integer ck;
    reg [4:0] nko;
    reg [5:0] nbt;
    always @* begin
        nko = 0; nbt = 0;
        for (ck = 0; ck < 16; ck = ck + 1) nko = nko + o_kv[ck];
        for (ck = 0; ck < NPC; ck = ck + 1) nbt = nbt + (rsp_v[ck] & rsp_rdy[ck]);
    end
    always @(posedge clk)
        if (!rst_n) begin
            cnt_keys_streamed <= 0; cnt_hbm_beats <= 0;
        end else begin
            if (o_valid && o_ready) cnt_keys_streamed <= cnt_keys_streamed + nko;
            cnt_hbm_beats <= cnt_hbm_beats + nbt;
        end
    ot_hdc_v41x_idx_kctl_ring #(.NPC(NPC), .WB(WB), .GA(GA), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW)) u_c (
        .clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_nkeys(cmd_nkeys),
        .cmd_base2(cmd_base2), .cmd_nkeys2(cmd_nkeys2), .busy(kbusy),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot),
        .dr_q(dr_q), .dr_fold(dr_fold), .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready));
    wire [NPC*BEATW-1:0] rsp_beat_adj;
    genvar pp;
    generate for(pp=0;pp<NPC;pp=pp+1) begin:g_adj
        assign rsp_beat_adj[pp*BEATW +: BEATW]=rsp_beat[pp*BEATW +: BEATW]+BEATW'(rsp_tag[pp*TAGW+TAGW-1 -: 2]);
    end endgenerate
    generate if (ROBM != 0) begin : g_robm
    ot_hdc_v41x_idx_kdata_m #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW), .MACRO(ROB_MACRO),
                              .XP(ROB_XP)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat_adj),
        .rsp_data(rsp_data),
        .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot), .dr_q(dr_q), .dr_fold(dr_fold),
        .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready),
        .o_kv(o_kv), .o_key(o_key), .busy(dbusy));
    end else begin : g_rob
    ot_hdc_v41x_idx_kdata #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat_adj),
        .rsp_data(rsp_data),
        .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot), .dr_q(dr_q), .dr_fold(dr_fold),
        .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready),
        .o_kv(o_kv), .o_key(o_key));
    assign dbusy = 1'b0;
    end endgenerate
endmodule
