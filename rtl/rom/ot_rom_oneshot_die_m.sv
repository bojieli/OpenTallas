`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MARGIN form of ot_rom_oneshot_die (rtl/rom/ot_rom_oneshot_allreduce.sv), the Qwen ROM die's collective engine
// (r21 master qfd_io_collective), for the 2026-10-06/07 closure rules.  Same transactions, same rank-order binary32
// fold, same faults; latency is longer (transaction-level exactness, design simplification rule 1):
//   * every input is captured in a flop at its pin, every output leaves from a flop (register-to-register boundary);
//   * the local port is credit-based (rule 2: no same-cycle cross-block handshake): the sender holds IB credits and
//     in_cr returns one per word taken out of the IB-word input buffer;
//   * each source FIFO has a registered HEAD word (hd / hv): the pop decision reads only flops (hv, the head's mode
//     bit, g_busy, s0_v / s0_mode, inflight == 0), instead of the FIFO counts and the DEPTH:1 read mux;
//   * the adders are ot_hdc_fp32_add_lat at ADD_LAT 7 (the tile's 1.2 GHz-at-SS binary32 adder, same RNE results
//     and error encoding) instead of ot_fp32_add_rne_pipe at 5 (~1.09 GHz at SS);
//   * tx_ready / cr_in are taken from their pin registers (a cycle late): tx_ready is the link layer's registered
//     "may send" (the die link is credit-based end to end; a send against a deasserted tx_ready faults, code bit 2).
// Capacity per source: DEPTH FIFO words + the head register >= the DEPTH credits, so no FIFO can overflow; an
// overflow is still checked and faults.
// ---------------------------------------------------------------------------
module ot_rom_oneshot_die_m #(
    parameter integer N       = 4,
    parameter integer RANK    = 0,
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 16,
    parameter integer ADD_LAT = 7,
    parameter integer IB      = 4,
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW,
    parameter integer RB      = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_cr,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [TAGW-1:0]   in_tag,
    output wire              tx_valid,
    output wire [PW-1:0]     tx_rec,
    input  wire [N-1:0]      tx_ready,
    input  wire [N-1:0]      cr_in,
    input  wire [N-1:0]      rx_valid,
    input  wire [N*PW-1:0]   rx_rec,
    output wire [N-1:0]      cr_out,
    output wire              out_valid,
    output wire [FW-1:0]     out_data,
    output wire              out_last,
    output wire [RB-1:0]     out_rank,
    output wire              out_err,
    output reg               fault,
    output reg  [2:0]        fault_code
);
    localparam integer DB = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer CB = $clog2(DEPTH + 1);
    localparam integer IA = (IB <= 2) ? 1 : $clog2(IB);
    localparam integer DL = (N - 1) * ADD_LAT;
    integer r;
    // ---- pin registers -------------------------------------------------------------------------------------------
    reg              iv_q;
    reg [PW-1:0]     irec_q;
    reg [N-1:0]      txr_q, cri_q, rxv_q;
    reg [N*PW-1:0]   rxr_q;
    always @(posedge clk) begin irec_q <= {in_tag, in_mode, in_last, in_data}; rxr_q <= rx_rec; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv_q <= 1'b0; txr_q <= 0; cri_q <= 0; rxv_q <= 0; end
        else begin iv_q <= in_valid; txr_q <= tx_ready; cri_q <= cr_in; rxv_q <= rx_valid; end
    // ---- local input buffer (IB words, credit per word taken) ----------------------------------------------------
    reg [PW-1:0] ib [0:IB-1];
    reg [IA:0]   iw, ir;
    wire ib_empty = (iw == ir);
    wire ib_full  = (iw[IA-1:0] == ir[IA-1:0]) && (iw[IA] != ir[IA]);
    wire [PW-1:0] ib_head = ib[ir[IA-1:0]];
    always @(posedge clk) if (iv_q && !ib_full) ib[iw[IA-1:0]] <= irec_q;
    // ---- credits and transmit -------------------------------------------------------------------------------------
    reg  [CB-1:0] cr [0:N-1];
    reg  [CB:0]   mcnt [0:N-1];          // words in the source FIFO (head register excluded)
    reg  [N-1:0]  hv;                    // head register valid
    reg  [N-1:0]  can_tx;
    always @(*) for (r = 0; r < N; r = r + 1)
        can_tx[r] = (r == RANK) ? ((mcnt[r] + hv[r]) < DEPTH) : (cr[r] != 0 && txr_q[r]);
    wire fire = !ib_empty && (&can_tx);
    reg          txv_q, icr_q;
    reg [PW-1:0] txrec_q;
    always @(posedge clk) if (fire) txrec_q <= ib_head;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin txv_q <= 1'b0; icr_q <= 1'b0; iw <= 0; ir <= 0; end
        else begin
            txv_q <= fire; icr_q <= fire;
            if (iv_q && !ib_full) iw <= iw + 1'b1;
            if (fire) ir <= ir + 1'b1;
        end
    assign tx_valid = txv_q;
    assign tx_rec = txrec_q;
    assign in_cr = icr_q;
    // ---- receive FIFOs with registered heads ----------------------------------------------------------------------
    reg [PW-1:0] mem [0:N*DEPTH-1];
    reg [DB-1:0] wp [0:N-1];
    reg [DB-1:0] rp [0:N-1];
    reg [PW-1:0] hd [0:N-1];
    wire [N-1:0] push;
    wire [N*PW-1:0] push_rec;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_src
        if (g == RANK) begin : g_loc
            assign push[g] = fire;
            assign push_rec[g*PW +: PW] = ib_head;
        end else begin : g_rem
            assign push[g] = rxv_q[g];
            assign push_rec[g*PW +: PW] = rxr_q[g*PW +: PW];
        end
    end endgenerate
    // ---- pop: a word index leaves every head at once ----------------------------------------------------------------
    reg          g_busy;
    reg  [RB-1:0] g_cnt;
    reg  [15:0]  inflight;
    reg          s0_v, s0_mode, s0_last;
    reg  [FW-1:0] s0_d [0:N-1];
    wire hmode = hd[0][FW + 1];
    wire all_hv = &hv;
    wire pop_red = all_hv && !g_busy && !(s0_v && s0_mode) && !hmode;
    wire pop_gat = all_hv && !g_busy && hmode && inflight == 16'd0 && !s0_v;
    wire pop = pop_red || pop_gat;
    reg [N-1:0] refill;
    always @(*) for (r = 0; r < N; r = r + 1) refill[r] = (mcnt[r] != 0) && (!hv[r] || pop);
    reg cro_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) cro_q <= 1'b0; else cro_q <= pop;
    generate for (g = 0; g < N; g = g + 1) begin : g_cr
        assign cr_out[g] = (g == RANK) ? 1'b0 : cro_q;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (r = 0; r < N; r = r + 1) begin cr[r] <= DEPTH; mcnt[r] <= 0; wp[r] <= 0; rp[r] <= 0; end
            hv <= 0;
        end else begin
            for (r = 0; r < N; r = r + 1) begin
                if (r != RANK) cr[r] <= cr[r] - (fire ? 1'b1 : 1'b0) + (cri_q[r] ? 1'b1 : 1'b0);
                if (push[r]) begin
                    mem[r*DEPTH + wp[r]] <= push_rec[r*PW +: PW];
                    wp[r] <= wp[r] + 1'b1;
                end
                if (refill[r]) begin
                    hd[r] <= mem[r*DEPTH + rp[r]];
                    rp[r] <= rp[r] + 1'b1;
                end
                hv[r] <= refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mcnt[r] <= mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0);
            end
        end
    end
    // ---- head stage ----------------------------------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s0_v <= 1'b0; s0_mode <= 1'b0; s0_last <= 1'b0; end
        else begin
            s0_v <= pop;
            if (pop) begin s0_mode <= hmode; s0_last <= hd[0][FW]; end
        end
    end
    reg [TAGW:0] s0_t [0:N-1];
    always @(posedge clk) if (pop) for (r = 0; r < N; r = r + 1) begin
        s0_d[r] <= hd[r][FW-1:0];
        s0_t[r] <= hd[r][PW-1 -: TAGW + 1];
    end
    reg agree;
    always @(*) begin
        agree = 1'b1;
        for (r = 1; r < N; r = r + 1) if (s0_t[r] != s0_t[0]) agree = 1'b0;
    end
    // ---- all-reduce: ((p0 + p1) + p2) + ... in rank order ----------------------------------------------------------
    wire red_in = s0_v && !s0_mode;
    wire [FW-1:0] sum  [0:N-1];
    wire [N-1:0]  sv;
    wire [N-1:0]  serr;
    // OT_ONESHOT_M_MUTANT (negative control only): ranks 1 and 2 swap places in the fold, ((p0 + p2) + p1) + p3
    wire [FW-1:0] fsrc [0:N-1];
    generate for (g = 0; g < N; g = g + 1) begin : g_fsrc
`ifdef OT_ONESHOT_M_MUTANT
        assign fsrc[g] = (g == 1 && N > 2) ? s0_d[2] : (g == 2) ? s0_d[1] : s0_d[g];
`else
        assign fsrc[g] = s0_d[g];
`endif
    end endgenerate
    assign sum[0] = fsrc[0];
    assign sv[0] = red_in;
    assign serr[0] = 1'b0;
    generate
        for (g = 1; g < N; g = g + 1) begin : g_stage
            wire [FW-1:0] pg;
            if (g == 1) begin : g_nd
                assign pg = fsrc[1];
            end else begin : g_d
                localparam integer D = (g - 1) * ADD_LAT;
                reg [FW*D-1:0] dl;
                always @(posedge clk) dl <= {dl[FW*(D-1)-1:0], fsrc[g]};
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
                ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                    .clk(clk), .rst_n(rst_n), .valid_in(sv[g-1]),
                    .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                    .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
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
    // ---- all-gather --------------------------------------------------------------------------------------------------
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
    // ---- registered outputs --------------------------------------------------------------------------------------------
    reg          ov_q, ol_q, oe_q;
    reg [FW-1:0] od_q;
    reg [RB-1:0] ork_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ov_q <= 1'b0; oe_q <= 1'b0; end
        else begin ov_q <= red_out || go_v; oe_q <= red_out && serr[N-1]; end
    always @(posedge clk) begin
        od_q <= go_v ? go_d : sum[N-1];
        ol_q <= go_v ? go_last : ldl[DL-1];
        ork_q <= go_v ? go_rank : {RB{1'b0}};
    end
    assign out_valid = ov_q; assign out_data = od_q; assign out_last = ol_q; assign out_rank = ork_q; assign out_err = oe_q;
    // ---- faults ------------------------------------------------------------------------------------------------------
    reg ovf;
    always @(*) begin
        ovf = iv_q && ib_full;                                   // the sender ignored its credits
        for (r = 0; r < N; r = r + 1) if (mcnt[r] > DEPTH) ovf = 1'b1;
    end
    localparam [N-1:0] SELF = {{(N-1){1'b0}}, 1'b1} << RANK;
    reg txv_d, txbad;     // a send while a link said no (link-layer violation), judged from the pin registers
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin txv_d <= 1'b0; txbad <= 1'b0; end
        else begin txv_d <= txv_q; txbad <= txv_d && !(&(txr_q | SELF)); end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; fault_code <= 3'b0; end
        else begin
            if (red_out && serr[N-1]) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if (s0_v && !agree) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf || txbad) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
        end
    end
endmodule
