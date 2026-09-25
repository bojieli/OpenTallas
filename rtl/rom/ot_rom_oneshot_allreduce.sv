`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One-shot fixed-order collectives of a 4-die tensor group (one ROM-array
// package: docs/ARCHITECTURE_ATLAS.html 6.6-6.8,
// results/roofline/critical_path/decode_critical_path.json "one_shot").
//
// Every die sends its record stream ONCE to every other die (one UCIe link
// crossing) and each die combines the N streams itself, in RANK order:
//
//   ALL-REDUCE (mode 0)  y = ((p0 + p1) + p2) + p3, lane by lane, binary32
//                        (tools/hdc_golden.fold).  The order is fixed by rank,
//                        never by arrival, so all N dies hold the same bits.
//   ALL-GATHER (mode 1)  the N words of one index are delivered in rank order
//                        (index-major: r0 w0, r1 w0, ..., r0 w1, ...); no
//                        arithmetic, bit-transparent (the argmax gather).
//
// Three modules:
//
// ot_rom_oneshot_die    the per-die engine (what sits on each die; this is the
//                       block routed on ASAP7).  One local port from the die's
//                       sequencer; a broadcast transmit bundle to the N-1 links;
//                       N-1 receive ports; a credit per (source, destination).
//                       Fully pipelined: one word of LANES binary32 lanes per
//                       cycle in, one reduced word per cycle out, latency
//                       2 + (N-1) * ADD_LAT after the last partial of a word
//                       lands.  Each source has a DEPTH-word receive FIFO on
//                       every die; a sender transmits only while it holds a
//                       credit for every destination FIFO, so a FIFO can never
//                       overflow (an overflow is still checked and faults).
// ot_rom_ucie_link      the link model: LAT cycles of flight (hop latency of
//                       configs/hardware/technology.json links.rom_package_ucie,
//                       10 ns, times the clock) and a byte-rate limit
//                       (BPC_NUM / BPC_DEN bytes per cycle, a token bucket of
//                       4 TB/s per die pair and direction divided by the clock);
//                       credits return over the same link, LAT cycles too.
// ot_rom_oneshot_allreduce  the package: N engines and N(N-1) links, a
//                       point-to-point full mesh ("every die in a four-die
//                       package has a direct link to every other").
//
// FAIL CLOSED.  The adders are the qualified ot_fp32_add_rne_pipe: a NaN or
// infinite partial, or a sum past the finite range, raises `err`; the word
// leaves with out_err and the die's `fault` latches.  Records of one word
// index must agree on mode and tag (the step and segment they belong to) on
// every source, or the die faults: a collective never mixes two steps.
// ---------------------------------------------------------------------------
module ot_rom_oneshot_die #(
    parameter integer N       = 4,
    parameter integer RANK    = 0,
    parameter integer LANES   = 16,           // binary32 lanes per word
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 16,           // receive FIFO words per source (power of two)
    parameter integer ADD_LAT = 5,            // ot_fp32_add_rne_pipe latency
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW, // record: {tag, mode, last, data}
    parameter integer RB      = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // local port (the die's sequencer)
    input  wire              in_valid,
    output wire              in_ready,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,         // 0 all-reduce, 1 all-gather
    input  wire [TAGW-1:0]   in_tag,
    // transmit: one record broadcast to every remote link
    output wire              tx_valid,
    output wire [PW-1:0]     tx_rec,
    input  wire [N-1:0]      tx_ready,        // per destination link (bit RANK ignored)
    input  wire [N-1:0]      cr_in,           // a credit back from destination r
    // receive from every remote source (bit / slice RANK ignored)
    input  wire [N-1:0]      rx_valid,
    input  wire [N*PW-1:0]   rx_rec,
    output wire [N-1:0]      cr_out,          // a credit back to source r
    // result
    output wire              out_valid,
    output wire [FW-1:0]     out_data,
    output wire              out_last,
    output wire [RB-1:0]     out_rank,
    output wire              out_err,
    output reg               fault,
    output reg  [2:0]        fault_code       // [0] arithmetic, [1] tag / mode mismatch, [2] FIFO overflow
);
    localparam integer DB = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer CB = $clog2(DEPTH + 1);
    localparam integer DL = (N - 1) * ADD_LAT;          // reduce latency after the head stage

    // -- credits and transmit ---------------------------------------------------------
    reg  [CB-1:0] cr [0:N-1];
    reg  [N-1:0]  can_tx;
    reg  [CB:0]   cnt [0:N-1];
    integer r;
    always @(*) begin
        for (r = 0; r < N; r = r + 1)
            can_tx[r] = (r == RANK) ? (cnt[r] < DEPTH) : (cr[r] != 0 && tx_ready[r]);
    end
    assign in_ready = &can_tx;
    wire fire = in_valid && in_ready;
    assign tx_valid = fire;
    assign tx_rec = {in_tag, in_mode, in_last, in_data};

    // -- receive FIFOs, one per source rank --------------------------------------------
    reg [PW-1:0] mem [0:N*DEPTH-1];
    reg [DB-1:0] wp [0:N-1];
    reg [DB-1:0] rp [0:N-1];
    wire [N-1:0] push;
    wire [N*PW-1:0] push_rec;
    genvar g;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_src
            if (g == RANK) begin : g_loc
                assign push[g] = fire;
                assign push_rec[g*PW +: PW] = tx_rec;
            end else begin : g_rem
                assign push[g] = rx_valid[g];
                assign push_rec[g*PW +: PW] = rx_rec[g*PW +: PW];
            end
        end
    endgenerate

    // heads
    reg  [N-1:0] nonempty;
    reg  [PW-1:0] head [0:N-1];
    always @(*) begin
        for (r = 0; r < N; r = r + 1) begin
            nonempty[r] = (cnt[r] != 0);
            head[r] = mem[r*DEPTH + rp[r]];
        end
    end
    wire head_mode = head[0][FW + 1];

    // -- pop: a word index leaves every FIFO at once ---------------------------------------
    reg          g_busy;                 // all-gather words being emitted
    reg  [RB-1:0] g_cnt;
    reg  [15:0]  inflight;               // reduce words between the head stage and the output
    reg          s0_v, s0_mode, s0_last;
    reg  [FW-1:0] s0_d [0:N-1];
    wire all_ne = &nonempty;
    // nothing is popped while the gather's latched words are being emitted
    wire pop_red = all_ne && !g_busy && !(s0_v && s0_mode) && !head_mode;
    wire pop_gat = all_ne && !g_busy && head_mode && inflight == 0 && !s0_v;
    wire pop = pop_red || pop_gat;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_cr
            if (g == RANK) begin : g_l
                assign cr_out[g] = 1'b0;
            end else begin : g_r
                assign cr_out[g] = pop;
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (r = 0; r < N; r = r + 1) begin
                cr[r] <= DEPTH; cnt[r] <= 0; wp[r] <= 0; rp[r] <= 0;
            end
        end else begin
            for (r = 0; r < N; r = r + 1) begin
                if (r != RANK) cr[r] <= cr[r] - (fire ? 1'b1 : 1'b0) + (cr_in[r] ? 1'b1 : 1'b0);
                if (push[r]) begin
                    mem[r*DEPTH + wp[r]] <= push_rec[r*PW +: PW];
                    wp[r] <= wp[r] + 1'b1;
                end
                if (pop) rp[r] <= rp[r] + 1'b1;
                cnt[r] <= cnt[r] + (push[r] ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            end
        end
    end

    // -- head stage: the popped word of every source, registered -----------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s0_v <= 1'b0; s0_mode <= 1'b0; s0_last <= 1'b0;
        end else begin
            s0_v <= pop;
            // held while a gather emits its latched words
            if (pop) begin s0_mode <= head_mode; s0_last <= head[0][FW]; end
        end
    end
    // the popped words and their {tag, mode}; the sources' tags are compared
    // from these registers, a cycle after the pop (the fault is sticky)
    reg [TAGW:0] s0_t [0:N-1];
    always @(posedge clk) if (pop) for (r = 0; r < N; r = r + 1) begin
        s0_d[r] <= head[r][FW-1:0];
        s0_t[r] <= head[r][PW-1 -: TAGW + 1];
    end
    reg agree;
    always @(*) begin
        agree = 1'b1;
        for (r = 1; r < N; r = r + 1) if (s0_t[r] != s0_t[0]) agree = 1'b0;
    end

    // -- all-reduce: ((p0 + p1) + p2) + ... in rank order ---------------------------------------
    wire red_in = s0_v && !s0_mode;
    wire [FW-1:0] sum  [0:N-1];
    wire [N-1:0]  sv;
    wire [N-1:0]  serr;                  // error of this stage or an earlier one, aligned
    assign sum[0] = s0_d[0];
    assign sv[0] = red_in;
    assign serr[0] = 1'b0;
    generate
        for (g = 1; g < N; g = g + 1) begin : g_stage
            // partial g waits (g-1) adder latencies for the running sum
            wire [FW-1:0] pg;
            if (g == 1) begin : g_nd
                assign pg = s0_d[1];
            end else begin : g_d
                localparam integer D = (g - 1) * ADD_LAT;
                reg [FW*D-1:0] dl;
                always @(posedge clk) dl <= {dl[FW*(D-1)-1:0], s0_d[g]};
                assign pg = dl[FW*D-1 -: FW];
            end
            reg [ADD_LAT-1:0] edl;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) edl <= 0;
                else edl <= {edl[ADD_LAT-2:0], serr[g-1]};
            wire [LANES-1:0] lv;
            wire [2*LANES-1:0] le;
            genvar l;
            for (l = 0; l < LANES; l = l + 1) begin : g_lane
                ot_fp32_add_rne_pipe u_add (
                    .clk(clk), .rst_n(rst_n), .valid_in(sv[g-1]),
                    .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                    .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
            end
            assign sv[g] = lv[0];
            assign serr[g] = (|le) || edl[ADD_LAT-1];
        end
    endgenerate
    reg [DL-1:0] ldl;                    // `last` beside the adders
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ldl <= 0;
        else ldl <= {ldl[DL-2:0], s0_last};
    wire red_out = sv[N-1];

    // -- all-gather: emit the N latched words in rank order ---------------------------------
    reg          go_v, go_last;
    reg [FW-1:0] go_d;
    reg [RB-1:0] go_rank;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            g_busy <= 1'b0; g_cnt <= 0; go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; inflight <= 0;
        end else begin
            go_v <= 1'b0;
            if (s0_v && s0_mode) begin g_busy <= 1'b1; g_cnt <= 0; end
            if (g_busy || (s0_v && s0_mode)) begin
                go_v <= 1'b1;
                go_d <= s0_d[g_busy ? g_cnt : 0];
                go_rank <= g_busy ? g_cnt : 0;
                go_last <= s0_last && (g_busy ? g_cnt : 0) == N - 1;
                if (g_busy) begin
                    g_cnt <= g_cnt + 1'b1;
                    if (g_cnt == N - 1) g_busy <= 1'b0;
                end else begin
                    g_cnt <= 1;
                    if (N == 1) g_busy <= 1'b0;
                end
            end
            inflight <= inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
        end
    end

    assign out_valid = red_out || go_v;
    assign out_data  = go_v ? go_d : sum[N-1];
    assign out_last  = go_v ? go_last : ldl[DL-1];
    assign out_rank  = go_v ? go_rank : {RB{1'b0}};
    assign out_err   = red_out && serr[N-1];

    // -- faults ---------------------------------------------------------------------------
    // a push into a full FIFO leaves its count past DEPTH (seen a cycle later)
    reg ovf;
    always @(*) begin
        ovf = 1'b0;
        for (r = 0; r < N; r = r + 1) if (cnt[r] > DEPTH) ovf = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault <= 1'b0; fault_code <= 3'b0;
        end else begin
            if (out_err) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if (s0_v && !agree) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// UCIe-class die-to-die link model: LAT cycles of flight each way and a byte
// rate of BPC_NUM / BPC_DEN bytes per cycle (token bucket; a record costs its
// flit bytes).  Credits travel back with the same latency.
// ---------------------------------------------------------------------------
module ot_rom_ucie_link #(
    parameter integer PW         = 546,
    parameter integer LAT        = 11,
    parameter integer FLIT_BYTES = 64,
    parameter integer BPC_NUM    = 3600,
    parameter integer BPC_DEN    = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_valid,
    input  wire [PW-1:0] in_rec,
    output wire          in_ready,
    output wire          out_valid,
    output wire [PW-1:0] out_rec,
    input  wire          cr_in,          // at the receiving die
    output wire          cr_out          // at the sending die
);
    localparam integer CAP = ((BPC_NUM > FLIT_BYTES * BPC_DEN) ? BPC_NUM : FLIT_BYTES * BPC_DEN);
    localparam integer COST = FLIT_BYTES * BPC_DEN;
    reg [31:0] tokens;
    assign in_ready = tokens >= COST;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tokens <= CAP;
        else tokens <= ((tokens - ((in_valid && in_ready) ? COST : 0) + BPC_NUM) > CAP) ? CAP
                       : (tokens - ((in_valid && in_ready) ? COST : 0) + BPC_NUM);
    end
    reg [LAT-1:0]    v_line, c_line;
    reg [PW*LAT-1:0] d_line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v_line <= 0; c_line <= 0;
        end else begin
            v_line <= (LAT > 1) ? {v_line[LAT-2:0], in_valid && in_ready} : in_valid && in_ready;
            c_line <= (LAT > 1) ? {c_line[LAT-2:0], cr_in} : cr_in;
        end
    end
    always @(posedge clk) d_line <= (LAT > 1) ? {d_line[PW*(LAT-1)-1:0], in_rec} : in_rec;
    assign out_valid = v_line[LAT-1];
    assign out_rec   = d_line[PW*LAT-1 -: PW];
    assign cr_out    = c_line[LAT-1];
endmodule

// ---------------------------------------------------------------------------
// The package: N dies' engines on a full mesh of UCIe links.
// ---------------------------------------------------------------------------
module ot_rom_oneshot_allreduce #(
    parameter integer N          = 4,
    parameter integer LANES      = 16,
    parameter integer TAGW       = 32,
    parameter integer DEPTH      = 16,
    parameter integer LAT        = 11,
    parameter integer BPC_NUM    = 3600,
    parameter integer BPC_DEN    = 1,
    parameter integer FW         = 32 * LANES,
    parameter integer RB         = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      in_valid,
    output wire [N-1:0]      in_ready,
    input  wire [N*FW-1:0]   in_data,
    input  wire [N-1:0]      in_last,
    input  wire [N-1:0]      in_mode,
    input  wire [N*TAGW-1:0] in_tag,
    output wire [N-1:0]      out_valid,
    output wire [N*FW-1:0]   out_data,
    output wire [N-1:0]      out_last,
    output wire [N*RB-1:0]   out_rank,
    output wire [N-1:0]      out_err,
    output wire [N-1:0]      fault,
    output wire [N*3-1:0]    fault_code,
    output reg  [31:0]       link_stalls       // cycles a die held a word back (credits or link rate)
);
    localparam integer PW = FW + 2 + TAGW;
    wire [N-1:0]    txv;
    wire [N*PW-1:0] txr;
    wire [N*N-1:0]  txrdy;       // [s*N + r]: link s -> r ready
    wire [N*N-1:0]  crin;        // [s*N + r]: credit at s from r
    wire [N*N-1:0]  rxv;         // [r*N + s]: at r from s
    wire [N*N*PW-1:0] rxr;
    wire [N*N-1:0]  crout;       // [r*N + s]: credit from r to s
    genvar s, t;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_die
            ot_rom_oneshot_die #(.N(N), .RANK(s), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH)) u_die (
                .clk(clk), .rst_n(rst_n),
                .in_valid(in_valid[s]), .in_ready(in_ready[s]), .in_data(in_data[s*FW +: FW]),
                .in_last(in_last[s]), .in_mode(in_mode[s]), .in_tag(in_tag[s*TAGW +: TAGW]),
                .tx_valid(txv[s]), .tx_rec(txr[s*PW +: PW]), .tx_ready(txrdy[s*N +: N]), .cr_in(crin[s*N +: N]),
                .rx_valid(rxv[s*N +: N]), .rx_rec(rxr[s*N*PW +: N*PW]), .cr_out(crout[s*N +: N]),
                .out_valid(out_valid[s]), .out_data(out_data[s*FW +: FW]), .out_last(out_last[s]),
                .out_rank(out_rank[s*RB +: RB]), .out_err(out_err[s]),
                .fault(fault[s]), .fault_code(fault_code[s*3 +: 3]));
            for (t = 0; t < N; t = t + 1) begin : g_to
                if (t == s) begin : g_self
                    assign txrdy[s*N + t] = 1'b1;
                    assign crin[s*N + t] = 1'b0;
                    assign rxv[s*N + t] = 1'b0;
                    assign rxr[(s*N + t)*PW +: PW] = {PW{1'b0}};
                end else begin : g_link
                    // link s -> t: data to die t's port s, credits from die t's port s back to s
                    ot_rom_ucie_link #(.PW(PW), .LAT(LAT), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC_NUM),
                                       .BPC_DEN(BPC_DEN)) u_link (
                        .clk(clk), .rst_n(rst_n),
                        .in_valid(txv[s]), .in_rec(txr[s*PW +: PW]), .in_ready(txrdy[s*N + t]),
                        .out_valid(rxv[t*N + s]), .out_rec(rxr[(t*N + s)*PW +: PW]),
                        .cr_in(crout[t*N + s]), .cr_out(crin[s*N + t]));
                end
            end
        end
    endgenerate
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) link_stalls <= 0;
        else for (k = 0; k < N; k = k + 1) if (in_valid[k] && !in_ready[k]) link_stalls <= link_stalls + 1;
    end
endmodule
