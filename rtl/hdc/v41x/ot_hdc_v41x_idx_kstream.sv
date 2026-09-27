`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Index-key stream from HBM, one HBM3E stack (NPC pseudo-channels).
//
// KEY LAYOUT (lossless, 68 B per key: 128 E2M1 codes + 4 UE8M0 scales).  A
// stack holds its keys in SUPER-BLOCKS of 1,024 keys = 17 blocks of 4 KB: block
// 0 carries the 1,024 keys' scales (4 B each, key order), blocks 1..16 the
// codes of 64 keys each (64 B = 2 sectors per key, key order).  17 x 4 KB =
// 1,024 x 68 B: no padding.  A partial last super-block is packed the same
// way; only its needed sectors are read.  Across the die's stacks keys are
// interleaved in 16-key groups (group g on stack g mod NS; ot_hdc_v41x_idx_kmerge).
//
// ADDRESS MAP (ot_hdc_v41x_idx_hbm / ot_hdc_hbm_model): sector s -> pseudo-
// channel ((s>>2) ^ (s>>7) ^ (s>>12)) mod 32, so block B's column c (sectors
// 4c..4c+3) lives on pseudo-channel p = c ^ fold(B), fold(B) = (B ^ B>>5) mod
// 32: every pseudo-channel carries exactly one 128-B column of every block.
//
// REQUESTS.  One generator per pseudo-channel walks the scan's blocks in
// order and asks its own channel for its column (1-4 sectors, trimmed to what
// the scan needs; a column needing none is marked done without a request).
// It runs ahead of the drain by at most GA blocks and only when its channel's
// queue has room: a channel stalled by a refresh backs up its own generator
// and no other (no head-of-line blocking across channels).  GA sets how far
// ahead the controller's queue sees, which is what refresh-aware REFpb needs:
// a bank no queued burst needs must stay unneeded for tRFCpb.  A beat whose
// block is more than WB ahead of the drain waits in its channel's return
// queue (rsp_rdy low), so the ROB is WB blocks, not GA.
//
// REORDER.  Beats return per channel in order; each is written to the ROB
// (bank = channel, entry = block mod WB, word = beat) and counted.  The drain
// walks blocks in order: a scale block moves to the scale buffer in one cycle
// once all its columns are in; a code block leaves in quarters (32 sectors =
// 16 keys; the quarter's 8 columns are 8 distinct banks) once the quarter's
// columns are in, each key joined with its 4 scale bytes.
//
// OUTPUT: valid/ready beats of 16 keys (o_kv marks the keys present: a scan's
// last beat may be partial), key j = {scales[31:0], codes[511:0]} (the
// engine's key format).  Command: cmd_v with base block, key count; `busy`
// until the last beat has left.
//
// The ROB (NPC banks x WB entries x 1,024 bits) and the 4-KB scale buffer are
// behavioural arrays here; on silicon they are SRAM macros (one 1W1R bank per
// channel).  ot_hdc_v41x_idx_kctl is the control (generators, entry state,
// drain), the unit routed on its own.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kctl #(
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
    input  wire [HW+9:0]        cmd_nkeys,
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
    // Pipelined for 1.034 GHz: every per-cycle decision reads registers only --
    //   * each generator prepares its next request one cycle ahead (address,
    //     length, block) and issues it the cycle its channel and the lookahead
    //     allow;
    //   * a response is registered, then counted (left: beats still to come per
    //     bank and ROB entry; cc: the entry's column is complete);
    //   * the drain reads the completion rows of the head entry and the next one
    //     from registers sampled a cycle earlier (a completion is seen one cycle
    //     late, never early: a bit is only cleared by the drain of its own entry).
    localparam integer SW = $clog2(WB);
    localparam integer BW = TAGW - 3;

    reg [HW-1:0]   base;
    reg [HW-1:0]   nblk;                      // blocks in the scan
    reg            run;

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction
    function automatic [10:0] sbkeys(input [HW+9:0] rem);
        sbkeys = (rem >= 1024) ? 11'd1024 : rem[10:0];
    endfunction
    // sectors a block needs: scale block ceil(m/8); code block b (1..16) 2 x keys
    function automatic [7:0] need(input [4:0] bidx, input [10:0] m);
        reg [11:0] kb;
        begin
            if (bidx == 0) need = (m + 11'd7) >> 3;
            else begin
                kb = (m > 64 * (bidx - 1)) ? (m - 64 * (bidx - 1)) : 12'd0;
                need = (kb >= 64) ? 8'd128 : {kb[6:0], 1'b0};
            end
        end
    endfunction

    // -- per bank, per entry ---------------------------------------------------------
    reg [2:0]    left [0:NPC*WB-1];
    reg [WB-1:0] cc   [0:NPC-1];

    // -- generators: g_* is the next block to prepare; nx_* the prepared request -------
    reg [HW-1:0]   g_hi   [0:NPC-1];
    reg [4:0]      g_bidx [0:NPC-1];
    reg [HW+9:0]   g_rem  [0:NPC-1];
    reg [HW-1:0]   g_abs  [0:NPC-1];
    reg [NPC-1:0]  nx_v;
    reg [HW-1:0]   nx_hi  [0:NPC-1];
    reg [2:0]      nx_len [0:NPC-1];
    reg [AW-1:0]   nx_addr[0:NPC-1];

    // -- drain state ------------------------------------------------------------------
    reg [HW-1:0]   d_hi;                      // head block (relative)
    reg [HW-1:0]   d_abs;                     // base + d_hi
    reg [4:0]      d_bidx;                    // block within its super-block (0 = scales)
    reg [HW+9:0]   d_rem;                     // keys from the head super-block's start
    reg [1:0]      d_q;
    reg [6:0]      d_kb;                      // keys of the head code block (0..64)
    reg            adv;                       // the head moved at the last edge
    reg [NPC-1:0]  row_a, row_b;              // cc[*][d_slot], cc[*][d_slot + 1] as of last cycle; after a
                                              // step the head is last cycle's d_slot + 1: row_b
    wire [SW-1:0]  d_slot = d_hi[SW-1:0];
    wire [4:0]     d_fold = fold(d_abs);
    wire [NPC-1:0] row = adv ? row_b : row_a;
    reg  [NPC-1:0] prow;                      // row permuted: bit c = bank c ^ fold
    integer b, c;
    always @* begin
        for (c = 0; c < NPC; c = c + 1) prow[c] = row[c[4:0] ^ d_fold];
    end
    wire           all_in = &row;
    wire           q_in = &prow[8 * d_q +: 8];
    wire [6:0]     d_qk = (d_kb > {d_q, 4'd0}) ? d_kb - {d_q, 4'd0} : 7'd0;   // keys left from this quarter
    wire           d_live = run && (d_hi < nblk);
    wire           do_scale = d_live && (d_bidx == 0) && all_in;
    wire           do_q = d_live && (d_bidx != 0) && q_in && (d_qk == 0 || dr_ready);
    wire           d_step = do_scale || (do_q && d_q == 3);
    // keys of the code block after the head (the head's next d_bidx / d_rem)
    wire [4:0]     n_bidx = (d_bidx == 16) ? 5'd0 : d_bidx + 5'd1;
    wire [HW+9:0]  n_rem = (d_bidx == 16) ? d_rem - 1024 : d_rem;
    wire [10:0]    n_m = sbkeys(n_rem);
    wire [11:0]    n_off = {n_bidx - 5'd1, 6'd0};
    wire [6:0]     n_kb = (n_bidx == 0 || n_m <= n_off) ? 7'd0 : ((n_m - n_off >= 64) ? 7'd64 : n_m - n_off);

    // a beat is taken only when its block has a ROB entry (within WB of the head);
    // otherwise its channel's return queue holds it and that channel alone stops
    genvar gq;
    generate
        for (gq = 0; gq < NPC; gq = gq + 1) begin : g_rr
            wire [BW-1:0] ahead = rsp_tag[gq*TAGW +: BW] - d_hi[BW-1:0];
            assign rsp_rdy[gq] = (ahead < WB);
        end
    endgenerate
    // registered responses
    reg [NPC-1:0]  rr_v;
    reg [SW-1:0]   rr_s [0:NPC-1];

    integer p, s;
    reg [4:0]    gc;
    reg [7:0]    gn;
    reg [8:0]    ge;
    reg [2:0]    gl;
    reg          iss, prep;
    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; req_v <= 0; nx_v <= 0; rr_v <= 0; adv <= 1'b0;
            dr_scale <= 1'b0; dr_quarter <= 1'b0;
            for (p = 0; p < NPC; p = p + 1) begin cc[p] <= 0; g_hi[p] <= 0; end
        end else begin
            dr_scale <= 1'b0;
            dr_quarter <= 1'b0;
            // completion rows for the next cycle
            for (b = 0; b < NPC; b = b + 1) begin
                row_a[b] <= cc[b][d_slot];
                row_b[b] <= cc[b][d_slot + 1'b1];
            end
            adv <= 1'b0;
            // responses: registered, then counted
            for (p = 0; p < NPC; p = p + 1) begin
                rr_v[p] <= rsp_v[p] && rsp_rdy[p];
                rr_s[p] <= rsp_tag[p*TAGW +: SW];
                if (rr_v[p]) begin
                    left[p * WB + rr_s[p]] <= left[p * WB + rr_s[p]] - 3'd1;
                    if (left[p * WB + rr_s[p]] == 3'd1) cc[p][rr_s[p]] <= 1'b1;
                end
            end
            if (cmd_v && !busy) begin
                base <= cmd_base;
                // 17 blocks per full super-block; a partial one: 1 + ceil(m / 64)
                nblk <= 17 * (cmd_nkeys >> 10) +
                        ((cmd_nkeys[9:0] != 0) ? (1 + ((cmd_nkeys[9:0] + 10'd63) >> 6)) : 0);
                run <= 1'b1; busy <= 1'b1;
                d_hi <= 0; d_abs <= cmd_base; d_bidx <= 0; d_rem <= cmd_nkeys; d_q <= 0; d_kb <= 0;
                nx_v <= 0;
                for (p = 0; p < NPC; p = p + 1) begin
                    g_hi[p] <= 0; g_abs[p] <= cmd_base; g_bidx[p] <= 0; g_rem[p] <= cmd_nkeys;
                end
            end else if (run) begin
                for (p = 0; p < NPC; p = p + 1) begin
                    if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                    // issue the prepared request
                    iss = nx_v[p] && (!req_v[p] || req_rdy[p]) && ((nx_hi[p] - d_hi) < GA);
                    if (iss) begin
                        s = nx_hi[p] % WB;
                        left[p * WB + s] <= nx_len[p];
                        cc[p][s] <= (nx_len[p] == 3'd0);
                        if (nx_len[p] != 0) begin
                            req_v[p] <= 1'b1;
                            req_addr[p*AW +: AW] <= nx_addr[p];
                            req_len[p*LENW +: LENW] <= nx_len[p];
                            req_tag[p*TAGW +: TAGW] <= {nx_len[p], nx_hi[p][BW-1:0]};
                        end
                    end
                    // prepare the next one
                    prep = (!nx_v[p] || iss) && (g_hi[p] < nblk);
                    if (prep) begin
                        gc = p[4:0] ^ fold(g_abs[p]);
                        gn = need(g_bidx[p], sbkeys(g_rem[p]));
                        ge = ({1'b0, gn} > {2'b0, gc, 2'b00}) ? ({1'b0, gn} - {2'b0, gc, 2'b00}) : 9'd0;
                        gl = (ge >= 4) ? 3'd4 : ge[2:0];
                        nx_hi[p] <= g_hi[p];
                        nx_len[p] <= gl;
                        nx_addr[p] <= {g_abs[p], gc, 2'b00};
                        g_hi[p] <= g_hi[p] + 1;
                        g_abs[p] <= g_abs[p] + 1;
                        if (g_bidx[p] == 16) begin
                            g_bidx[p] <= 0;
                            g_rem[p] <= g_rem[p] - 1024;
                        end else g_bidx[p] <= g_bidx[p] + 1;
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
                    for (c = 0; c < 8; c = c + 1) cc[{d_q, c[2:0]} ^ d_fold][d_slot] <= 1'b0;
                    d_q <= d_q + 1;
                end
                if (d_step) begin
                    adv <= 1'b1;
                    d_hi <= d_hi + 1;
                    d_abs <= d_abs + 1;
                    d_bidx <= n_bidx;
                    d_rem <= n_rem;
                    d_kb <= n_kb;
                end
                if (!d_live) run <= 1'b0;
            end else if (busy && !dr_quarter) busy <= 1'b0;
        end
    end
endmodule

// ---------------------------------------------------------------------------
// The datapath: ROB banks, the scale buffer, key assembly, the output register.
// A quarter command at cycle t reads the 8 banks and the scale word; the beat
// is registered at t+1.  dr_ready: the output register is free or leaving.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kdata #(
    parameter integer NPC  = 32,
    parameter integer WB   = 32,
    parameter integer TAGW = 16,
    parameter integer BEATW = 4,
    parameter integer DW   = 256
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NPC-1:0]        rsp_v,
    input  wire [NPC-1:0]        rsp_rdy,
    input  wire [NPC*TAGW-1:0]   rsp_tag,
    input  wire [NPC*BEATW-1:0]  rsp_beat,
    input  wire [NPC*DW-1:0]     rsp_data,
    input  wire                  dr_scale,
    input  wire                  dr_quarter,
    input  wire [$clog2(WB)-1:0] dr_slot,
    input  wire [1:0]            dr_q,
    input  wire [4:0]            dr_fold,
    input  wire [5:0]            dr_sidx,
    input  wire [4:0]            dr_nkeys,
    output wire                  dr_ready,
    output reg                   o_valid,
    input  wire                  o_ready,
    output reg  [15:0]           o_kv,
    output reg  [16*544-1:0]     o_key
);
    reg [4*DW-1:0] rob [0:NPC-1][0:WB-1];     // one bank per pseudo-channel (SRAM on silicon)
    reg [511:0]    sbuf [0:63];               // the super-block's scales, 16 keys per word
    integer p, c, i, w;
    always @(posedge clk)
        for (p = 0; p < NPC; p = p + 1)
            if (rsp_v[p] && rsp_rdy[p]) rob[p][rsp_tag[p*TAGW +: TAGW] % WB][DW * rsp_beat[p*BEATW +: 2] +: DW] <= rsp_data[p*DW +: DW];
    // scale block: sector s = column s/4, beat s%4; word e = sectors 2e, 2e+1
    always @(posedge clk)
        if (dr_scale)
            for (w = 0; w < 64; w = w + 1)
                sbuf[w] <= rob[(w >> 1) ^ dr_fold][dr_slot][512 * (w & 1) +: 512];
    // a 2-entry output queue: a quarter decided at edge t is written at edge t+1,
    // so the control may decide one only while (entries after this edge) <= 1
    reg [16*544+15:0] ob;                     // second entry (o_* is the head)
    reg               obv;
    wire pop = o_valid && o_ready;
    wire [1:0] occ = {1'b0, o_valid} + {1'b0, obv};
    assign dr_ready = (occ + (dr_quarter ? 2'd1 : 2'd0) - (pop ? 2'd1 : 2'd0)) <= 2'd1;
    reg [511:0] sw;
    reg [16*544-1:0] nk;
    reg [15:0] nkv;
    always @* begin
        sw = sbuf[dr_sidx];
        for (i = 0; i < 16; i = i + 1) begin
            c = {dr_q, i[3:1]};
            nk[544*i +: 544] = {sw[32*i +: 32], rob[c ^ dr_fold][dr_slot][512 * (i & 1) +: 512]};
            nkv[i] = (i < dr_nkeys);
        end
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            o_valid <= 1'b0; obv <= 1'b0;
        end else begin
            // the head leaves; the second entry (or the new beat) moves up
            if (!o_valid || pop) begin
                if (obv) begin
                    {o_kv, o_key} <= ob; o_valid <= 1'b1;
                    if (dr_quarter) ob <= {nkv, nk}; else obv <= 1'b0;
                end else if (dr_quarter) begin
                    {o_kv, o_key} <= {nkv, nk}; o_valid <= 1'b1;
                end else o_valid <= 1'b0;
            end else if (dr_quarter) begin
                ob <= {nkv, nk}; obv <= 1'b1;
            end
        end
    end
endmodule

// One stack's key stream: control + datapath.
module ot_hdc_v41x_idx_kstream #(
    parameter integer NPC  = 32,
    parameter integer WB   = 32,
    parameter integer GA   = 64,
    parameter integer AW   = 24,
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 cmd_v,
    input  wire [HW-1:0]        cmd_base,
    input  wire [HW+9:0]        cmd_nkeys,
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
    wire       kbusy;
    assign busy = kbusy || o_valid;
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
    ot_hdc_v41x_idx_kctl #(.NPC(NPC), .WB(WB), .GA(GA), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW)) u_c (
        .clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_nkeys(cmd_nkeys), .busy(kbusy),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot),
        .dr_q(dr_q), .dr_fold(dr_fold), .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready));
    ot_hdc_v41x_idx_kdata #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
        .rsp_data(rsp_data),
        .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot), .dr_q(dr_q), .dr_fold(dr_fold),
        .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready),
        .o_kv(o_kv), .o_key(o_key));
endmodule

// ---------------------------------------------------------------------------
// Die merge, QUARTER ORDER (contract with the 4 x 16 streaming select).
// A scan of N >= 1 keys is split into 4 contiguous position quarters:
//   Qs = 8 floor(N / 32);  quarter q < 3: [q Qs, (q+1) Qs);  quarter 3:
//   [3 Qs, N), length L3 = N - 3 Qs in [Qs, Qs + 31] -- never empty, every
//   quarter start a multiple of 8 (N < 32: quarters 0-2 empty, all on port 3).
// Beats: B = ceil(L3 / 16).  Beat b, lane group q (lanes 16q .. 16q+15) holds
// positions q Qs + 16 b + (0..15), present (o_kv) while 16 b + lane < L_q: a
// lane prefix.  o_last[q] marks port q's last beat (beat ceil(L_q/16) - 1, or
// beat 0 for an empty quarter, with an empty prefix); a port ignores beats
// after its last.  The image holds 4 B groups of 16 keys: group g = quarter
// g mod 4, beat g / 4, on stack g mod NS (lanes past L_q are padding keys);
// the per-stack streams are unchanged.  A beat leaves only when all 4 of its
// groups are in.  valid/ready both sides; cmd_v/cmd_nkeys start a scan (N).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kmerge #(
    parameter integer NS = 5,
    parameter integer FQ = 4            // FIFO depth per stack (groups)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  cmd_v,
    input  wire [29:0]           cmd_nkeys,
    input  wire [NS-1:0]         i_valid,
    output wire [NS-1:0]         i_ready,
    input  wire [NS*16-1:0]      i_kv,
    input  wire [NS*16*544-1:0]  i_key,
    output reg                   o_valid,
    input  wire                  o_ready,
    output reg  [63:0]           o_kv,
    output reg  [3:0]            o_last,
    output reg  [64*544-1:0]     o_key,
    // fail-closed key refusal (the standalone engine's rule, applied at ingest
    // for the pooled path): a key with a UE8M0 scale byte >= 253 (2^126 and up,
    // where every quantiser-produced block holds a code past binary32) is
    // flagged; the consumer faults it.  cnt_refused counts flagged keys.
    output reg  [63:0]           o_ref,
    output reg  [47:0]           cnt_refused
);
    localparam integer GW = 16 * 544 + 16;
    function automatic kref(input [543:0] k);
        kref = (k[519:512] >= 8'd253) || (k[527:520] >= 8'd253) || (k[535:528] >= 8'd253) ||
               (k[543:536] >= 8'd253);
    endfunction
    reg [6:0] nref;
    localparam integer FW = $clog2(FQ + 1);
    reg [GW-1:0] fq [0:NS-1][0:FQ-1];
    reg [FW-1:0] fn [0:NS-1];
    reg [$clog2(FQ)-1:0] fw [0:NS-1], fr [0:NS-1];
    reg [$clog2(NS)-1:0] gs;                     // stack of the next group
    genvar gi;
    generate
        for (gi = 0; gi < NS; gi = gi + 1) begin : g_rdy
            assign i_ready[gi] = (fn[gi] < FQ);
        end
    endgenerate
    // a beat: the 4 groups of stacks gs .. gs+3, all present
    reg [2:0] take;
    reg [NS-1:0] pop;
    integer j, s, jc, sc;
    always @* begin
        take = 4; pop = 0;
        for (jc = 0; jc < 4; jc = jc + 1) begin
            sc = (gs + jc) % NS;
            if (fn[sc] == 0) take = 0;
        end
        if (o_valid && !o_ready) take = 0;
        if (take != 0)
            for (jc = 0; jc < 4; jc = jc + 1) pop[(gs + jc) % NS] = 1'b1;
    end
    // quarter geometry: L0..L2 = Qs = 8 floor(N/32), L3 = N - 3 Qs; bpos = 16 b
    reg [29:0] lq0, lq3, bpos, lb0, lb3;          // lengths, last-beat positions
    wire [29:0] qs_c = {cmd_nkeys[29:5], 3'b000};
    wire [29:0] l3_c = cmd_nkeys - 3 * qs_c;
    always @(posedge clk)
        if (cmd_v) begin
            lq0 <= qs_c;
            lq3 <= l3_c;
            lb0 <= (qs_c == 0) ? 30'd0 : (((qs_c - 30'd1) >> 4) << 4);
            lb3 <= (l3_c == 0) ? 30'd0 : (((l3_c - 30'd1) >> 4) << 4);
            bpos <= 0;
        end else if (take != 0) bpos <= bpos + 30'd16;
    reg [63:0] lkv;                               // lanes present (the prefixes)
    integer lq;
    always @* for (lq = 0; lq < 64; lq = lq + 1)
        lkv[lq] = (bpos + (lq % 16)) < ((lq >= 48) ? lq3 : lq0);
    reg [GW-1:0] g;
    always @(posedge clk) begin
        if (!rst_n) begin
            o_valid <= 1'b0; gs <= 0; cnt_refused <= 0;
            for (s = 0; s < NS; s = s + 1) begin fn[s] <= 0; fw[s] <= 0; fr[s] <= 0; end
        end else begin
            if (o_valid && o_ready) o_valid <= 1'b0;
            for (s = 0; s < NS; s = s + 1) begin
                if (i_valid[s] && i_ready[s]) begin
                    fq[s][fw[s]] <= {i_kv[16*s +: 16], i_key[16*544*s +: 16*544]};
                    fw[s] <= (fw[s] == FQ - 1) ? 0 : fw[s] + 1;
                end
                if (pop[s]) fr[s] <= (fr[s] == FQ - 1) ? 0 : fr[s] + 1;
                fn[s] <= fn[s] + ((i_valid[s] && i_ready[s]) ? 1 : 0) - (pop[s] ? 1 : 0);
            end
            if (take != 0) begin
                nref = 0;
                for (j = 0; j < 4; j = j + 1) begin
                    s = (gs + j) % NS;
                    g = fq[s][fr[s]];
                    o_kv[16*j +: 16] <= g[GW-1 -: 16] & lkv[16*j +: 16];
                    o_last[j] <= (bpos == ((j == 3) ? lb3 : lb0));
                    o_key[16*544*j +: 16*544] <= g[16*544-1:0];
                    for (sc = 0; sc < 16; sc = sc + 1) begin
                        o_ref[16*j + sc] <= kref(g[544*sc +: 544]);
                        if (g[16*544 + sc] && lkv[16*j + sc] && kref(g[544*sc +: 544])) nref = nref + 1;
                    end
                end
                cnt_refused <= cnt_refused + nref;
                o_valid <= 1'b1;
                gs <= (gs + take) % NS;
            end
        end
    end
endmodule
