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
    parameter integer GA   = 64,        // request lookahead in blocks (>= WB)
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
    localparam integer SW = $clog2(WB);
    localparam integer CW = (NPC > 1) ? $clog2(NPC) : 1;

    // scan parameters
    reg [HW-1:0]   base;
    reg [HW+9:0]   nkeys;
    reg [HW-1:0]   nblk;                      // blocks in the scan
    reg            run;

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction
    // keys in super-block from `rem` keys remaining at its start
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

    // -- completion, per bank and ROB entry ---------------------------------------------------
    // The HBM scheduler reorders bursts within a pseudo-channel (FR-FCFS), so beats
    // do not return in request order: each entry counts its own.  issued: the
    // entry holds its block's column; left: beats still to come.  A request's tag
    // is {length, block mod 2^BW}.
    localparam integer BW = TAGW - 3;
    reg [WB-1:0] issued [0:NPC-1];
    reg [2:0]    left   [0:NPC*WB-1];
    reg [NPC-1:0] done;
    integer b, c;
    always @* begin
        for (b = 0; b < NPC; b = b + 1)
            done[b] = issued[b][d_slot] && (left[b * WB + d_slot] == 3'd0);
    end

    // -- generators ---------------------------------------------------------------------
    reg [HW-1:0]   g_hi   [0:NPC-1];
    reg [4:0]      g_bidx [0:NPC-1];
    reg [HW+9:0]   g_rem  [0:NPC-1];

    // -- drain state --------------------------------------------------------------------
    reg [HW-1:0]   d_hi;                      // head block (relative)
    reg [4:0]      d_bidx;                    // block within its super-block (0 = scales)
    reg [HW+9:0]   d_rem;                     // keys from the head super-block's start
    reg [1:0]      d_q;
    wire [HW-1:0]  d_abs = base + d_hi;
    wire [4:0]     d_fold = fold(d_abs);
    wire [SW-1:0]  d_slot = d_hi[SW-1:0];
    wire [10:0]    d_m = sbkeys(d_rem);
    wire [11:0]    d_kb = (d_bidx == 0) ? 12'd0 :
                          ((d_m > 64 * (d_bidx - 1)) ? ((d_m - 64 * (d_bidx - 1) >= 64) ? 12'd64 : d_m - 64 * (d_bidx - 1))
                                                     : 12'd0);
    wire [12:0]    d_qk = (d_kb > 16 * d_q) ? d_kb - 16 * d_q : 13'd0;   // keys in this quarter (before cap)
    reg            all_in, q_in;
    always @* begin
        all_in = &done;
        q_in = 1'b1;
        for (c = 0; c < 8; c = c + 1)
            if (!done[{d_q, c[2:0]} ^ d_fold]) q_in = 1'b0;
    end
    wire d_live = run && (d_hi < nblk);
    wire do_scale = d_live && (d_bidx == 0) && all_in;
    wire do_q = d_live && (d_bidx != 0) && q_in && (d_qk == 0 || dr_ready);

    // a beat is taken only when its block has a ROB entry (within WB of the head);
    // otherwise its channel's return queue holds it and that channel alone stops
    genvar gq;
    generate
        for (gq = 0; gq < NPC; gq = gq + 1) begin : g_rr
            wire [BW-1:0] ahead = rsp_tag[gq*TAGW +: BW] - d_hi[BW-1:0];
            assign rsp_rdy[gq] = (ahead < WB);
        end
    endgenerate


    integer p, s;
    reg [HW-1:0] ga;
    reg [4:0]    gc;
    reg [7:0]    gn;
    reg [8:0]    ge;
    reg [2:0]    gl;
    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; req_v <= 0;
            dr_scale <= 1'b0; dr_quarter <= 1'b0;
            for (p = 0; p < NPC; p = p + 1) begin issued[p] <= 0; g_hi[p] <= 0; end
        end else begin
            dr_scale <= 1'b0;
            dr_quarter <= 1'b0;
            if (cmd_v && !busy) begin
                base <= cmd_base;
                nkeys <= cmd_nkeys;
                // 17 blocks per full super-block; a partial one: 1 + ceil(m / 64)
                nblk <= 17 * (cmd_nkeys >> 10) +
                        ((cmd_nkeys[9:0] != 0) ? (1 + ((cmd_nkeys[9:0] + 10'd63) >> 6)) : 0);
                run <= 1'b1; busy <= 1'b1;
                d_hi <= 0; d_bidx <= 0; d_rem <= cmd_nkeys; d_q <= 0;
                for (p = 0; p < NPC; p = p + 1) begin
                    g_hi[p] <= 0; g_bidx[p] <= 0; g_rem[p] <= cmd_nkeys;
                end
            end else if (run) begin
                // generators
                for (p = 0; p < NPC; p = p + 1) begin
                    if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                    if ((!req_v[p] || req_rdy[p]) && g_hi[p] < nblk && (g_hi[p] - d_hi) < GA) begin
                        ga = base + g_hi[p];
                        gc = p[4:0] ^ fold(ga);
                        gn = need(g_bidx[p], sbkeys(g_rem[p]));
                        ge = ({1'b0, gn} > {2'b0, gc, 2'b00}) ? ({1'b0, gn} - {2'b0, gc, 2'b00}) : 9'd0;
                        gl = (ge >= 4) ? 3'd4 : ge[2:0];
                        s = g_hi[p] % WB;
                        issued[p][s] <= 1'b1;
                        left[p * WB + s] <= gl;
                        if (gl != 0) begin
                            req_v[p] <= 1'b1;
                            req_addr[p*AW +: AW] <= {ga, gc, 2'b00};
                            req_len[p*LENW +: LENW] <= gl;
                            req_tag[p*TAGW +: TAGW] <= {gl, g_hi[p][BW-1:0]};
                        end
                        g_hi[p] <= g_hi[p] + 1;
                        if (g_bidx[p] == 16) begin
                            g_bidx[p] <= 0;
                            g_rem[p] <= g_rem[p] - 1024;
                        end else g_bidx[p] <= g_bidx[p] + 1;
                    end
                end
                // responses
                for (p = 0; p < NPC; p = p + 1)
                    if (rsp_v[p] && rsp_rdy[p])
                        left[p * WB + rsp_tag[p*TAGW +: SW]] <= left[p * WB + rsp_tag[p*TAGW +: SW]] - 3'd1;
                // drain
                if (do_scale) begin
                    dr_scale <= 1'b1;
                    dr_slot <= d_slot;
                    dr_fold <= d_fold;
                    for (p = 0; p < NPC; p = p + 1) issued[p][d_slot] <= 1'b0;
                    d_hi <= d_hi + 1;
                    d_bidx <= 1;
                end else if (do_q) begin
                    if (d_qk != 0) begin
                        dr_quarter <= 1'b1;
                        dr_slot <= d_slot;
                        dr_q <= d_q;
                        dr_fold <= d_fold;
                        dr_sidx <= {d_bidx[3:0] - 4'd1, d_q};
                        dr_nkeys <= (d_qk >= 16) ? 5'd16 : d_qk[4:0];
                    end
                    for (c = 0; c < 8; c = c + 1) issued[{d_q, c[2:0]} ^ d_fold][d_slot] <= 1'b0;
                    d_q <= d_q + 1;
                    if (d_q == 3) begin
                        d_hi <= d_hi + 1;
                        if (d_bidx == 16) begin
                            d_bidx <= 0;
                            d_rem <= d_rem - 1024;
                        end else d_bidx <= d_bidx + 1;
                    end
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
    output wire [16*544-1:0]    o_key
);
    wire dr_scale, dr_quarter, dr_ready;
    wire [$clog2(WB)-1:0] dr_slot;
    wire [1:0] dr_q;
    wire [4:0] dr_fold, dr_nkeys;
    wire [5:0] dr_sidx;
    wire       kbusy;
    assign busy = kbusy || o_valid;
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
// Die merge: NS stack streams of 16-key groups -> beats of up to 64 keys in
// position order.  Global group g lives on stack g mod NS (NS >= 4, so the 4
// groups of a beat come from 4 distinct stacks).  Each stack's beats queue in
// a small FIFO; a beat takes the longest run of consecutive groups whose
// stack FIFOs are non-empty (up to 4).  valid/ready both sides.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kmerge #(
    parameter integer NS = 5,
    parameter integer FQ = 4            // FIFO depth per stack (groups)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NS-1:0]         i_valid,
    output wire [NS-1:0]         i_ready,
    input  wire [NS*16-1:0]      i_kv,
    input  wire [NS*16*544-1:0]  i_key,
    output reg                   o_valid,
    input  wire                  o_ready,
    output reg  [63:0]           o_kv,
    output reg  [64*544-1:0]     o_key
);
    localparam integer GW = 16 * 544 + 16;
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
    // groups this cycle: consecutive stacks gs, gs+1, ... with data (<= 4)
    reg [2:0] take;
    reg [NS-1:0] pop;
    integer j, s, jc, sc;
    always @* begin
        take = 0; pop = 0;
        if (!o_valid || o_ready)
            for (jc = 0; jc < 4; jc = jc + 1) begin
                sc = (gs + jc) % NS;
                if (take == jc && fn[sc] != 0) begin take = take + 1; pop[sc] = 1'b1; end
            end
    end
    reg [GW-1:0] g;
    always @(posedge clk) begin
        if (!rst_n) begin
            o_valid <= 1'b0; gs <= 0;
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
                for (j = 0; j < 4; j = j + 1) begin
                    s = (gs + j) % NS;
                    g = fq[s][fr[s]];
                    o_kv[16*j +: 16] <= (j < take) ? g[GW-1 -: 16] : 16'd0;
                    o_key[16*544*j +: 16*544] <= g[16*544-1:0];
                end
                o_valid <= 1'b1;
                gs <= (gs + take) % NS;
            end
        end
    end
endmodule
