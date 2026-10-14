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
    localparam integer BW = TAGW - 4; // high tag bits hold the first sector's offset in its 4-sector column

    reg [HW-1:0]   base;
    reg [HW-1:0]   nblk;                      // blocks in the scan
    reg            run;
    reg [9:0]      first_skip;
    wire [HW+9:0] cmd_span=cmd_nkeys+{{HW{1'b0}},cmd_skip};
    // segment 2 follows segment 1's (possibly partial) last super-block
    reg [HW-1:0]   nblk1, base2;
    reg [HW+9:0]   span2;
    function automatic [HW-1:0] blocks(input [HW+9:0] span);
        blocks = 17 * (span >> 10) + ((span[9:0] != 0) ? (1 + ((span[9:0] + 10'd63) >> 6)) : 0);
    endfunction

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
    function automatic [7:0] lower(input [4:0] bidx,input [9:0] skip);
        reg [10:0] first;
        begin
            if(bidx==0) lower={1'b0,skip[9:3]};
            else begin
                first=11'(64*(bidx-1));
                if(skip<=first) lower=0;
                else if(skip>=first+64) lower=128;
                else lower=8'(2*(skip-first));
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
    reg [1:0]      nx_off [0:NPC-1];
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
    reg [7:0]    gn,glo;
    reg [8:0]    ge,lo_sec,hi_sec,col_sec;
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
                first_skip<=cmd_skip;
                // 17 blocks per full super-block; a partial one: 1 + ceil(m / 64)
                nblk1 <= blocks(cmd_span);
                nblk <= blocks(cmd_span) + blocks(cmd_nkeys2);
                base2 <= cmd_base2; span2 <= cmd_nkeys2;
                run <= 1'b1; busy <= 1'b1;
                d_hi <= 0; d_abs <= cmd_base; d_bidx <= 0; d_rem <= cmd_span; d_q <= 0; d_kb <= 0;
                nx_v <= 0;
                for (p = 0; p < NPC; p = p + 1) begin
                    g_hi[p] <= 0; g_abs[p] <= cmd_base; g_bidx[p] <= 0; g_rem[p] <= cmd_span;
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
                            req_tag[p*TAGW +: TAGW] <= {nx_off[p],2'b00,nx_hi[p][BW-1:0]};
                        end
                    end
                    // prepare the next one
                    prep = (!nx_v[p] || iss) && (g_hi[p] < nblk);
                    if (prep) begin
                        gc = p[4:0] ^ fold(g_abs[p]);
                        gn = need(g_bidx[p], sbkeys(g_rem[p]));
                        glo = (g_hi[p]<17 && g_hi[p]<nblk1) ? lower(g_bidx[p],first_skip) : 8'd0;
                        col_sec={2'b00,gc,2'b00};
                        lo_sec=({1'b0,glo}>col_sec) ? {1'b0,glo} : col_sec;
                        hi_sec=({1'b0,gn}<col_sec+4) ? {1'b0,gn} : col_sec+4;
                        ge=(hi_sec>lo_sec) ? hi_sec-lo_sec : 9'd0;
                        gl=ge[2:0];
                        nx_hi[p] <= g_hi[p];
                        nx_len[p] <= gl;
                        nx_off[p]<=2'(lo_sec-col_sec);
                        nx_addr[p] <= {g_abs[p], gc, 2'b00}+AW'(lo_sec-col_sec);
                        g_hi[p] <= g_hi[p] + 1;
                        if (g_hi[p] + 1'b1 == nblk1) begin
                            // wrap: continue at the ring's first super-block
                            g_abs[p] <= base2; g_bidx[p] <= 0; g_rem[p] <= span2;
                        end else begin
                            g_abs[p] <= g_abs[p] + 1;
                            if (g_bidx[p] == 16) begin
                                g_bidx[p] <= 0;
                                g_rem[p] <= g_rem[p] - 1024;
                            end else g_bidx[p] <= g_bidx[p] + 1;
                        end
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
                    if (d_hi + 1'b1 == nblk1) begin
                        d_abs <= base2; d_bidx <= 0; d_rem <= span2; d_kb <= 0;
                    end else begin
                        d_abs <= d_abs + 1;
                        d_bidx <= n_bidx;
                        d_rem <= n_rem;
                        d_kb <= n_kb;
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
    parameter integer DW   = 256
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
    ot_hdc_v41x_idx_kdata #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat_adj),
        .rsp_data(rsp_data),
        .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot), .dr_q(dr_q), .dr_fold(dr_fold),
        .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready),
        .o_kv(o_kv), .o_key(o_key));
endmodule
