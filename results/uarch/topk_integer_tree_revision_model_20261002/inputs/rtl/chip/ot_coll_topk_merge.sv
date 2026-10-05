`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_coll_topk_merge: the select half of COLL_TOPK_MERGE / ARGMAX_MERGE (W15b).
//
// Every die holds the same gathered candidates (the all-gather of each rank's
// n (score, local id) pairs, rank-major), so every die runs this identical,
// deterministic select and needs no second exchange.
//
//   global id  = rank * stride + local id
//   result     = the k global ids of the largest scores, ties to the LOWER
//                global id (tools/hdc_golden_v41.topk_lowest_index: scores
//                compared as values, so -0 == +0), emitted in ascending
//                global-id order, 16 ids a 512-bit word (the last word padded
//                with zeros).
//   order      = candidates are stored rank-major and each rank's local ids
//                ascending (the contract), so buffer order IS global-id order.
//
// Method: exact radix select, then one filter pass.
//   keys       binary32 -> an order-preserving u32 (-0 canonicalised to +0;
//              a NaN score latches fault).
//   HIST pass  d = 0..32/DIG-1: P candidates a cycle; those whose top d*DIG
//              key bits equal the prefix found so far are counted into
//              2^DIG bins by their next DIG bits.  The bin holding the r-th
//              largest extends the prefix and r becomes the rank inside it.
//              After the last pass the prefix is T, the k-th largest key, and
//              r is how many keys equal to T are taken.
//   FILTER     P candidates a cycle in buffer order: take key > T, or
//              key == T while fewer than r equal keys were taken (ties to the
//              lower id, since buffer order is id order).  Taken ids are
//              compacted (prefix counts, one-hot slot select) into a staging
//              buffer that emits OW = PF/LW full words at a time (aligned).
// Cycles (no stalls): (32/DIG) x (N*n/P + 7) + N*n/PF + 9.
// The candidate buffers are register files here (a synthesis stand-in for
// the die's SRAM); all timing-critical logic is pipelined for 1.2 GHz at SS.
// ---------------------------------------------------------------------------
module ot_coll_topk_merge #(
    parameter integer N     = 4,              // ranks
    parameter integer NMAX  = 512,            // candidates per rank (max); n % P == 0
    parameter integer LW    = 16,             // lanes (u32 elements) in one VM word
    parameter integer LDW   = 1,              // words a load beat: 1 (rank ld_rank) or N (word j is rank j)
    parameter integer P     = 64,             // HIST candidates a cycle (multiple of LW)
    parameter integer PF    = P,              // FILTER candidates a cycle (divides P, multiple of LW): the filter's
                                              // compactor is PF x PF, so a wide P keeps a narrow PF
    parameter integer DIG   = 4,              // radix bits per HIST pass (divides 32)
    parameter integer RB    = (N > 1) ? $clog2(N) : 1,
    parameter integer CAP   = N * NMAX,
    parameter integer CB    = $clog2(CAP + 1),
    parameter integer WB    = $clog2(CAP / LW),
    parameter integer OW    = PF / LW         // output words a cycle (max)
) (
    input  wire              clk,
    input  wire              rst_n,
    // gathered candidates: one 16-lane word of scores (ld_id 0) or local ids (ld_id 1) of rank ld_rank
    input  wire              ld_valid,
    input  wire              ld_id,
    input  wire [RB-1:0]     ld_rank,
    input  wire [WB-1:0]     ld_word,         // word index inside the rank (n / LW words); n stable while loading
    input  wire [32*LW*LDW-1:0] ld_data,
    // command
    input  wire              go,
    input  wire [CB-1:0]     n,               // candidates per rank
    input  wire [CB-1:0]     k,               // 1 <= k <= N * n
    input  wire [31:0]       stride,          // >= n (rank r owns [r*stride, (r+1)*stride))
    output reg               busy,
    output reg               done,            // one cycle, after the last output word
    output reg               fault,           // NaN score, or a bad command
    // result: out_nw words (LW ids each, word 0 in the low bits) a cycle, in order, in aligned groups of OW
    // words (only the last group may be short; the last word zero-padded)
    output reg               out_valid,
    output reg  [$clog2(OW+1)-1:0] out_nw,
    output reg  [32*LW*OW-1:0] out_data,
    output reg               out_last,
    output reg  [31:0]       stat_cycles      // go -> done
);
    localparam integer NR    = CAP / P;        // P-lane rows
    localparam integer QW    = P / LW;         // words per row
    localparam integer NPASS = 32 / DIG;
    localparam integer NBIN  = 1 << DIG;
    localparam integer RRB   = (NR > 1) ? $clog2(NR) : 1;
    localparam integer PB    = $clog2(P + 1);
    localparam integer SB    = $clog2(2 * PF + 1);
    localparam integer FB    = $clog2(PF + 1);
    localparam integer FQ    = P / PF;         // filter chunks per row

    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;       // -0 == +0 (values compared)
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic isnan(input [31:0] x);
        isnan = (x[30:23] == 8'hFF) && (x[22:0] != 0);
    endfunction

    // ---- candidate buffers (P-lane rows) ------------------------------------------------------------------
    reg [32*P-1:0] kmem [0:NR-1];
    reg [32*P-1:0] imem [0:NR-1];
    reg            nan_seen;
    reg [WB:0]     wpr;                             // words per rank (n / LW)
    integer ln, lj;
    always @(posedge clk) if (ld_valid)
        for (lj = 0; lj < LDW; lj = lj + 1) begin : wr
            reg [WB+RB:0] fw;
            fw = (LDW == 1 ? ld_rank : lj[RB-1:0]) * wpr + ld_word;
            if (ld_id) imem[fw / QW][32*LW*(fw % QW) +: 32*LW] <= ld_data[32*LW*lj +: 32*LW];
            else for (ln = 0; ln < LW; ln = ln + 1)
                kmem[fw / QW][32*(LW*(fw % QW) + ln) +: 32] <= okey(ld_data[32*(LW*lj + ln) +: 32]);
        end

    // ---- control ------------------------------------------------------------------------------------------
    localparam [2:0] S_IDLE = 3'd0, S_HIST = 3'd1, S_PICK = 3'd2, S_FILT = 3'd3, S_DRAIN = 3'd4;
    reg  [2:0]      st;
    reg  [CB-1:0]   k_r, n_r;
    reg  [31:0]     stride_r;
    reg  [31:0]     prefix;
    reg  [$clog2(NPASS+1)-1:0] pass;
    reg  [CB-1:0]   rr;
    reg  [RRB:0]    row, nrow, rpr;                 // row issued, rows in use, rows per rank
    reg  [CB-1:0]   cnt [0:NBIN-1];
    wire [5:0]      sh = 6'd32 - 6'(pass) * 6'(DIG);
    integer b, l, j;

    // ---- HIST: read row -> match + one-hot -> per-bin popcount -> accumulate ------------------------------------
    reg              h0_v, h1_v, h2_v;
    reg [32*P-1:0]   h0_k;
    reg [P-1:0]      h1_hot [0:NBIN-1];
    reg [PB-1:0]     h2_pc [0:NBIN-1];
    always @(posedge clk) begin
        h0_k <= kmem[row[RRB-1:0]];
        for (l = 0; l < P; l = l + 1) begin : hot
            reg [31:0] kk;
            reg [63:0] top;
            reg        m;
            kk = h0_k[32*l +: 32];
            top = {32'd0, kk} >> sh;
            m = (top[31:0] == ({32'd0, prefix} >> sh));
            for (b = 0; b < NBIN; b = b + 1)
                h1_hot[b][l] <= m && (((kk >> (sh - DIG)) & (NBIN - 1)) == b);
        end
        for (b = 0; b < NBIN; b = b + 1) begin : pc
            reg [PB-1:0] s;
            s = 0;
            for (l = 0; l < P; l = l + 1) s = s + h1_hot[b][l];
            h2_pc[b] <= s;
        end
    end

    // ---- PICK -----------------------------------------------------------------------------------------------
    reg  [CB-1:0]   suf [0:NBIN-1];
    reg  [1:0]      pk;
    reg  [DIG-1:0]  pbin;
    reg  [CB-1:0]   pgt;

    // ---- FILTER: read -> compare -> take -> prefix -> compact -> stage/emit ------------------------------------
    reg              f0_v, f1_v, f2_v, f3_v, f4_v;
    reg  [32*PF-1:0]  f0_k, f0_i, f1_id, f2_id, f3_id;
    reg  [31:0]      f0_base, rbase;
    reg  [RRB+8:0]   frow, frr, nfch, fpr;          // chunk issued; chunk inside the rank; chunks in use; per rank
    reg  [PF-1:0]     f1_gt, f1_eq, f2_take, f3_take;
    reg  [FB-1:0]    f3_tp [0:PF-1];                 // take prefix counts
    reg  [FB-1:0]    f3_n;
    reg  [32*PF-1:0]  f4_c;                          // compacted ids
    reg  [FB-1:0]    f4_n;
    reg  [CB-1:0]    eq_left;
    reg  [64*PF-1:0]  stg;                           // 2PF staging slots
    reg  [SB-1:0]    stn;
    reg  [CB-1:0]    outw_left;
    wire [31:0]      T = prefix;
    wire             fpipe = f0_v || f1_v || f2_v || f3_v || f4_v;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
            out_nw <= 0; pass <= 0; row <= 0; pk <= 0; stn <= 0; stat_cycles <= 0; nan_seen <= 1'b0;
            wpr <= NMAX / LW; h0_v <= 1'b0; h1_v <= 1'b0; h2_v <= 1'b0;
            {f0_v, f1_v, f2_v, f3_v, f4_v} <= 5'b0;
            for (b = 0; b < NBIN; b = b + 1) cnt[b] <= 0;
        end else begin
            if (!busy) wpr <= (WB+1)'(n / LW);
            if (ld_valid && !ld_id)
                for (ln = 0; ln < LW * LDW; ln = ln + 1) if (isnan(ld_data[32*ln +: 32])) nan_seen <= 1'b1;
            done <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0; out_nw <= 0;
            if (busy) stat_cycles <= stat_cycles + 1;
            h0_v <= (st == S_HIST) && (row < nrow);
            h1_v <= h0_v;
            h2_v <= h1_v;
            case (st)
                S_IDLE: if (go) begin
                    if (nan_seen || k == 0 || n == 0 || ((n * N) % P) != 0 || (n % PF) != 0 || n > NMAX || k > n * N) fault <= 1'b1;
                    else begin
                        busy <= 1'b1; stat_cycles <= 0; st <= S_HIST;
                        k_r <= k; n_r <= n; stride_r <= stride; rr <= k;
                        prefix <= 0; pass <= 0; row <= 0;
                        nrow <= (n * N) / P; rpr <= n / P; nfch <= (n * N) / PF; fpr <= n / PF;
                        for (b = 0; b < NBIN; b = b + 1) cnt[b] <= 0;
                    end
                end
                S_HIST: begin
                    if (row < nrow) row <= row + 1'b1;
                    if (h2_v) for (b = 0; b < NBIN; b = b + 1) cnt[b] <= cnt[b] + h2_pc[b];
                    if (row == nrow && !h0_v && !h1_v && !h2_v) begin st <= S_PICK; pk <= 0; end
                end
                S_PICK: begin
                    pk <= pk + 1'b1;
                    if (pk == 0) begin : sufs
                        reg [CB-1:0] a;
                        a = 0;
                        for (b = NBIN - 1; b >= 0; b = b - 1) begin suf[b] <= a; a = a + cnt[b]; end
                    end
                    if (pk == 1) begin : choose
                        reg found;
                        found = 1'b0;
                        for (b = NBIN - 1; b >= 0; b = b - 1)
                            if (!found && suf[b] < rr && rr <= suf[b] + cnt[b]) begin
                                found = 1'b1; pbin <= b[DIG-1:0]; pgt <= suf[b];
                            end
                    end
                    if (pk == 2) begin
                        prefix <= prefix | ({{(32-DIG){1'b0}}, pbin} << (sh - DIG));
                        rr <= rr - pgt;
                        for (b = 0; b < NBIN; b = b + 1) cnt[b] <= 0;
                        row <= 0;
                        if (pass == NPASS - 1) begin
                            st <= S_FILT; frow <= 0; frr <= 0; rbase <= 0; stn <= 0;
                            eq_left <= rr - pgt; outw_left <= (k_r + LW - 1) / LW;
                        end else begin
                            pass <= pass + 1'b1; st <= S_HIST;
                        end
                    end
                end
                S_FILT, S_DRAIN: begin
                    // f0: read a row of keys and ids
                    f0_v <= (st == S_FILT) && (frow < nfch);
                    if ((st == S_FILT) && (frow < nfch)) begin
                        f0_k <= kmem[frow / FQ][32*PF*(frow % FQ) +: 32*PF];
                        f0_i <= imem[frow / FQ][32*PF*(frow % FQ) +: 32*PF];
                        f0_base <= rbase;
                        frow <= frow + 1'b1;
                        if (frr == fpr - 1) begin frr <= 0; rbase <= rbase + stride_r; end
                        else frr <= frr + 1'b1;
                    end
                    if (st == S_FILT && frow == nfch) st <= S_DRAIN;
                    // f1: compare with T, global ids
                    f1_v <= f0_v;
                    for (l = 0; l < PF; l = l + 1) begin
                        f1_gt[l] <= f0_k[32*l +: 32] > T;
                        f1_eq[l] <= f0_k[32*l +: 32] == T;
                        f1_id[32*l +: 32] <= f0_base + f0_i[32*l +: 32];
                    end
                    // f2: take (equal keys while eq_left lasts, lowest lanes first)
                    f2_v <= f1_v;
                    f2_id <= f1_id;
                    begin : take
                        reg [FB-1:0] e;
                        reg [PF-1:0] t;
                        e = 0;
                        for (l = 0; l < PF; l = l + 1) begin
                            t[l] = f1_gt[l] || (f1_eq[l] && (CB'(e) < eq_left));
                            e = e + f1_eq[l];
                        end
                        f2_take <= f1_v ? t : {PF{1'b0}};
                        if (f1_v) eq_left <= (CB'(e) < eq_left) ? eq_left - CB'(e) : {CB{1'b0}};
                    end
                    // f3: prefix counts of taken lanes
                    f3_v <= f2_v; f3_id <= f2_id; f3_take <= f2_take;
                    begin : pfx
                        reg [FB-1:0] a;
                        a = 0;
                        for (l = 0; l < PF; l = l + 1) begin f3_tp[l] <= a; a = a + f2_take[l]; end
                        f3_n <= a;
                    end
                    // f4: compact: slot j <- the taken lane whose prefix count is j
                    f4_v <= f3_v; f4_n <= f3_v ? f3_n : {FB{1'b0}};
                    for (j = 0; j < PF; j = j + 1) begin : cmp
                        reg [31:0] x;
                        x = 0;
                        for (l = j; l < PF; l = l + 1) if (f3_take[l] && f3_tp[l] == j) x = x | f3_id[32*l +: 32];
                        f4_c[32*j +: 32] <= x;
                    end
                    // f5: append at stn; emit OW full words once PF ids are staged (aligned groups), and at the end the
                    // rest, OW words a cycle, the last word zero-padded
                    begin : emit
                        reg [64*PF-1:0] s;
                        reg [SB-1:0] m;
                        reg [$clog2(OW+1)-1:0] w;
                        s = stg; m = stn;
                        if (f4_v && f4_n != 0) begin
                            s = s | ({{(32*PF){1'b0}}, f4_c & ((f4_n == PF) ? {(32*PF){1'b1}} :
                                     (({{(32*PF-1){1'b0}}, 1'b1} << (32 * f4_n)) - 1'b1))} << (32 * m));
                            m = m + f4_n;
                        end
                        w = 0;
                        if (m >= PF) w = OW;
                        else if (st == S_DRAIN && !fpipe && m != 0) w = ($clog2(OW+1))'((m + LW - 1) / LW);
                        if (w != 0) begin
                            out_valid <= 1'b1; out_nw <= w;
                            out_data <= s[32*LW*OW-1:0] & ((m >= SB'(32'(w) * LW)) ?
                                        ((w == OW) ? {(32*LW*OW){1'b1}} :
                                         (({{(32*LW*OW-1){1'b0}}, 1'b1} << (32 * LW * w)) - 1'b1)) :
                                        (({{(32*LW*OW-1){1'b0}}, 1'b1} << (32 * m)) - 1'b1));
                            out_last <= (outw_left == CB'(w));
                            outw_left <= outw_left - CB'(w);
                            s = s >> (32 * LW * w);
                            m = (m >= SB'(32'(w) * LW)) ? m - SB'(32'(w) * LW) : {SB{1'b0}};
                        end
                        stg <= s; stn <= m;
                    end
                    if (st == S_DRAIN && !fpipe && stn == 0 && !out_valid) begin
                        st <= S_IDLE; busy <= 1'b0; done <= 1'b1; nan_seen <= 1'b0;
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
