`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_oneshot_die_px: the one-shot collective engine of a 4-die tensor group
// that spans a PACKAGE PAIR (V4.1 option (b): two 2-die packages; UCIe inside
// a package, the T1 board link between packages -- docs/ARCH_V41_RACK.md,
// R-L9), with three changes to ot_rom_oneshot_die (rtl/rom/
// ot_rom_oneshot_allreduce.sv, left as it is).  Same arithmetic, same bits:
// the all-reduce is still ((p0 + p1) + p2) + p3 in rank order
// (tools/hdc_golden.fold), and the all-gather still delivers index-major, rank
// order.  Gate C7 / O2 lever bench: tools/rtl_v41_collective_levers_campaign.py.
//
// 1. RECEIVE-SIDE RELAY (RELAY = 1).  The one-shot broadcasts every word to
//    BOTH dies of the partner package, so every word crosses the package
//    boundary twice and the T1 links (13 lanes per die pair) carry the whole
//    partial each.  Here word k (index parity p = k mod 2) of a die goes over
//    T1 only to the partner-package die whose in-package index is p; that die
//    pushes it into its own FIFO and relays it, the cycle it lands, over UCIe
//    to its package peer.  Each T1 link carries half the words; UCIe (4.2 TB/s,
//    26x a T1 link) carries the relayed half.  No link gets new bandwidth.
//    The receive FIFOs are split by index parity, so each (source, parity)
//    stream has exactly one writer (direct link, or relay), and credits are
//    kept per (destination, parity): a sender needs a credit for parity p at
//    EVERY destination, and the relayed copy's credit comes back from the die
//    that pops it, over that die's own T1 link to the sender (full mesh).
//    With RELAY = 0 every word goes to every die directly (the original
//    one-shot schedule, on the parity-split FIFOs).
// 2. ADD_LAT = 3 selects ot_hdc_fp32_add_fast (rtl/hdc/ot_hdc_fastfp.sv, the
//    spec's 3-cycle binary32 add, bit-identical to ot_fp32_add_rne_pipe);
//    ADD_LAT = 5 keeps the qualified five-stage pipe.
// 3. GATHER EMISSION GW words wide, no bubble.  The engine pops all N words of
//    an index into its head registers in one cycle (as before); it now emits
//    them GW per cycle (GW = N: the whole index in one beat) and pops the next
//    index in the cycle it emits the last beat of this one.  The original
//    emits one word per cycle and waits a cycle between indices (5 cycles per
//    4 words), which made the KV-rows all-gather engine-bound.
//
// Record: {tag, mode, last, par, data}; par is the word's index parity.
// FAIL CLOSED as before, plus: a head whose parity is not the pop parity, or a
// direct and a relayed record for the same (source, parity) FIFO in one cycle,
// faults (code bit 1).
// ---------------------------------------------------------------------------
module ot_rom_oneshot_die_px #(
    parameter integer N        = 4,
    parameter integer RANK     = 0,
    parameter integer LANES    = 16,
    parameter integer TAGW     = 32,
    parameter integer DEPTH    = 16,           // receive words per source (both parities; power of two, >= 2)
    parameter integer PKG_DIES = 2,
    parameter integer RELAY    = 1,
    parameter integer ADD_LAT  = 3,            // 3: ot_hdc_fp32_add_fast, 5: ot_fp32_add_rne_pipe
    parameter integer GW       = 1,            // gather words emitted per cycle (divides N)
    parameter integer FW       = 32 * LANES,
    parameter integer PW       = FW + 3 + TAGW, // {tag, mode, last, par, data}
    parameter integer RB       = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_ready,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [TAGW-1:0]   in_tag,
    // transmit: one record, a valid per destination link
    output wire [N-1:0]      tx_valid,
    output wire [PW-1:0]     tx_rec,
    input  wire [N-1:0]      tx_ready,
    input  wire [2*N-1:0]    cr_in,           // [2t + p]: a parity-p credit back from destination t
    // receive, direct link from every remote source
    input  wire [N-1:0]      rx_valid,
    input  wire [N*PW-1:0]   rx_rec,
    output wire [2*N-1:0]    cr_out,          // [2r + p]: a parity-p credit back to source r
    // relay to / from the package peer (one channel per source rank)
    output wire [N-1:0]      rl_tx_valid,
    output wire [N*PW-1:0]   rl_tx_rec,
    input  wire [N-1:0]      rl_rx_valid,
    input  wire [N*PW-1:0]   rl_rx_rec,
    // result
    output wire              out_valid,
    output wire [GW*FW-1:0]  out_data,
    output wire              out_last,
    output wire [RB-1:0]     out_rank,
    output wire              out_err,
    output reg               fault,
    output reg  [2:0]        fault_code       // [0] arithmetic, [1] tag / mode / parity / relay, [2] FIFO overflow
);
    localparam integer PD = DEPTH / 2;                  // words per (source, parity) FIFO
    localparam integer DB = (PD > 1) ? $clog2(PD) : 1;
    localparam integer CB = $clog2(PD + 1);
    localparam integer DL = (N - 1) * ADD_LAT;
    localparam integer E  = N / GW;                     // gather beats per index
    localparam integer EB = (E > 1) ? $clog2(E) : 1;
    localparam integer MYPKG = RANK / PKG_DIES;
    localparam integer PAR_B = FW;                      // record bit positions
    localparam integer LAST_B = FW + 1;
    localparam integer MODE_B = FW + 2;

    function automatic same_pkg(input integer t);
        same_pkg = (t / PKG_DIES) == MYPKG;
    endfunction

    integer r, p;
    genvar g, q;

    // -- transmit ----------------------------------------------------------------------
    reg          lpar;                                  // index parity of the next local word
    reg [CB-1:0] cr  [0:2*N-1];                         // credits per (destination, parity)
    reg [CB:0]   cnt [0:2*N-1];                         // FIFO occupancy per (source, parity)
    reg [N-1:0]  uses, can_tx;
    always @(*) begin
        for (r = 0; r < N; r = r + 1) begin
            uses[r] = (r != RANK) && (same_pkg(r) || RELAY == 0 || (r % PKG_DIES) == lpar);
            if (r == RANK) can_tx[r] = cnt[2*r + lpar] < PD;
            else can_tx[r] = (cr[2*r + lpar] != 0) && (!uses[r] || tx_ready[r]);
        end
    end
    assign in_ready = &can_tx;
    wire fire = in_valid && in_ready;
    assign tx_valid = fire ? uses : {N{1'b0}};
    assign tx_rec = {in_tag, in_mode, in_last, lpar, in_data};

    // -- receive: every (source, parity) FIFO has one writer ------------------------------
    reg [PW-1:0] mem [0:2*N*PD-1];
    reg [DB-1:0] wp [0:2*N-1];
    reg [DB-1:0] rp [0:2*N-1];
    reg [2*N-1:0] push;
    reg [PW-1:0]  push_rec [0:2*N-1];
    reg           relay_clash;
    always @(*) begin
        relay_clash = 1'b0;
        for (r = 0; r < 2 * N; r = r + 1) begin push[r] = 1'b0; push_rec[r] = {PW{1'b0}}; end
        for (r = 0; r < N; r = r + 1) begin
            if (r == RANK) begin
                push[2*r + lpar] = fire;
                push_rec[2*r + lpar] = tx_rec;
            end else begin
                if (rx_valid[r]) begin
                    push[2*r + rx_rec[r*PW + PAR_B]] = 1'b1;
                    push_rec[2*r + rx_rec[r*PW + PAR_B]] = rx_rec[r*PW +: PW];
                end
                if (RELAY != 0 && !same_pkg(r) && rl_rx_valid[r]) begin
                    if (rx_valid[r] && rx_rec[r*PW + PAR_B] == rl_rx_rec[r*PW + PAR_B]) relay_clash = 1'b1;
                    push[2*r + rl_rx_rec[r*PW + PAR_B]] = 1'b1;
                    push_rec[2*r + rl_rx_rec[r*PW + PAR_B]] = rl_rx_rec[r*PW +: PW];
                end
            end
        end
    end
    // a record landing from a partner-package source is relayed to the package peer the cycle it lands
    generate
        for (g = 0; g < N; g = g + 1) begin : g_rl
            if (RELAY != 0 && g != RANK && (g / PKG_DIES) != MYPKG) begin : g_on
                assign rl_tx_valid[g] = rx_valid[g];
                assign rl_tx_rec[g*PW +: PW] = rx_rec[g*PW +: PW];
            end else begin : g_off
                assign rl_tx_valid[g] = 1'b0;
                assign rl_tx_rec[g*PW +: PW] = {PW{1'b0}};
            end
        end
    endgenerate

    // -- heads of the pop parity --------------------------------------------------------
    reg           ppar;                                 // index parity of the next pop
    reg  [N-1:0]  nonempty;
    reg  [PW-1:0] head [0:N-1];
    always @(*) begin
        for (r = 0; r < N; r = r + 1) begin
            nonempty[r] = cnt[2*r + ppar] != 0;
            head[r] = mem[(2*r + ppar)*PD + rp[2*r + ppar]];
        end
    end
    wire head_mode = head[0][MODE_B];
    wire head_last = head[0][LAST_B];

    // -- pop -------------------------------------------------------------------------------
    reg           g_busy;                               // beats 1..E-1 of a gathered index being emitted
    reg  [EB-1:0] g_cnt;
    reg  [15:0]   inflight;
    reg           s0_v, s0_mode, s0_last;
    reg  [FW-1:0] s0_d [0:N-1];
    wire all_ne = &nonempty;
    wire g_first = s0_v && s0_mode;                     // beat 0 of the index in the head registers
    wire g_idle = !g_busy && !g_first;
    // the head registers are free after this cycle when the emitter is idle or emits the index's last beat now
    wire g_free = g_idle || (g_busy && g_cnt == E - 1) || (g_first && E == 1);
    wire pop_red = all_ne && g_idle && !head_mode;
    wire pop_gat = all_ne && head_mode && inflight == 0 && g_free && !(s0_v && !s0_mode);
    wire pop = pop_red || pop_gat;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_cr
            for (q = 0; q < 2; q = q + 1) begin : g_p
                if (g == RANK) begin : g_l
                    assign cr_out[2*g + q] = 1'b0;
                end else begin : g_r
                    assign cr_out[2*g + q] = pop && (ppar == q);
                end
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lpar <= 1'b0; ppar <= 1'b0;
            for (r = 0; r < 2 * N; r = r + 1) begin
                cr[r] <= PD; cnt[r] <= 0; wp[r] <= 0; rp[r] <= 0;
            end
        end else begin
            if (fire) lpar <= in_last ? 1'b0 : ~lpar;
            if (pop) ppar <= head_last ? 1'b0 : ~ppar;
            for (r = 0; r < 2 * N; r = r + 1) begin
                if ((r / 2) != RANK)
                    cr[r] <= cr[r] - ((fire && (r % 2) == lpar) ? 1'b1 : 1'b0) + (cr_in[r] ? 1'b1 : 1'b0);
                if (push[r]) begin
                    mem[r*PD + wp[r]] <= push_rec[r];
                    wp[r] <= wp[r] + 1'b1;
                end
                if (pop && (r % 2) == ppar) rp[r] <= rp[r] + 1'b1;
                cnt[r] <= cnt[r] + (push[r] ? 1'b1 : 1'b0) - ((pop && (r % 2) == ppar) ? 1'b1 : 1'b0);
            end
        end
    end

    // -- head stage -------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s0_v <= 1'b0; s0_mode <= 1'b0; s0_last <= 1'b0;
        end else begin
            s0_v <= pop;
            if (pop) begin s0_mode <= head_mode; s0_last <= head_last; end
        end
    end
    reg [TAGW+1:0] s0_t [0:N-1];                        // {tag, mode, par}
    always @(posedge clk) if (pop) for (r = 0; r < N; r = r + 1) begin
        s0_d[r] <= head[r][FW-1:0];
        s0_t[r] <= {head[r][PW-1 -: TAGW + 1], head[r][PAR_B]};
    end
    reg s0_ppar;
    always @(posedge clk) if (pop) s0_ppar <= ppar;
    reg agree;
    always @(*) begin
        agree = (s0_t[0][0] == s0_ppar);
        for (r = 1; r < N; r = r + 1) if (s0_t[r] != s0_t[0]) agree = 1'b0;
    end

    // -- all-reduce, rank order --------------------------------------------------------------
    wire red_in = s0_v && !s0_mode;
    wire [FW-1:0] sum [0:N-1];
    wire [N-1:0]  sv, serr;
    assign sum[0] = s0_d[0];
    assign sv[0] = red_in;
    assign serr[0] = 1'b0;
    generate
        for (g = 1; g < N; g = g + 1) begin : g_stage
            wire [FW-1:0] pg;
            if (g == 1) begin : g_nd
                assign pg = s0_d[1];
            end else begin : g_d
                localparam integer D = (g - 1) * ADD_LAT;
                reg [FW*D-1:0] dl;
                if (D == 1) begin : g_d1
                    always @(posedge clk) dl <= s0_d[g];
                end else begin : g_dn
                    always @(posedge clk) dl <= {dl[FW*(D-1)-1:0], s0_d[g]};
                end
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
                if (ADD_LAT == 3) begin : g_fast
                    ot_hdc_fp32_add_fast u_add (
                        .clk(clk), .rst_n(rst_n), .valid_in(sv[g-1]),
                        .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                        .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
                end else begin : g_pipe
                    ot_fp32_add_rne_pipe u_add (
                        .clk(clk), .rst_n(rst_n), .valid_in(sv[g-1]),
                        .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                        .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
                end
            end
            assign sv[g] = lv[0];
            assign serr[g] = (|le) || edl[ADD_LAT-1];
        end
    endgenerate
    reg [DL-1:0] ldl;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ldl <= 0;
        else ldl <= {ldl[DL-2:0], s0_last};
    wire red_out = sv[N-1];

    // -- all-gather: GW words per beat, E beats per index, back to back ------------------------------
    reg              go_v, go_last;
    reg [GW*FW-1:0]  go_d;
    reg [RB-1:0]     go_rank;
    wire [EB-1:0]    beat = g_busy ? g_cnt : {EB{1'b0}};
    reg  [GW*FW-1:0] beat_d;
    always @(*) begin
        for (r = 0; r < GW; r = r + 1) beat_d[r*FW +: FW] = s0_d[beat * GW + r];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            g_busy <= 1'b0; g_cnt <= 0; go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; inflight <= 0;
        end else begin
            go_v <= 1'b0;
            if (g_busy || g_first) begin
                go_v <= 1'b1;
                go_d <= beat_d;
                go_rank <= beat * GW;
                go_last <= s0_last && beat == E - 1;
                if (g_busy) begin
                    // the last beat; a new index popped this cycle starts its beat 0 next cycle via g_first
                    if (g_cnt == E - 1) g_busy <= 1'b0;
                    else g_cnt <= g_cnt + 1'b1;
                end else if (E > 1) begin
                    g_busy <= 1'b1;
                    g_cnt <= 1;
                end
            end
            inflight <= inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
        end
    end

    assign out_valid = red_out || go_v;
    assign out_data  = go_v ? go_d : {{(GW-1)*FW{1'b0}}, sum[N-1]};
    assign out_last  = go_v ? go_last : ldl[DL-1];
    assign out_rank  = go_v ? go_rank : {RB{1'b0}};
    assign out_err   = red_out && serr[N-1];

    // -- faults -------------------------------------------------------------------------------
    reg ovf;
    always @(*) begin
        ovf = 1'b0;
        for (r = 0; r < 2 * N; r = r + 1) if (cnt[r] > PD) ovf = 1'b1;
    end
    reg clash_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault <= 1'b0; fault_code <= 3'b0; clash_q <= 1'b0;
        end else begin
            clash_q <= relay_clash;
            if (out_err) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if ((s0_v && !agree) || clash_q) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
        end
    end
endmodule
